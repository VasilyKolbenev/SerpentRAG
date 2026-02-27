"""
Qdrant vector store service.
"""

import logging
from typing import Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger("serpent.vector_store")


class SearchResult:
    """Single vector search result."""

    def __init__(self, id: str, content: str, score: float, metadata: dict) -> None:
        self.id = id
        self.content = content
        self.score = score
        self.metadata = metadata


class QdrantService:
    """Manages Qdrant vector store operations."""

    def __init__(self) -> None:
        self._client: Optional[AsyncQdrantClient] = None

    async def initialize(self) -> None:
        """Connect to Qdrant."""
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
        )
        logger.info("Qdrant service initialized", extra={"url": settings.qdrant_url})

    async def close(self) -> None:
        """Close Qdrant connection."""
        if self._client:
            await self._client.close()

    async def ensure_collection(
        self,
        collection_name: str,
        dimensions: int = settings.embedding_dimensions,
    ) -> None:
        """Create collection if it doesn't exist."""
        collections = await self._client.get_collections()
        existing = {c.name for c in collections.collections}

        if collection_name not in existing:
            try:
                await self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=dimensions,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection", extra={"collection": collection_name})
            except Exception as exc:
                if "already exists" in str(exc):
                    logger.debug("Collection already exists (race condition)", extra={"collection": collection_name})
                else:
                    raise

    async def upsert(
        self,
        collection_name: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        """Upsert vectors with payloads."""
        points = [
            PointStruct(id=id_, vector=vec, payload=payload)
            for id_, vec, payload in zip(ids, vectors, payloads)
        ]

        await self._client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True,
        )

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[dict] = None,
    ) -> list[SearchResult]:
        """Search for similar vectors."""
        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        results = await self._client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
        )

        return [
            SearchResult(
                id=str(r.id),
                content=r.payload.get("content", ""),
                score=r.score,
                metadata={
                    k: v
                    for k, v in r.payload.items()
                    if k != "content"
                },
            )
            for r in results
        ]

    async def delete_by_filter(
        self,
        collection_name: str,
        field: str,
        value: str,
    ) -> int:
        """Delete points matching a payload filter. Returns count of deleted points."""
        count_result = await self._client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key=field, match=MatchValue(value=value))]
            ),
            exact=True,
        )
        points_count = count_result.count

        if points_count > 0:
            await self._client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key=field, match=MatchValue(value=value))]
                ),
                wait=True,
            )
            logger.info(
                "Deleted points by filter",
                extra={
                    "collection": collection_name,
                    "field": field,
                    "value": value,
                    "count": points_count,
                },
            )

        return points_count

    async def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        await self._client.delete_collection(collection_name=collection_name)

    async def get_collections(self) -> list[str]:
        """List all collection names."""
        result = await self._client.get_collections()
        return [c.name for c in result.collections]

    async def collection_info(self, collection_name: str) -> dict:
        """Get collection point count and status."""
        info = await self._client.get_collection(collection_name=collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "status": info.status.value,
        }

    async def scroll(
        self,
        collection_name: str,
        limit: int = 100,
        with_payload: bool = True,
    ) -> list[SearchResult]:
        """Scroll through collection points without a query vector.

        Used by MemoRAG to sample collection chunks for memory building.
        """
        results, _ = await self._client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=with_payload,
            with_vectors=False,
        )
        return [
            SearchResult(
                id=str(r.id),
                content=r.payload.get("content", "") if r.payload else "",
                score=1.0,
                metadata={
                    k: v
                    for k, v in (r.payload or {}).items()
                    if k != "content"
                },
            )
            for r in results
        ]

    async def health_check(self) -> bool:
        """Check Qdrant connectivity."""
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False
