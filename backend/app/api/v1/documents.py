"""
Document upload and management endpoints.
"""

import hashlib
import logging
import os
import pathlib
import shutil
import uuid
from datetime import datetime
from typing import Optional

import aiofiles
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile

from app.config import settings
from app.schemas.document import (
    DeleteDocumentResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentResponse,
)

logger = logging.getLogger("serpent.api.documents")

router = APIRouter(tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/documents/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    req: Request,
    file: UploadFile = File(...),
    collection: str = "default",
):
    """Upload and index a document."""
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    # A6: Chunked reading with size limit to prevent OOM
    max_size = settings.max_upload_size
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(
                413,
                f"File too large (max {max_size // 1024 // 1024}MB)",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    # Check for duplicate via SHA256 content hash
    content_hash = hashlib.sha256(content).hexdigest()
    cache = req.app.state.cache
    existing_doc_id = await cache.get_file_hash(collection, content_hash)

    if existing_doc_id:
        logger.info(
            "Duplicate file detected",
            extra={"collection": collection, "existing_doc_id": existing_doc_id},
        )
        # Return existing document info
        status_data = await cache.get_trace(f"doc_status:{existing_doc_id}")
        return DocumentResponse(
            id=existing_doc_id,
            filename=status_data.get("filename", file.filename) if status_data else file.filename,
            status="already_exists",
            chunks=status_data.get("chunks", 0) if status_data else 0,
            collection=collection,
            file_size=len(content),
            created_at=status_data.get("created_at", "") if status_data else "",
            processing_phase=None,
            content_hash=content_hash,
        )

    doc_id = str(uuid.uuid4())

    # A1: Sanitize filename to prevent path traversal
    safe_name = pathlib.PurePosixPath(file.filename).name
    if not safe_name or safe_name.startswith("."):
        raise HTTPException(400, "Invalid filename")

    # Save file to disk
    upload_dir = os.path.join(settings.upload_dir, doc_id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)

    # Verify resolved path is inside upload_dir (defense in depth)
    if not os.path.realpath(file_path).startswith(os.path.realpath(upload_dir)):
        raise HTTPException(400, "Invalid filename")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # B7: Atomic set — if another concurrent upload already stored this hash,
    # return the existing document instead of creating a duplicate.
    hash_set = await cache.set_file_hash(collection, content_hash, doc_id)
    if not hash_set:
        # Another upload won the race — clean up and return existing
        shutil.rmtree(upload_dir, ignore_errors=True)
        existing_doc_id = await cache.get_file_hash(collection, content_hash)
        status_data = await cache.get_trace(f"doc_status:{existing_doc_id}") if existing_doc_id else None
        return DocumentResponse(
            id=existing_doc_id or doc_id,
            filename=status_data.get("filename", safe_name) if status_data else safe_name,
            status="already_exists",
            chunks=status_data.get("chunks", 0) if status_data else 0,
            collection=collection,
            file_size=len(content),
            created_at=status_data.get("created_at", "") if status_data else "",
            processing_phase=None,
            content_hash=content_hash,
        )

    # Dispatch Celery task for background processing
    from app.workers.tasks.ingest import process_document_task

    process_document_task.delay(
        doc_id=doc_id,
        file_path=file_path,
        collection=collection,
        filename=safe_name,
        content_type=file.content_type,
        file_size=len(content),
        content_hash=content_hash,
    )

    return DocumentResponse(
        id=doc_id,
        filename=safe_name,
        status="processing",
        chunks=0,
        collection=collection,
        file_size=len(content),
        created_at=datetime.utcnow().isoformat(),
        content_hash=content_hash,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    req: Request,
    collection: Optional[str] = Query(None, description="Filter by collection"),
    limit: int = Query(50, ge=1, le=200, description="Max documents per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List documents with pagination and optional collection filter."""
    cache = req.app.state.cache
    documents = await cache.list_doc_statuses(collection=collection)

    # B12: Apply pagination after fetch (Redis SCAN doesn't support offset natively)
    total = len(documents)
    paginated = documents[offset : offset + limit]

    doc_responses = [
        DocumentResponse(
            id=doc.get("id", ""),
            filename=doc.get("filename", "unknown"),
            status=doc.get("status", "unknown"),
            chunks=doc.get("chunks", 0),
            collection=doc.get("collection", "default"),
            file_size=doc.get("file_size", 0),
            created_at=doc.get("created_at", ""),
            processing_phase=doc.get("processing_phase"),
            content_hash=doc.get("content_hash"),
        )
        for doc in paginated
    ]

    return DocumentListResponse(documents=doc_responses, total=total)


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
async def get_document(doc_id: str, req: Request):
    """Get document status and details."""
    # Check Redis for processing status
    cache = req.app.state.cache
    status_data = await cache.get_trace(f"doc_status:{doc_id}")

    if status_data:
        return DocumentDetail(**status_data)

    raise HTTPException(404, f"Document {doc_id} not found")


@router.delete("/documents/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(doc_id: str, req: Request):
    """Delete a document and all its data (vectors, entities, cache, files)."""
    cache = req.app.state.cache
    vector_store = req.app.state.vector_store

    # Verify document exists
    status_data = await cache.get_trace(f"doc_status:{doc_id}")
    if not status_data:
        raise HTTPException(404, f"Document {doc_id} not found")

    collection = status_data.get("collection", "default")
    chunks_removed = 0

    # 1. Delete vectors from Qdrant
    try:
        chunks_removed = await vector_store.delete_by_filter(
            collection_name=collection,
            field="document_id",
            value=doc_id,
        )
    except Exception as exc:
        logger.warning(
            "Failed to delete vectors from Qdrant",
            extra={"doc_id": doc_id, "error": str(exc)},
        )

    # 2. Delete entities from Neo4j (graceful — may not be available)
    graph_store = getattr(req.app.state, "graph_store", None)
    if graph_store:
        try:
            await graph_store.delete_by_document(
                document_id=doc_id,
                collection=collection,
            )
        except Exception as exc:
            logger.warning(
                "Failed to delete entities from Neo4j",
                extra={"doc_id": doc_id, "error": str(exc)},
            )

    # 3. Delete file hash mapping from Redis
    content_hash = status_data.get("content_hash")
    if content_hash:
        await cache.delete_file_hash(collection, content_hash)

    # 4. Delete status from Redis
    await cache.delete_doc_status(doc_id)

    # 5. Delete uploaded files
    upload_dir = os.path.join(settings.upload_dir, doc_id)
    if os.path.isdir(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)

    logger.info(
        "Document deleted",
        extra={
            "doc_id": doc_id,
            "collection": collection,
            "chunks_removed": chunks_removed,
        },
    )

    return DeleteDocumentResponse(
        deleted=True,
        doc_id=doc_id,
        chunks_removed=chunks_removed,
    )
