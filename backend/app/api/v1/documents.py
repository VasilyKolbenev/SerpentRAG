"""
Document upload and management endpoints.
"""

import os
import uuid
from datetime import datetime

import aiofiles
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.config import settings
from app.schemas.document import DocumentDetail, DocumentResponse

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

    doc_id = str(uuid.uuid4())

    # Save file to disk
    upload_dir = os.path.join(settings.upload_dir, doc_id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Dispatch Celery task for background processing
    from app.workers.tasks.ingest import process_document_task

    process_document_task.delay(
        doc_id=doc_id,
        file_path=file_path,
        collection=collection,
        filename=file.filename,
        content_type=file.content_type,
        file_size=len(content),
    )

    return DocumentResponse(
        id=doc_id,
        filename=file.filename,
        status="processing",
        chunks=0,
        collection=collection,
        file_size=len(content),
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
async def get_document(doc_id: str, req: Request):
    """Get document status and details."""
    # Check Redis for processing status
    cache = req.app.state.cache
    status_data = await cache.get_trace(f"doc_status:{doc_id}")

    if status_data:
        return DocumentDetail(**status_data)

    raise HTTPException(404, f"Document {doc_id} not found")
