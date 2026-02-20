"""
Tenant middleware — extracts tenant_id from JWT and injects into request.state.
When multi-tenancy is disabled, tenant_id defaults to None (no filtering).
"""

import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings

logger = logging.getLogger("serpent.tenant")


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant_id from JWT claims and set on request.state."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.tenant_id = None

        if settings.multi_tenancy_enabled:
            tenant_id = self._extract_tenant_id(request)
            request.state.tenant_id = tenant_id

        return await call_next(request)

    @staticmethod
    def _extract_tenant_id(request: Request) -> Optional[str]:
        """Extract tenant_id from JWT Bearer token."""
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        try:
            import jwt as pyjwt
            token = auth_header[7:]
            payload = pyjwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            return payload.get("tenant_id")
        except Exception:
            return None


def get_tenant_id(request: Request) -> Optional[str]:
    """FastAPI dependency to get the current tenant_id from request."""
    return getattr(request.state, "tenant_id", None)
