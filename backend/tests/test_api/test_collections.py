"""
Tests for collection endpoints — GET /collections.
"""

import pytest
from httpx import AsyncClient


class TestCollectionsEndpoint:
    """GET /collections — list document collections."""

    async def test_list_collections_returns_list(self, client: AsyncClient):
        response = await client.get("/collections")
        assert response.status_code == 200
        data = response.json()
        assert "collections" in data
        collections = data["collections"]
        assert isinstance(collections, list)
        assert len(collections) >= 1
        for c in collections:
            assert "name" in c
            assert "chunks" in c

    async def test_list_collections_fallback_on_error(self, client: AsyncClient, app):
        # Make vector_store raise
        app.state.vector_store.get_collections.side_effect = Exception("connection error")
        response = await client.get("/collections")
        assert response.status_code == 200
        data = response.json()
        assert data["collections"][0]["name"] == "default"
        # Restore
        app.state.vector_store.get_collections.side_effect = None
