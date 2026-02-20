"""
Tests for query endpoints — POST /query, POST /compare, validation.
"""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


class TestQueryEndpoint:
    """POST /query — main RAG query."""

    async def test_query_returns_answer_and_sources(self, client: AsyncClient):
        response = await client.post(
            "/query",
            json={
                "query": "What is Python?",
                "strategy": "naive",
                "collection": "default",
                "top_k": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "strategy_used" in data
        assert data["strategy_used"] == "naive"
        assert "trace_id" in data
        assert "latency_ms" in data
        assert isinstance(data["sources"], list)

    async def test_query_with_default_strategy(self, client: AsyncClient):
        response = await client.post(
            "/query",
            json={"query": "Hello world"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_used"] == "hybrid"  # default

    async def test_query_validation_empty_query(self, client: AsyncClient):
        response = await client.post(
            "/query",
            json={"query": ""},
        )
        assert response.status_code == 422  # validation error

    async def test_query_validation_invalid_strategy(self, client: AsyncClient):
        response = await client.post(
            "/query",
            json={"query": "test", "strategy": "nonexistent"},
        )
        assert response.status_code == 422

    async def test_query_validation_top_k_out_of_range(self, client: AsyncClient):
        response = await client.post(
            "/query",
            json={"query": "test", "top_k": 100},
        )
        assert response.status_code == 422


class TestCompareEndpoint:
    """POST /compare — A/B comparison."""

    async def test_compare_returns_results(self, client: AsyncClient):
        response = await client.post(
            "/compare",
            json={
                "query": "What is Python?",
                "strategies": ["naive", "hybrid"],
                "collection": "default",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 2

    async def test_compare_requires_min_two_strategies(self, client: AsyncClient):
        response = await client.post(
            "/compare",
            json={
                "query": "test",
                "strategies": ["naive"],
            },
        )
        assert response.status_code == 422

    async def test_compare_max_four_strategies(self, client: AsyncClient):
        response = await client.post(
            "/compare",
            json={
                "query": "test",
                "strategies": ["naive", "hybrid", "graph", "agentic", "naive"],
            },
        )
        assert response.status_code == 422
