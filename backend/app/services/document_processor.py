"""
Document processing service — parse, chunk, embed, store.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.services.embedding import EmbeddingService
from app.services.vector_store import QdrantService

logger = logging.getLogger("serpent.document_processor")


class DocumentProcessorService:
    """Handles document ingestion pipeline: parse → chunk → embed → store."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantService,
    ) -> None:
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=128,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    async def process_file(
        self,
        file_path: str,
        document_id: str,
        collection: str = "default",
        metadata: Optional[dict] = None,
    ) -> int:
        """Process a document file end-to-end. Returns chunk count."""
        # 1. Parse
        text = await self._parse_file(file_path)
        if not text.strip():
            raise ValueError(f"No text extracted from {file_path}")

        # 2. Chunk
        chunks = self._splitter.split_text(text)
        logger.info(
            "Document chunked",
            extra={"doc_id": document_id, "chunks": len(chunks)},
        )

        # 3. Ensure collection exists
        await self._vector_store.ensure_collection(collection)

        # 4. Embed in batches
        embeddings = await self._embedding.embed(chunks, batch_size=64)

        # 5. Prepare payloads
        file_meta = metadata or {}
        filename = Path(file_path).name
        ids = []
        payloads = []
        for i, (chunk, _emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid5(uuid.UUID(document_id), str(i)))
            ids.append(chunk_id)
            payloads.append({
                "content": chunk,
                "document_id": document_id,
                "chunk_index": i,
                "source": filename,
                "collection": collection,
                **file_meta,
            })

        # 6. Upsert to Qdrant
        await self._vector_store.upsert(
            collection_name=collection,
            ids=ids,
            vectors=embeddings,
            payloads=payloads,
        )

        logger.info(
            "Document indexed",
            extra={
                "doc_id": document_id,
                "collection": collection,
                "chunks": len(chunks),
            },
        )
        return len(chunks)

    async def _parse_file(self, file_path: str) -> str:
        """Extract text from file based on extension."""
        ext = Path(file_path).suffix.lower()

        if ext in (".txt", ".md"):
            return self._read_text(file_path)
        elif ext == ".pdf":
            return self._parse_pdf(file_path)
        elif ext == ".docx":
            return self._parse_docx(file_path)
        elif ext == ".csv":
            return self._parse_csv(file_path)
        elif ext == ".json":
            return self._parse_json(file_path)
        else:
            # Try unstructured as fallback
            return self._parse_unstructured(file_path)

    @staticmethod
    def _read_text(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    @staticmethod
    def _parse_docx(file_path: str) -> str:
        from docx import Document

        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    @staticmethod
    def _parse_csv(file_path: str) -> str:
        import csv

        rows = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(" | ".join(row))
        return "\n".join(rows)

    @staticmethod
    def _parse_json(file_path: str) -> str:
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _parse_unstructured(file_path: str) -> str:
        try:
            from unstructured.partition.auto import partition

            elements = partition(filename=file_path)
            return "\n\n".join(str(el) for el in elements)
        except ImportError:
            logger.warning("unstructured not available, reading as plain text")
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
