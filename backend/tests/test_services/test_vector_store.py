"""
Tests for QdrantService — search, upsert, collections, health.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.vector_store import QdrantService, SearchResult


class TestSearchResult:
    """SearchResult data class."""

    def test_init_stores_fields(self):
        r = SearchResult(id="1", content="text", score=0.9, metadata={"src": "a"})
        assert r.id == "1"
        assert r.content == "text"
        assert r.score == 0.9
        assert r.metadata == {"src": "a"}


class TestQdrantServiceSearch:
    """search() — result mapping and filters."""

    async def test_search_maps_results(self):
        svc = QdrantService()
        mock_client = AsyncMock()

        mock_point = MagicMock()
        mock_point.id = "point-1"
        mock_point.score = 0.95
        mock_point.payload = {
            "content": "Test chunk",
            "source": "doc.pdf",
            "page": 1,
        }
        mock_client.search.return_value = [mock_point]
        svc._client = mock_client

        results = await svc.search("test-col", [0.1] * 1024, limit=5)
        assert len(results) == 1
        assert results[0].content == "Test chunk"
        assert results[0].score == 0.95
        assert "source" in results[0].metadata
        assert "content" not in results[0].metadata

    async def test_search_with_filters(self):
        svc = QdrantService()
        mock_client = AsyncMock()
        mock_client.search.return_value = []
        svc._client = mock_client

        await svc.search(
            "test-col", [0.1] * 1024, limit=5, filters={"source": "doc.pdf"}
        )
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["query_filter"] is not None

    async def test_search_without_filters(self):
        svc = QdrantService()
        mock_client = AsyncMock()
        mock_client.search.return_value = []
        svc._client = mock_client

        await svc.search("test-col", [0.1] * 1024, limit=5)
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["query_filter"] is None


class TestQdrantServiceCollections:
    """Collection management."""

    async def test_get_collections_returns_names(self):
        svc = QdrantService()
        mock_client = AsyncMock()
        mock_col = MagicMock()
        mock_col.name = "default"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_col]
        mock_client.get_collections.return_value = mock_collections
        svc._client = mock_client

        result = await svc.get_collections()
        assert result == ["default"]

    async def test_ensure_collection_creates_when_missing(self):
        svc = QdrantService()
        mock_client = AsyncMock()
        mock_collections = MagicMock()
        mock_collections.collections = []  # no existing collections
        mock_client.get_collections.return_value = mock_collections
        svc._client = mock_client

        await svc.ensure_collection("new-col", dimensions=1024)
        mock_client.create_collection.assert_called_once()

    async def test_ensure_collection_skips_when_exists(self):
        svc = QdrantService()
        mock_client = AsyncMock()
        mock_col = MagicMock()
        mock_col.name = "existing"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_col]
        mock_client.get_collections.return_value = mock_collections
        svc._client = mock_client

        await svc.ensure_collection("existing")
        mock_client.create_collection.assert_not_called()


class TestQdrantServiceHealth:
    """Health check."""

    async def test_health_check_success(self):
        svc = QdrantService()
        mock_client = AsyncMock()
        mock_client.get_collections.return_value = MagicMock()
        svc._client = mock_client
        assert await svc.health_check() is True

    async def test_health_check_failure(self):
        svc = QdrantService()
        mock_client = AsyncMock()
        mock_client.get_collections.side_effect = Exception("connection refused")
        svc._client = mock_client
        assert await svc.health_check() is False
