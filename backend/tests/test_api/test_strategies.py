"""
Tests for strategy endpoints — GET /strategies, POST /recommend.
"""

import pytest
from httpx import AsyncClient


class TestStrategiesEndpoint:
    """GET /strategies — list all strategies."""

    async def test_list_strategies_returns_all_four(self, client: AsyncClient):
        response = await client.get("/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        strategies = data["strategies"]
        assert len(strategies) == 6
        ids = [s["id"] for s in strategies]
        assert "naive" in ids
        assert "hybrid" in ids
        assert "graph" in ids
        assert "agentic" in ids
        assert "memo" in ids
        assert "corrective" in ids

    async def test_strategy_info_has_required_fields(self, client: AsyncClient):
        response = await client.get("/strategies")
        data = response.json()
        for s in data["strategies"]:
            assert "id" in s
            assert "name" in s
            assert "description" in s
            assert "complexity" in s
            assert "latency" in s
            assert "accuracy" in s


class TestRecommendEndpoint:
    """POST /recommend — strategy recommendation."""

    async def test_recommend_returns_strategy(self, client: AsyncClient):
        response = await client.post(
            "/recommend",
            json={
                "domain": "enterprise",
                "query_complexity": "moderate",
                "data_structure": "flat",
                "priority": "speed",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommended" in data
        assert data["recommended"] in (
            "naive", "hybrid", "graph", "agentic", "memo", "corrective"
        )
        assert "scores" in data
        assert "reasoning" in data
        assert isinstance(data["scores"], dict)
        assert len(data["scores"]) == 6
