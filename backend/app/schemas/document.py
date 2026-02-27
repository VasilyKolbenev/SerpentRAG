"""
Document upload/response schemas.
"""

from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    chunks: int
    collection: str
    file_size: int = 0
    created_at: str
    processing_phase: Optional[str] = None
    content_hash: Optional[str] = None


class DocumentDetail(DocumentResponse):
    content_type: str
    error_message: Optional[str] = None
    metadata: dict = {}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DeleteDocumentResponse(BaseModel):
    deleted: bool
    doc_id: str
    chunks_removed: int


class CollectionInfo(BaseModel):
    name: str
    documents: int
    chunks: int


class CollectionListResponse(BaseModel):
    collections: list[CollectionInfo]
