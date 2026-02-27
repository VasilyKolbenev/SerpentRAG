"""
Redis cache service.
"""

import json
import hashlib
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("serpent.cache")


class RedisService:
    """Redis-based caching for queries and embeddings."""

    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None

    async def initialize(self) -> None:
        """Connect to Redis."""
        self._client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis service initialized")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()

    # ── Query Cache ──

    async def get_query_cache(
        self, query: str, strategy: str, collection: str
    ) -> Optional[dict]:
        """Get cached query result."""
        key = self._query_key(query, strategy, collection)
        data = await self._client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_query_cache(
        self,
        query: str,
        strategy: str,
        collection: str,
        result: dict,
        ttl: int = 3600,
    ) -> None:
        """Cache a query result with TTL."""
        key = self._query_key(query, strategy, collection)
        await self._client.setex(key, ttl, json.dumps(result, default=str))

    async def invalidate_collection_cache(self, collection: str) -> None:
        """Invalidate all cached queries for a collection."""
        pattern = f"serpent:query:*:{collection}:*"
        async for key in self._client.scan_iter(match=pattern, count=100):
            await self._client.delete(key)

    # ── Trace Cache ──

    async def store_trace(self, trace_id: str, trace_data: dict, ttl: int = 86400) -> None:
        """Store pipeline trace in Redis (24h TTL)."""
        key = f"serpent:trace:{trace_id}"
        await self._client.setex(key, ttl, json.dumps(trace_data, default=str))

    async def get_trace(self, trace_id: str) -> Optional[dict]:
        """Get pipeline trace from Redis."""
        key = f"serpent:trace:{trace_id}"
        data = await self._client.get(key)
        if data:
            return json.loads(data)
        return None

    # ── Embedding Cache ──

    async def get_embedding_cache(self, text: str) -> Optional[list[float]]:
        """Get cached embedding for text."""
        key = self._embedding_key(text)
        data = await self._client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_embedding_cache(
        self, text: str, embedding: list[float], ttl: int = 86400
    ) -> None:
        """Cache an embedding (24h TTL)."""
        key = self._embedding_key(text)
        await self._client.setex(key, ttl, json.dumps(embedding))

    # ── MemoRAG Memory ──

    async def get_memo_memory(self, collection: str) -> Optional[str]:
        """Get cached collection memory for MemoRAG."""
        key = f"serpent:memo:{collection}:memory"
        return await self._client.get(key)

    async def set_memo_memory(
        self, collection: str, memory: str, ttl: int = 86400
    ) -> None:
        """Cache collection memory for MemoRAG (24h TTL)."""
        key = f"serpent:memo:{collection}:memory"
        await self._client.setex(key, ttl, memory)

    # ── Advisor Sessions ──

    async def get_advisor_session(self, session_id: str) -> Optional[list[dict]]:
        """Get advisor chatbot conversation history."""
        key = f"serpent:advisor:{session_id}"
        data = await self._client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_advisor_session(
        self, session_id: str, history: list[dict], ttl: int = 3600
    ) -> None:
        """Save advisor chatbot conversation history (1h TTL)."""
        key = f"serpent:advisor:{session_id}"
        await self._client.setex(key, ttl, json.dumps(history))

    # ── Chat Sessions ──

    async def get_chat_session(
        self, user_id: str, session_id: str
    ) -> Optional[list[dict]]:
        """Get chat conversation history for a user session."""
        key = f"serpent:chat:{user_id}:{session_id}"
        data = await self._client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_chat_session(
        self,
        user_id: str,
        session_id: str,
        history: list[dict],
        ttl: int = 14400,
    ) -> None:
        """Save chat conversation history (4h TTL)."""
        key = f"serpent:chat:{user_id}:{session_id}"
        await self._client.setex(key, ttl, json.dumps(history))

    async def delete_chat_session(self, user_id: str, session_id: str) -> bool:
        """Delete a chat session. Returns True if key existed."""
        key = f"serpent:chat:{user_id}:{session_id}"
        deleted = await self._client.delete(key)
        return deleted > 0

    async def list_chat_sessions(self, user_id: str) -> list[dict]:
        """List all active chat sessions for a user via SCAN."""
        pattern = f"serpent:chat:{user_id}:*"
        sessions: list[dict] = []

        async for key in self._client.scan_iter(match=pattern, count=100):
            # Extract session_id from key
            session_id = key.split(":")[-1]
            ttl = await self._client.ttl(key)
            sessions.append({"session_id": session_id, "ttl_seconds": ttl})

        return sessions

    # ── File Hash Dedup ──

    async def get_file_hash(self, collection: str, file_hash: str) -> Optional[str]:
        """Get existing doc_id for a file content hash. Returns None if new."""
        key = f"serpent:file_hash:{collection}:{file_hash}"
        return await self._client.get(key)

    async def set_file_hash(
        self, collection: str, file_hash: str, doc_id: str, ttl: int = 86400
    ) -> None:
        """Store file content hash → doc_id mapping (24h TTL)."""
        key = f"serpent:file_hash:{collection}:{file_hash}"
        await self._client.setex(key, ttl, doc_id)

    async def delete_file_hash(self, collection: str, file_hash: str) -> None:
        """Remove file hash mapping (called on document deletion)."""
        key = f"serpent:file_hash:{collection}:{file_hash}"
        await self._client.delete(key)

    # ── Document Status ──

    async def list_doc_statuses(
        self, collection: str | None = None
    ) -> list[dict]:
        """List all document statuses from Redis via SCAN."""
        pattern = "serpent:trace:doc_status:*"
        documents: list[dict] = []

        async for key in self._client.scan_iter(match=pattern, count=100):
            data = await self._client.get(key)
            if data:
                doc = json.loads(data)
                if collection is None or doc.get("collection") == collection:
                    documents.append(doc)

        documents.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        return documents

    async def delete_doc_status(self, doc_id: str) -> bool:
        """Delete a document status key from Redis. Returns True if key existed."""
        key = f"serpent:trace:doc_status:{doc_id}"
        deleted = await self._client.delete(key)
        return deleted > 0

    # ── Health ──

    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            return await self._client.ping()
        except Exception:
            return False

    # ── Key helpers ──

    @staticmethod
    def _query_key(query: str, strategy: str, collection: str) -> str:
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        return f"serpent:query:{strategy}:{collection}:{query_hash}"

    @staticmethod
    def _embedding_key(text: str) -> str:
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"serpent:embed:{text_hash}"
