"""
Tests for RedisService — key generation, get/set patterns.
"""

import json
from unittest.mock import AsyncMock, patch

from app.services.cache import RedisService


class TestRedisServiceKeys:
    """Key generation (static, pure logic)."""

    def test_query_key_is_deterministic(self):
        k1 = RedisService._query_key("hello", "naive", "default")
        k2 = RedisService._query_key("hello", "naive", "default")
        assert k1 == k2
        assert k1.startswith("serpent:query:naive:default:")

    def test_query_key_differs_by_strategy(self):
        k1 = RedisService._query_key("hello", "naive", "default")
        k2 = RedisService._query_key("hello", "hybrid", "default")
        assert k1 != k2

    def test_query_key_differs_by_collection(self):
        k1 = RedisService._query_key("hello", "naive", "default")
        k2 = RedisService._query_key("hello", "naive", "other")
        assert k1 != k2

    def test_embedding_key_is_deterministic(self):
        k1 = RedisService._embedding_key("some text")
        k2 = RedisService._embedding_key("some text")
        assert k1 == k2
        assert k1.startswith("serpent:embed:")

    def test_embedding_key_differs_by_text(self):
        k1 = RedisService._embedding_key("text a")
        k2 = RedisService._embedding_key("text b")
        assert k1 != k2


class TestRedisServiceOperations:
    """Operations with mocked Redis client."""

    async def test_get_query_cache_returns_parsed_json(self):
        svc = RedisService()
        svc._client = AsyncMock()
        cached = {"answer": "test", "sources": []}
        svc._client.get.return_value = json.dumps(cached)

        result = await svc.get_query_cache("query", "naive", "default")
        assert result == cached

    async def test_get_query_cache_returns_none_on_miss(self):
        svc = RedisService()
        svc._client = AsyncMock()
        svc._client.get.return_value = None

        result = await svc.get_query_cache("query", "naive", "default")
        assert result is None

    async def test_set_query_cache_calls_setex(self):
        svc = RedisService()
        svc._client = AsyncMock()
        await svc.set_query_cache("q", "naive", "c", {"answer": "a"}, ttl=600)
        svc._client.setex.assert_called_once()

    async def test_store_trace_uses_correct_key(self):
        svc = RedisService()
        svc._client = AsyncMock()
        await svc.store_trace("trace-123", {"data": "test"}, ttl=3600)
        svc._client.setex.assert_called_once()
        key = svc._client.setex.call_args[0][0]
        assert key == "serpent:trace:trace-123"

    async def test_get_trace_returns_parsed_json(self):
        svc = RedisService()
        svc._client = AsyncMock()
        trace_data = {"trace_id": "abc", "steps": []}
        svc._client.get.return_value = json.dumps(trace_data)

        result = await svc.get_trace("abc")
        assert result == trace_data

    async def test_health_check_returns_ping_result(self):
        svc = RedisService()
        svc._client = AsyncMock()
        svc._client.ping.return_value = True
        assert await svc.health_check() is True

    async def test_health_check_returns_false_on_error(self):
        svc = RedisService()
        svc._client = AsyncMock()
        svc._client.ping.side_effect = ConnectionError("refused")
        assert await svc.health_check() is False

    async def test_set_embedding_cache(self):
        svc = RedisService()
        svc._client = AsyncMock()
        embedding = [0.1] * 10
        await svc.set_embedding_cache("text", embedding, ttl=3600)
        svc._client.setex.assert_called_once()

    async def test_get_embedding_cache_returns_parsed(self):
        svc = RedisService()
        svc._client = AsyncMock()
        svc._client.get.return_value = json.dumps([0.1, 0.2, 0.3])
        result = await svc.get_embedding_cache("text")
        assert result == [0.1, 0.2, 0.3]

    async def test_get_embedding_cache_returns_none_on_miss(self):
        svc = RedisService()
        svc._client = AsyncMock()
        svc._client.get.return_value = None
        result = await svc.get_embedding_cache("text")
        assert result is None

    async def test_get_trace_returns_none_on_miss(self):
        svc = RedisService()
        svc._client = AsyncMock()
        svc._client.get.return_value = None
        result = await svc.get_trace("missing")
        assert result is None

    async def test_invalidate_collection_cache(self):
        svc = RedisService()
        mock_client = AsyncMock()
        mock_client.scan_iter = lambda **kwargs: AsyncIterator(
            ["serpent:query:naive:test:abc"]
        )
        mock_client.delete = AsyncMock()
        svc._client = mock_client
        await svc.invalidate_collection_cache("test")
        mock_client.delete.assert_called_once()

    async def test_close(self):
        svc = RedisService()
        svc._client = AsyncMock()
        await svc.close()
        svc._client.close.assert_called_once()

    async def test_close_without_client(self):
        svc = RedisService()
        svc._client = None
        await svc.close()  # Should not raise


class AsyncIterator:
    """Helper async iterator for mocking scan_iter."""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration
