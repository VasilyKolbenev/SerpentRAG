"""
Tests for graph endpoints — GET /graph/explore.
"""

import pytest
from httpx import AsyncClient


class TestGraphExploreEndpoint:
    """GET /graph/explore — Knowledge Graph Explorer data."""

    async def test_explore_returns_graph_data(self, client: AsyncClient):
        response = await client.get("/graph/explore?collection=default&depth=2&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    async def test_explore_with_entity(self, client: AsyncClient):
        response = await client.get(
            "/graph/explore?collection=default&entity=Python&depth=3"
        )
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data

    async def test_explore_handles_graph_store_error(self, client: AsyncClient, app):
        app.state.graph_store.get_subgraph.side_effect = Exception("connection error")
        response = await client.get("/graph/explore")
        assert response.status_code == 200
        data = response.json()
        assert data == {"nodes": [], "edges": []}
        # Restore
        app.state.graph_store.get_subgraph.side_effect = None
