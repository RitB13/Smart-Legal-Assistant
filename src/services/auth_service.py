"""
Authentication Module - Handles password hashing, JWT tokens, and user verification.

This module provides:
- Password hashing and verification
- JWT token generation and validation
- User context extraction from tokens
- Token expiration handling
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import logging
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = "your-secret-key-change-this-in-production-use-env-variable"  # TODO: Move to env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours

# ==================== TOKEN MODELS ====================

class TokenData(BaseModel):
    """Data stored in JWT token"""
    user_id: str
    email: str
    exp: datetime = None  # Expiration time


class TokenResponse(BaseModel):
    """Response when returning token to client"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


# ==================== PASSWORD FUNCTIONS ====================

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Handles passwords longer than bcrypt's 72-byte limit by
    pre-hashing with SHA256 if necessary.
    
    Args:
        password: Plaintext password from user
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> # Store hashed in database
    """
    try:
        # Bcrypt has a 72-byte limit, so pre-hash longer passwords with SHA256
        if len(password.encode('utf-8')) > 72:
            import hashlib
            password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        hashed = pwd_context.hash(password)
        logger.debug("[AUTH] Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"[AUTH] Error hashing password: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hash.
    
    Handles passwords that were pre-hashed with SHA256 due to
    bcrypt's 72-byte limit.
    
    Args:
        plain_password: Password from login request
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> valid = verify_password("mypassword123", stored_hash)
        >>> if valid:
        >>>     # Password is correct
    """
    try:
        # Apply same pre-hashing if password is too long
        if len(plain_password.encode('utf-8')) > 72:
            import hashlib
            plain_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"[AUTH] Error verifying password: {e}")
        return False


# ==================== JWT TOKEN FUNCTIONS ====================

def create_access_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> TokenResponse:
    """
    Create a JWT access token for a user.
    
    Args:
        user_id: User's MongoDB ObjectId as string
        email: User's email address
        expires_delta: Token expiration time (default: 24 hours)
        
    Returns:
        TokenResponse with access_token and expiration info
        
    Example:
        >>> token = create_access_token(user_id="507f...", email="john@example.com")
        >>> # token.access_token can be sent to frontend
        >>> # token.expires_in shows seconds until expiration
    """
    try:
        # Calculate expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        # Create token payload
        to_encode = {
            "user_id": user_id,
            "email": email,
            "exp": expire.timestamp(),  # Unix timestamp
            "iat": datetime.now(timezone.utc).timestamp(),  # Issued at
        }
        
        # Encode JWT
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # Calculate expires_in
        expires_in = int((expire - datetime.now(timezone.utc)).total_seconds())
        
        logger.info(f"[AUTH] Token created for user: {email}")
        
        return TokenResponse(
            access_token=encoded_jwt,
            token_type="bearer",
            expires_in=expires_in
        )
        
    except Exception as e:
        logger.error(f"[AUTH] Error creating token: {e}")
        raise


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string from Authorization header
        
    Returns:
        TokenData if token is valid and not expired
        None if token is invalid or expired
        
    Example:
        >>> token_data = verify_token(token_from_header)
        >>> if token_data:
        >>>     user_id = token_data.user_id  # Use in endpoint
        >>> else:
        >>>     # Token invalid or expired
    """
    try:
        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract user info
        user_id = payload.get("user_id")
        email = payload.get("email")
        exp = payload.get("exp")
        
        if not user_id or not email:
            logger.warning("[AUTH] Token missing required fields")
            return None
        
        # Check expiration (jwt.decode checks this automatically, but being explicit)
        if exp:
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            if datetime.now(timezone.utc) > exp_datetime:
                logger.warning(f"[AUTH] Token expired for user: {email}")
                return None
        
        logger.debug(f"[AUTH] Token verified for user: {email}")
        
        return TokenData(
            user_id=user_id,
            email=email,
            exp=exp_datetime if exp else None
        )
        
    except JWTError as e:
        logger.warning(f"[AUTH] Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"[AUTH] Error verifying token: {e}")
        return None


def extract_token_from_header(authorization_header: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Expected format: "Bearer <token>"
    
    Args:
        authorization_header: Authorization header value
        
    Returns:
        Token string if valid format, None otherwise
        
    Example:
        >>> header = "Bearer eyJhbGciOiJIUzI1NiIs..."
        >>> token = extract_token_from_header(header)
        >>> # token = "eyJhbGciOiJIUzI1NiIs..."
    """
    try:
        parts = authorization_header.split()
        
        if len(parts) != 2:
            logger.warning("[AUTH] Invalid authorization header format")
            return None
        
        scheme, token = parts
        
        if scheme.lower() != "bearer":
            logger.warning(f"[AUTH] Invalid auth scheme: {scheme}")
            return None
        
        return token
        
    except Exception as e:
        logger.error(f"[AUTH] Error extracting token: {e}")
        return None


# ==================== DEMONSTRATION ====================

if __name__ == "__main__":
    # Example usage
    print("[TEST] Authentication Module Demo\n")
    
    # Password hashing
    password = "mySecurePassword123!"
    hashed = hash_password(password)
    print(f"Original: {password}")
    print(f"Hashed:   {hashed}\n")
    
    # Password verification
    is_valid = verify_password(password, hashed)
    print(f"Password valid: {is_valid}\n")
    
    # Token creation
    token_response = create_access_token(
        user_id="507f1f77bcf86cd799439011",
        email="test@example.com"
    )
    print(f"Token created: {token_response.access_token[:50]}...")
    print(f"Expires in: {token_response.expires_in} seconds\n")
    
    # Token verification
    token_data = verify_token(token_response.access_token)
    if token_data:
        print(f"Token verified!")
        print(f"User ID: {token_data.user_id}")
        print(f"Email: {token_data.email}")
    else:
        print("Token invalid!")
