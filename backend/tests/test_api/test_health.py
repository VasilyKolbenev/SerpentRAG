"""
Tests for health endpoints — healthy, degraded, readyz.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """GET /health — service connectivity checks."""

    async def test_health_all_healthy(self, client: AsyncClient, app):
        # engine is imported inside the function: from app.models.base import engine
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_ctx

        with patch("app.models.base.engine", mock_engine):
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["version"] == "1.0.0"
        assert "services" in data
        assert "timestamp" in data

    async def test_health_degraded_when_service_down(self, client: AsyncClient, app):
        app.state.vector_store.health_check.return_value = False

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_ctx

        with patch("app.models.base.engine", mock_engine):
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["vector_store"] == "unhealthy"

    async def test_health_handles_db_failure(self, client: AsyncClient, app):
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("connection refused")

        with patch("app.models.base.engine", mock_engine):
            response = await client.get("/health")

        data = response.json()
        assert data["services"]["database"] == "unhealthy"


class TestReadinessEndpoint:
    """GET /readyz — kubernetes-style probe."""

    async def test_readyz_returns_ready(self, client: AsyncClient):
        response = await client.get("/readyz")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
