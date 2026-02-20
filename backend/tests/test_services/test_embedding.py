"""
Tests for EmbeddingService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.embedding import EmbeddingService


class TestEmbeddingService:
    """EmbeddingService — provider routing, empty input handling."""

    async def test_embed_empty_list_returns_empty(self):
        svc = EmbeddingService()
        result = await svc.embed([])
        assert result == []

    async def test_embed_query_delegates_to_embed(self):
        svc = EmbeddingService()
        svc.embed = AsyncMock(return_value=[[0.5] * 1024])
        result = await svc.embed_query("hello")
        assert result == [0.5] * 1024
        svc.embed.assert_called_once_with(["hello"])

    async def test_embed_local_raises_without_init(self):
        svc = EmbeddingService()
        svc._provider = "local"
        svc._model = None
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc._embed_local(["test"], batch_size=64)

    async def test_embed_openai_raises_without_init(self):
        svc = EmbeddingService()
        svc._provider = "openai"
        svc._openai_client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc._embed_openai(["test"], batch_size=64)

    def test_dimensions_property(self):
        svc = EmbeddingService()
        assert svc.dimensions == svc._dimensions

    async def test_embed_routes_to_openai_provider(self):
        svc = EmbeddingService()
        svc._provider = "openai"
        svc._embed_openai = AsyncMock(return_value=[[0.1] * 1024])
        result = await svc.embed(["test"])
        svc._embed_openai.assert_called_once()
        assert result == [[0.1] * 1024]

    async def test_embed_routes_to_local_provider(self):
        svc = EmbeddingService()
        svc._provider = "local"
        svc._embed_local = AsyncMock(return_value=[[0.2] * 1024])
        result = await svc.embed(["test"])
        svc._embed_local.assert_called_once()
        assert result == [[0.2] * 1024]
