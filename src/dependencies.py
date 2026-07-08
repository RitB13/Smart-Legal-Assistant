"""
Shared FastAPI dependencies.

Centralised here so route files never need to import from each other and the
dependency can be used in any router without circular imports.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from src.services.auth_service import verify_token, TokenData

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> TokenData:
    """
    FastAPI dependency: extract and verify the current user from a JWT Bearer token.

    Raises:
        HTTPException 401 if the token is missing or invalid.
    """
    if not credentials:
        logger.warning("[AUTH] Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Missing authorization header. "
                "Use the Authorize button (top-right in Swagger) to set your Bearer token."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = verify_token(credentials.credentials)

    if not token_data:
        logger.warning("[AUTH] Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data
