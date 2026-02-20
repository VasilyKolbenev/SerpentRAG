"""
Tests for metrics endpoints — GET /metrics/quality.
"""

import pytest
from httpx import AsyncClient


class TestQualityMetricsEndpoint:
    """GET /metrics/quality — RAGAS dashboard data."""

    async def test_get_quality_metrics_default(self, client: AsyncClient):
        response = await client.get("/metrics/quality")
        assert response.status_code == 200
        data = response.json()
        assert data["strategy"] == "all"
        assert data["period"] == "7d"
        assert "avg_scores" in data
        assert "total_queries" in data

    async def test_get_quality_metrics_with_params(self, client: AsyncClient):
        response = await client.get("/metrics/quality?strategy=naive&period=24h")
        assert response.status_code == 200
        data = response.json()
        assert data["strategy"] == "naive"
        assert data["period"] == "24h"
