"""
Middleware modules for Smart Legal Assistant API.
"""

from .auth_middleware import jwt_auth_middleware

__all__ = ["jwt_auth_middleware"]
