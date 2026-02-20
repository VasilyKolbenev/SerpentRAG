"""
Tests for multi-tenancy — tenant isolation, middleware, JWT claims.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.dependencies import AuthService
from app.middleware.tenant import TenantMiddleware, get_tenant_id
from app.models.tenant import Tenant
from app.models.base import TenantMixin


class TestTenantModel:
    """Tenant model and TenantMixin tests."""

    def test_tenant_mixin_has_tenant_id(self):
        """TenantMixin provides tenant_id field."""
        assert hasattr(TenantMixin, "tenant_id")

    def test_tenant_model_exists(self):
        """Tenant model has required fields."""
        assert Tenant.__tablename__ == "tenants"


class TestTenantJWT:
    """JWT with tenant_id claim."""

    def test_create_token_with_tenant_id(self):
        """create_token includes tenant_id in JWT payload."""
        with patch("app.dependencies.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret-key-for-jwt"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_expire_hours = 24
            token = AuthService.create_token(
                user_id="user1",
                role="user",
                tenant_id="tenant-abc-123",
            )

        with patch("app.dependencies.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret-key-for-jwt"
            mock_settings.jwt_algorithm = "HS256"
            payload = AuthService.verify_token(token)

        assert payload["tenant_id"] == "tenant-abc-123"
        assert payload["sub"] == "user1"

    def test_create_token_without_tenant_id(self):
        """create_token without tenant_id doesn't include it."""
        with patch("app.dependencies.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret-key-for-jwt"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_expire_hours = 24
            token = AuthService.create_token(user_id="user1")

        with patch("app.dependencies.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret-key-for-jwt"
            mock_settings.jwt_algorithm = "HS256"
            payload = AuthService.verify_token(token)

        assert "tenant_id" not in payload


class TestTenantMiddleware:
    """TenantMiddleware extracts tenant_id from request."""

    def test_extract_tenant_id_no_header(self):
        """No auth header → None."""
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {}

        with patch("app.middleware.tenant.settings") as mock_settings:
            mock_settings.jwt_secret = "test"
            mock_settings.jwt_algorithm = "HS256"
            result = TenantMiddleware._extract_tenant_id(request)

        assert result is None

    def test_extract_tenant_id_with_header(self):
        """Auth header with tenant_id → extracts it."""
        from unittest.mock import MagicMock

        with patch("app.dependencies.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret-key-for-jwt"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_expire_hours = 24
            token = AuthService.create_token(
                user_id="u1", tenant_id="t-123"
            )

        request = MagicMock()
        request.headers = {"authorization": f"Bearer {token}"}

        with patch("app.middleware.tenant.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret-key-for-jwt"
            mock_settings.jwt_algorithm = "HS256"
            result = TenantMiddleware._extract_tenant_id(request)

        assert result == "t-123"
