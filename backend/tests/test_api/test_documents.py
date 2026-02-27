"""
Tests for document endpoints — upload, get status.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestDocumentUpload:
    """POST /documents/upload — file upload + processing."""

    async def test_upload_unsupported_type_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/documents/upload",
            files={"file": ("test.exe", b"binary", "application/octet-stream")},
        )
        assert response.status_code == 400

    async def test_upload_valid_text_file(self, client: AsyncClient, app):
        # The endpoint does: from app.workers.tasks.ingest import process_document_task
        # We need to make that import resolve to a mock
        mock_task = MagicMock()
        mock_task.delay = MagicMock()

        # Mock aiofiles context manager
        mock_file = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_file)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        # Create a fake ingest module so the import works
        fake_ingest = MagicMock()
        fake_ingest.process_document_task = mock_task

        # Ensure dedup check returns None (new file) and atomic set succeeds
        app.state.cache.get_file_hash.return_value = None
        app.state.cache.set_file_hash.return_value = True

        with (
            patch("app.api.v1.documents.os.makedirs"),
            patch("app.api.v1.documents.os.path.realpath", side_effect=lambda p: p),
            patch("app.api.v1.documents.aiofiles.open", return_value=mock_ctx),
            patch.dict(sys.modules, {"app.workers.tasks.ingest": fake_ingest}),
        ):
            response = await client.post(
                "/documents/upload",
                files={"file": ("test.txt", b"Hello world content", "text/plain")},
                data={"collection": "test"},
            )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["filename"] == "test.txt"
        assert data["status"] == "processing"

        # Restore mock defaults
        app.state.cache.get_file_hash.return_value = None
        app.state.cache.set_file_hash.return_value = True


class TestDocumentGet:
    """GET /documents/{doc_id} — status polling."""

    async def test_get_document_not_found(self, client: AsyncClient):
        response = await client.get("/documents/nonexistent-id")
        assert response.status_code == 404

    async def test_get_document_returns_cached_status(self, client: AsyncClient, app):
        doc_data = {
            "id": "doc-123",
            "filename": "test.pdf",
            "status": "indexed",
            "chunks": 42,
            "collection": "default",
            "file_size": 1024,
            "created_at": "2024-01-01T00:00:00",
            "content_type": "application/pdf",
        }
        app.state.cache.get_trace.return_value = doc_data

        response = await client.get("/documents/doc-123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc-123"
        assert data["status"] == "indexed"
        assert data["chunks"] == 42

        # Restore
        app.state.cache.get_trace.return_value = None
