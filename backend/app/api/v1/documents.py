"""
Document upload and management endpoints.
"""

import hashlib
import logging
import os
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


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    req: Request,
    file: UploadFile = File(...),
    collection: str = "default",
):
    """Upload and index a document."""
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    if file.size and file.size > settings.max_upload_size:
        raise HTTPException(400, f"File too large (max {settings.max_upload_size // 1024 // 1024}MB)")

    content = await file.read()

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

    # Save file to disk
    upload_dir = os.path.join(settings.upload_dir, doc_id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Store content hash → doc_id mapping in Redis
    await cache.set_file_hash(collection, content_hash, doc_id)

    # Dispatch Celery task for background processing
    from app.workers.tasks.ingest import process_document_task

    process_document_task.delay(
        doc_id=doc_id,
        file_path=file_path,
        collection=collection,
        filename=file.filename,
        content_type=file.content_type,
        file_size=len(content),
        content_hash=content_hash,
    )

    return DocumentResponse(
        id=doc_id,
        filename=file.filename,
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
):
    """List all documents with their processing status."""
    cache = req.app.state.cache
    documents = await cache.list_doc_statuses(collection=collection)

    doc_responses = []
    for doc in documents:
        doc_responses.append(
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
        )

    return DocumentListResponse(documents=doc_responses, total=len(doc_responses))


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
