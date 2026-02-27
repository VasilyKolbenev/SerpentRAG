"""
Tests for DocumentProcessorService — parse, chunk, embed+store pipeline.
"""

import json
import os
import tempfile
import uuid
from unittest.mock import AsyncMock

import pytest

from app.services.document_processor import DocumentProcessorService

# Stable UUIDs for tests (uuid5 needs a valid UUID as document_id)
TEST_DOC_ID = str(uuid.uuid4())
EMPTY_DOC_ID = str(uuid.uuid4())
META_DOC_ID = str(uuid.uuid4())


@pytest.fixture
def doc_processor(
    mock_embedding_service: AsyncMock,
    mock_vector_store: AsyncMock,
) -> DocumentProcessorService:
    """DocumentProcessorService with mock embedding and vector store."""
    return DocumentProcessorService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )


def _write_temp(suffix: str, content: str) -> str:
    """Write content to a temp file (closed) and return path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestDocumentProcessorParsing:
    """File parsing — text, JSON."""

    def test_read_text_file(self):
        path = _write_temp(".txt", "Hello world\nSecond line")
        try:
            text = DocumentProcessorService._read_text(path)
            assert "Hello world" in text
            assert "Second line" in text
        finally:
            os.unlink(path)

    def test_parse_json_file(self):
        data = {"key": "value", "items": [1, 2, 3]}
        path = _write_temp(".json", json.dumps(data))
        try:
            text = DocumentProcessorService._parse_json(path)
            assert '"key": "value"' in text
        finally:
            os.unlink(path)


class TestDocumentProcessorPipeline:
    """Full pipeline — process_file with mocked services."""

    async def test_process_text_file_returns_chunk_count(
        self, doc_processor: DocumentProcessorService, mock_embedding_service, mock_vector_store
    ):
        content = "This is a test document. " * 100
        path = _write_temp(".txt", content)
        try:
            mock_embedding_service.embed.return_value = [[0.1] * 1024] * 50
            chunk_count = await doc_processor.process_file(
                file_path=path,
                document_id=TEST_DOC_ID,
                collection="test",
            )
            assert chunk_count > 0
            mock_vector_store.ensure_collection.assert_called_once_with("test")
            mock_embedding_service.embed.assert_called_once()
            mock_vector_store.upsert.assert_called_once()
        finally:
            os.unlink(path)

    async def test_process_empty_file_raises(self, doc_processor: DocumentProcessorService):
        path = _write_temp(".txt", "")
        try:
            with pytest.raises(ValueError, match="No text extracted"):
                await doc_processor.process_file(
                    file_path=path,
                    document_id=EMPTY_DOC_ID,
                    collection="test",
                )
        finally:
            os.unlink(path)

    async def test_process_file_with_metadata(
        self, doc_processor: DocumentProcessorService, mock_embedding_service, mock_vector_store
    ):
        content = "Test content for metadata test. " * 50
        path = _write_temp(".txt", content)
        try:
            mock_embedding_service.embed.return_value = [[0.1] * 1024] * 20
            await doc_processor.process_file(
                file_path=path,
                document_id=META_DOC_ID,
                collection="test",
                metadata={"author": "test"},
            )
            upsert_call = mock_vector_store.upsert.call_args
            payloads = upsert_call.kwargs.get("payloads") or upsert_call[1].get("payloads")
            if payloads is None:
                payloads = upsert_call[0][3] if len(upsert_call[0]) > 3 else []
            assert any("author" in p for p in payloads)
        finally:
            os.unlink(path)
