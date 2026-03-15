"""
Authentication Routes - FastAPI endpoints for user authentication.

Endpoints:
- POST /auth/register   - Create new user account
- POST /auth/login      - Authenticate user and return JWT token
- POST /auth/logout     - Logout user (invalidate token)
- GET  /auth/me         - Get current authenticated user info
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging

from src.services.user_service import UserService
from src.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    extract_token_from_header,
    TokenResponse,
    TokenData
)
from src.models.db_models import UserCreate, User

logger = logging.getLogger(__name__)

# Router for auth endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== REQUEST/RESPONSE MODELS ====================

class RegisterRequest(BaseModel):
    """Register endpoint request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    name: str = Field(..., min_length=2, description="Full name")
    preferred_language: str = "en"
    jurisdiction: str = "india"
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123!",
                "name": "John Doe",
                "preferred_language": "en",
                "jurisdiction": "india"
            }
        }


class LoginRequest(BaseModel):
    """Login endpoint request"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123!"
            }
        }


class LoginResponse(BaseModel):
    """Login endpoint response"""
    user_id: str
    email: str
    name: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User info response"""
    id: str = Field(alias="_id")
    email: str
    name: str
    preferred_language: str
    jurisdiction: str
    is_active: bool
    
    class Config:
        populate_by_name = True


# ==================== DEPENDENCY: GET CURRENT USER ====================

async def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    """
    Dependency to extract and verify current user from JWT token.
    
    Used in protected endpoints to ensure user is authenticated.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        TokenData with user_id and email
        
    Raises:
        HTTPException 401 if token is missing or invalid
        HTTPException 403 if token is expired
    """
    if not authorization:
        logger.warning("[AUTH] Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = extract_token_from_header(authorization)
    
    if not token:
        logger.warning("[AUTH] Invalid header format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = verify_token(token)
    
    if not token_data:
        logger.warning("[AUTH] Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


# ==================== ENDPOINTS ====================

@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user account.
    
    Args:
        request: Registration details (email, password, name, etc.)
        
    Returns:
        LoginResponse with JWT token for immediate login
        
    Raises:
        HTTPException 400 if email already registered
        HTTPException 500 if server error
        
    Example:
        POST /auth/register
        {
            "email": "john@example.com",
            "password": "SecurePass123!",
            "name": "John Doe",
            "preferred_language": "en",
            "jurisdiction": "india"
        }
    """
    try:
        logger.info(f"[AUTH] Registration attempt: {request.email}")
        
        # Check if user already exists
        if UserService.user_exists(request.email):
            logger.warning(f"[AUTH] Registration failed: {request.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create user
        user_data = UserCreate(
            email=request.email,
            password=request.password,  # Not used after hashing, but required by model
            name=request.name,
            preferred_language=request.preferred_language,
            jurisdiction=request.jurisdiction
        )
        
        created_user = UserService.create_user(user_data, password_hash)
        
        if not created_user:
            logger.error(f"[AUTH] Failed to create user: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Create token
        token_response = create_access_token(
            user_id=str(created_user.id),
            email=created_user.email
        )
        
        logger.info(f"[AUTH] User registered successfully: {request.email}")
        
        return LoginResponse(
            user_id=str(created_user.id),
            email=created_user.email,
            name=created_user.name,
            access_token=token_response.access_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    Args:
        request: Login credentials (email, password)
        
    Returns:
        LoginResponse with JWT token
        
    Raises:
        HTTPException 401 if credentials are invalid
        HTTPException 500 if server error
        
    Example:
        POST /auth/login
        {
            "email": "john@example.com",
            "password": "SecurePass123!"
        }
    """
    try:
        logger.info(f"[AUTH] Login attempt: {request.email}")
        
        # Get user from database
        user = UserService.get_user_by_email(request.email)
        
        if not user:
            logger.warning(f"[AUTH] Login failed: user not found {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check password
        if not verify_password(request.password, user.password_hash):
            logger.warning(f"[AUTH] Login failed: invalid password {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"[AUTH] Login failed: account disabled {request.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Create token
        token_response = create_access_token(
            user_id=str(user.id),
            email=user.email
        )
        
        logger.info(f"[AUTH] User logged in: {request.email}")
        
        return LoginResponse(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            access_token=token_response.access_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_user)):
    """
    Logout user (client-side token invalidation).
    
    Note: JWT tokens can't be revoked server-side without a token blacklist.
    This endpoint is here for consistency. Clients should discard the token.
    
    Args:
        current_user: Current authenticated user (from JWT)
        
    Returns:
        Confirmation message
        
    Example:
        POST /auth/logout
        Header: Authorization: Bearer <token>
    """
    logger.info(f"[AUTH] User logged out: {current_user.email}")
    
    return {
        "message": "Logged out successfully",
        "user_id": current_user.user_id
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user's info.
    
    Args:
        current_user: Current authenticated user (from JWT)
        
    Returns:
        UserResponse with user profile information
        
    Example:
        GET /auth/me
        Header: Authorization: Bearer <token>
    """
    try:
        user = UserService.get_user_by_id(current_user.user_id)
        
        if not user:
            logger.error(f"[AUTH] User not found: {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.debug(f"[AUTH] Retrieved user info: {current_user.email}")
        
        return UserResponse(
            _id=str(user.id),
            email=user.email,
            name=user.name,
            preferred_language=user.preferred_language,
            jurisdiction=user.jurisdiction,
            is_active=user.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user info"
        )
