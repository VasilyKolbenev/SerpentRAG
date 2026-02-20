"""
FastAPI dependencies — auth, services, database sessions.
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Header

from app.config import settings


class AuthService:
    """JWT authentication service."""

    @staticmethod
    def create_token(
        user_id: str,
        role: str = "user",
        tenant_id: Optional[str] = None,
    ) -> str:
        """Create a JWT access token."""
        import uuid

        payload = {
            "sub": user_id,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours),
            "jti": str(uuid.uuid4()),
        }
        if tenant_id:
            payload["tenant_id"] = tenant_id
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify and decode a JWT token."""
        try:
            return jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> Optional[dict]:
    """Extract current user from Authorization header. Optional auth."""
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    return AuthService.verify_token(token)


async def require_auth(
    user: Optional[dict] = Depends(get_current_user),
) -> dict:
    """Require authenticated user."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
