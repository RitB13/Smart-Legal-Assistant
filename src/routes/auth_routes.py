"""
Authentication Routes - FastAPI endpoints for user authentication.

Endpoints:
- POST /auth/register        - Create new user account (sends OTP, no token yet)
- POST /auth/verify-otp      - Verify email OTP, returns JWT token
- POST /auth/resend-otp      - Resend verification OTP
- POST /auth/login           - Authenticate user and return JWT token
- POST /auth/logout          - Logout user (invalidate token)
- GET  /auth/me              - Get current authenticated user info
- POST /auth/forgot-password - Send password-reset OTP
- POST /auth/reset-password  - Reset password using OTP
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
from src.services.email_service import generate_otp, send_otp_email
from src.models.db_models import UserCreate, User
# Re-export so any code that still imports get_current_user from here continues to work.
from src.dependencies import get_current_user as get_current_user  # noqa: F401

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


class RegisterResponse(BaseModel):
    """Register endpoint response — no token yet, user must verify email"""
    message: str
    email: str


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


class VerifyOtpRequest(BaseModel):
    """OTP verification request"""
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "otp_code": "123456"
            }
        }


class ResendOtpRequest(BaseModel):
    """Resend OTP request"""
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com"
            }
        }


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com"
            }
        }


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, description="New password, at least 8 characters")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "otp_code": "123456",
                "new_password": "NewSecurePass456!"
            }
        }


class UserResponse(BaseModel):
    """User info response"""
    id: str = Field(alias="_id")
    email: str
    name: str
    preferred_language: str
    jurisdiction: str
    is_active: bool
    is_verified: bool

    class Config:
        populate_by_name = True


# ==================== ENDPOINTS ====================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user account.

    Creates the user and sends a 6-digit OTP to the provided email.
    The user must call POST /auth/verify-otp to get their JWT token.

    Raises:
        HTTPException 400 if email already registered
        HTTPException 500 if server error or email delivery failure
    """
    try:
        logger.info(f"[AUTH] Registration attempt: {request.email}")

        if UserService.user_exists(request.email):
            logger.warning(f"[AUTH] Registration failed: {request.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        password_hash = hash_password(request.password)

        user_data = UserCreate(
            email=request.email,
            password=request.password,
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

        otp = generate_otp()
        UserService.set_otp(request.email, otp, expires_minutes=10)

        email_sent = send_otp_email(
            to_email=request.email,
            otp=otp,
            user_name=request.name,
            purpose="verification"
        )

        if not email_sent:
            logger.warning(f"[AUTH] OTP email failed for {request.email} — user created but unverified")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account created but failed to send verification email. Use /auth/resend-otp to try again."
            )

        logger.info(f"[AUTH] User registered, OTP sent: {request.email}")
        return RegisterResponse(
            message="Account created. Please check your email for the 6-digit verification code.",
            email=request.email
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/verify-otp", response_model=LoginResponse)
async def verify_otp(request: VerifyOtpRequest):
    """
    Verify email OTP and return a JWT token.

    Call this after POST /auth/register with the code from the email.
    On success marks the account as verified and returns a token for immediate use.

    Raises:
        HTTPException 400 if OTP is invalid or expired
        HTTPException 404 if email not found
    """
    try:
        logger.info(f"[AUTH] OTP verification attempt: {request.email}")

        user = UserService.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email address not found"
            )

        verified = UserService.verify_and_clear_otp(request.email, request.otp_code)
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )

        token_response = create_access_token(
            user_id=str(user.id),
            email=user.email
        )

        logger.info(f"[AUTH] Email verified, token issued: {request.email}")
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
        logger.error(f"[AUTH] OTP verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP verification failed"
        )


@router.post("/resend-otp")
async def resend_otp(request: ResendOtpRequest):
    """
    Resend a verification OTP to the given email.

    Works for unverified accounts. Generates a fresh OTP and invalidates the old one.

    Raises:
        HTTPException 404 if email not found
        HTTPException 400 if account is already verified
        HTTPException 500 if email delivery fails
    """
    try:
        logger.info(f"[AUTH] Resend OTP request: {request.email}")

        user = UserService.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email address not found"
            )

        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified. Please log in."
            )

        otp = generate_otp()
        UserService.set_otp(request.email, otp, expires_minutes=10)

        email_sent = send_otp_email(
            to_email=request.email,
            otp=otp,
            user_name=user.name,
            purpose="verification"
        )

        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Please try again."
            )

        logger.info(f"[AUTH] OTP resent: {request.email}")
        return {"message": "Verification code sent. Please check your email.", "email": request.email}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Resend OTP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend OTP"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.

    Unverified accounts are rejected with 403 and a hint to use /auth/resend-otp.

    Raises:
        HTTPException 401 if credentials are invalid
        HTTPException 403 if account is unverified or disabled
        HTTPException 500 if server error
    """
    try:
        logger.info(f"[AUTH] Login attempt: {request.email}")

        user = UserService.get_user_by_email(request.email)

        if not user:
            logger.warning(f"[AUTH] Login failed: user not found {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not verify_password(request.password, user.password_hash):
            logger.warning(f"[AUTH] Login failed: invalid password {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not user.is_active:
            logger.warning(f"[AUTH] Login failed: account disabled {request.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        if not user.is_verified:
            logger.warning(f"[AUTH] Login failed: email not verified {request.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your inbox or use /auth/resend-otp."
            )

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


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Send a password-reset OTP to the given email.

    Always returns 200 even if the email does not exist (prevents user enumeration).

    Raises:
        HTTPException 500 if email delivery fails (only when user exists)
    """
    try:
        logger.info(f"[AUTH] Forgot password request: {request.email}")

        user = UserService.get_user_by_email(request.email)
        if not user:
            # Don't reveal whether the email exists
            return {"message": "If that email is registered, a reset code has been sent."}

        otp = generate_otp()
        UserService.set_otp(request.email, otp, expires_minutes=10)

        email_sent = send_otp_email(
            to_email=request.email,
            otp=otp,
            user_name=user.name,
            purpose="password_reset"
        )

        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email. Please try again."
            )

        logger.info(f"[AUTH] Password reset OTP sent: {request.email}")
        return {"message": "If that email is registered, a reset code has been sent."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process request"
        )


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using the OTP received via email.

    Validates the OTP, then updates the password hash and clears the OTP.

    Raises:
        HTTPException 400 if OTP is invalid or expired
        HTTPException 404 if email not found
        HTTPException 500 if update fails
    """
    try:
        logger.info(f"[AUTH] Password reset attempt: {request.email}")

        user = UserService.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email address not found"
            )

        verified = UserService.verify_and_clear_otp(request.email, request.otp_code)
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )

        new_hash = hash_password(request.new_password)
        success = UserService.update_password(request.email, new_hash)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )

        logger.info(f"[AUTH] Password reset successful: {request.email}")
        return {"message": "Password updated successfully. You can now log in with your new password."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_user)):
    """
    Logout user (client-side token invalidation).

    JWT tokens can't be revoked server-side without a blacklist.
    Clients should discard the token on receipt of this response.
    """
    logger.info(f"[AUTH] User logged out: {current_user.email}")
    return {
        "message": "Logged out successfully",
        "user_id": current_user.user_id
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user's profile.

    Raises:
        HTTPException 404 if user record not found
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
            is_active=user.is_active,
            is_verified=user.is_verified
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user info"
        )
