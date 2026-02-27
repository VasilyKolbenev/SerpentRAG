"""
Document ingestion Celery tasks.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

import redis

from app.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger("serpent.worker.ingest")


def _get_redis():
    """Get synchronous Redis client for worker."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def _update_doc_status(doc_id: str, status_data: dict) -> None:
    """Update document processing status in Redis."""
    r = _get_redis()
    key = f"serpent:trace:doc_status:{doc_id}"
    r.setex(key, 86400, json.dumps(status_data, default=str))


@celery_app.task(
    bind=True,
    queue="ingest",
    max_retries=3,
    default_retry_delay=30,
)
def process_document_task(
    self,
    doc_id: str,
    file_path: str,
    collection: str,
    filename: str,
    content_type: str,
    file_size: int,
    content_hash: str = "",
):
    """Process an uploaded document: parse, chunk, embed, store."""
    import asyncio

    logger.info(f"Processing document {doc_id}: {filename}")

    base_status = {
        "id": doc_id,
        "filename": filename,
        "collection": collection,
        "content_type": content_type,
        "file_size": file_size,
        "content_hash": content_hash,
        "created_at": datetime.utcnow().isoformat(),
    }

    _update_doc_status(doc_id, {
        **base_status,
        "status": "processing",
        "processing_phase": "queued",
        "chunks": 0,
    })

    def update_phase(phase: str) -> None:
        """Sync callback — updates processing phase in Redis."""
        _update_doc_status(doc_id, {
            **base_status,
            "status": "processing",
            "processing_phase": phase,
            "chunks": 0,
        })

    try:
        # Run async processing in sync context
        chunk_count = asyncio.run(
            _async_process(
                doc_id, file_path, collection, filename, update_phase,
            )
        )

        _update_doc_status(doc_id, {
            **base_status,
            "status": "indexed",
            "processing_phase": None,
            "chunks": chunk_count,
        })

        logger.info(f"Document {doc_id} indexed: {chunk_count} chunks")
        return {"doc_id": doc_id, "chunks": chunk_count, "status": "indexed"}

    except Exception as exc:
        logger.error(f"Document {doc_id} processing failed: {exc}")

        _update_doc_status(doc_id, {
            **base_status,
            "status": "failed",
            "processing_phase": None,
            "chunks": 0,
            "error_message": str(exc),
        })

        raise self.retry(exc=exc)


async def _async_process(
    doc_id: str,
    file_path: str,
    collection: str,
    filename: str,
    phase_callback: "Callable[[str], None] | None" = None,
) -> int:
    """Async document processing logic."""
    from app.services.document_processor import DocumentProcessorService
    from app.services.embedding import EmbeddingService
    from app.services.graph_store import Neo4jService
    from app.services.llm import LLMService
    from app.services.vector_store import QdrantService

    # Initialize services for worker
    embedding = EmbeddingService()
    await embedding.initialize()

    vector_store = QdrantService()
    await vector_store.initialize()

    # Initialize graph store (optional — graceful degradation if Neo4j unavailable)
    graph_store = None
    llm_service = None
    try:
        graph_store = Neo4jService()
        await graph_store.initialize()
        llm_service = LLMService()
        logger.info("Graph store + LLM initialized for entity extraction")
    except Exception as exc:
        logger.warning(
            "Neo4j unavailable, skipping entity extraction",
            extra={"error": str(exc)},
        )
        graph_store = None
        llm_service = None

    processor = DocumentProcessorService(
        embedding_service=embedding,
        vector_store=vector_store,
        graph_store=graph_store,
        llm_service=llm_service,
    )

    try:
        chunk_count = await processor.process_file(
            file_path=file_path,
            document_id=doc_id,
            collection=collection,
            metadata={"source": filename},
            phase_callback=phase_callback,
        )
        return chunk_count
    finally:
        await vector_store.close()
        if graph_store:
            await graph_store.close()
