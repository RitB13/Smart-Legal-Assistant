"""
JWT Authentication Middleware - Validates JWT tokens from request headers.

This middleware verifies JWT tokens from Authorization headers on protected endpoints,
ensuring only authenticated users can access certain routes.
"""

import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable

from src.services.auth_service import extract_token_from_header, verify_token

logger = logging.getLogger(__name__)


async def jwt_auth_middleware(request: Request, call_next: Callable):
    """
    Middleware to verify JWT token from Authorization header.
    
    Checks for Bearer token in Authorization header and validates it.
    If valid, adds user data to request state for use in endpoints.
    If invalid or missing, allows request to continue (endpoint-level validation).
    
    Args:
        request: HTTP request object
        call_next: Next middleware/route handler in chain
        
    Returns:
        Response from next handler, or error response if token invalid
    """
    # Skip auth for public endpoints
    public_paths = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/register",
        "/auth/login",
    ]
    
    request_path = request.url.path
    
    if any(request_path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        logger.debug(f"[MIDDLEWARE] Missing auth header for {request_path}")
        # Don't block - let endpoint-level dependencies handle auth
        return await call_next(request)
    
    try:
        # Extract token from Bearer scheme
        token = extract_token_from_header(auth_header)
        
        if not token:
            logger.warning(f"[MIDDLEWARE] Invalid header format for {request_path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"}
            )
        
        # Verify token
        token_data = verify_token(token)
        
        if not token_data:
            logger.warning(f"[MIDDLEWARE] Invalid token for {request_path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"}
            )
        
        # Add token data to request state for use in endpoints
        request.state.user_id = token_data.user_id
        request.state.email = token_data.email
        logger.debug(f"[MIDDLEWARE] Authenticated user {token_data.email} for {request_path}")
        
    except Exception as e:
        logger.error(f"[MIDDLEWARE] Auth error for {request_path}: {e}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication failed"}
        )
    
    # Continue to next handler
    return await call_next(request)
