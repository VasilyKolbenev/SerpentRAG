"""
Document processing service — parse, chunk, embed, store, extract entities.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Callable, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.services.embedding import EmbeddingService
from app.services.vector_store import QdrantService

logger = logging.getLogger("serpent.document_processor")

_ENTITY_EXTRACTION_PROMPT = """Extract named entities and relationships from the following text.
Return a JSON object with two arrays:

1. "entities": array of objects with "name" (string) and "type" (one of: PERSON, ORGANIZATION, CONCEPT, TECHNOLOGY, LOCATION, DOCUMENT, EVENT)
2. "relationships": array of objects with "source" (entity name), "target" (entity name), "type" (relationship label, e.g. "WORKS_FOR", "RELATED_TO", "PART_OF", "USES", "REGULATES")

Rules:
- Extract only meaningful, specific entities (skip generic words like "system", "data")
- Normalize entity names (e.g., "ML" → "Machine Learning", "ИИ" → "Искусственный интеллект")
- Relationships should be meaningful and directional
- If no clear entities found, return empty arrays
- Return ONLY valid JSON, no explanations

Text:
{chunk_text}

Response (JSON only):"""

_ENTITY_BATCH_SIZE = 5
_ENTITY_EXTRACTION_MODEL = "gpt-4o-mini"


class DocumentProcessorService:
    """Handles document ingestion pipeline: parse → chunk → embed → store → extract entities."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantService,
        graph_store: Optional[object] = None,
        llm_service: Optional[object] = None,
    ) -> None:
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._llm_service = llm_service
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
        phase_callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """Process a document file end-to-end. Returns chunk count.

        Args:
            phase_callback: Optional sync callback called with phase name
                before each processing step.
        """
        def _notify(phase: str) -> None:
            if phase_callback:
                phase_callback(phase)

        # 1. Parse
        _notify("parsing")
        text = await self._parse_file(file_path)
        if not text.strip():
            raise ValueError(f"No text extracted from {file_path}")

        # 2. Chunk
        _notify("chunking")
        chunks = self._splitter.split_text(text)
        logger.info(
            "Document chunked",
            extra={"doc_id": document_id, "chunks": len(chunks)},
        )

        # 3. Ensure collection exists
        await self._vector_store.ensure_collection(collection)

        # 4. Embed in batches
        _notify("embedding")
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
        _notify("storing")
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

        # 7. Extract entities and store in Neo4j (optional, graceful degradation)
        if self._graph_store and self._llm_service:
            _notify("extracting_entities")
            try:
                entity_count, rel_count = await self._extract_and_store_entities(
                    chunks=chunks,
                    document_id=document_id,
                    collection=collection,
                )
                logger.info(
                    "Entity extraction complete",
                    extra={
                        "doc_id": document_id,
                        "entities": entity_count,
                        "relationships": rel_count,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "Entity extraction failed, document indexed without graph",
                    extra={"doc_id": document_id, "error": str(exc)},
                )

        return len(chunks)

    async def _extract_and_store_entities(
        self,
        chunks: list[str],
        document_id: str,
        collection: str,
    ) -> tuple[int, int]:
        """Extract entities from chunks via LLM and store in Neo4j.

        Processes chunks in batches to minimize LLM calls.
        Returns (entity_count, relationship_count).
        """
        total_entities = 0
        total_relationships = 0
        all_entities: list[dict] = []
        all_relationships: list[dict] = []

        for i in range(0, len(chunks), _ENTITY_BATCH_SIZE):
            batch = chunks[i:i + _ENTITY_BATCH_SIZE]
            combined_text = "\n\n---\n\n".join(batch)

            prompt = _ENTITY_EXTRACTION_PROMPT.format(chunk_text=combined_text)

            try:
                raw_response = await self._llm_service.structured_extract(
                    prompt=prompt,
                    model=_ENTITY_EXTRACTION_MODEL,
                    temperature=0.0,
                )

                parsed = self._parse_entity_response(raw_response)
                if parsed:
                    all_entities.extend(parsed.get("entities", []))
                    all_relationships.extend(parsed.get("relationships", []))

            except Exception as exc:
                logger.warning(
                    "Entity extraction failed for batch",
                    extra={"batch_start": i, "error": str(exc)},
                )
                continue

        # Deduplicate entities by (name, type)
        seen_entities: set[tuple[str, str]] = set()
        unique_entities: list[dict] = []
        for entity in all_entities:
            key = (entity["name"].strip().lower(), entity["type"].strip().upper())
            if key not in seen_entities:
                seen_entities.add(key)
                unique_entities.append({
                    "name": entity["name"].strip(),
                    "type": entity["type"].strip().upper(),
                    "properties": {"document_id": document_id},
                })

        # Deduplicate relationships by (source, target, type)
        seen_rels: set[tuple[str, str, str]] = set()
        unique_rels: list[dict] = []
        for rel in all_relationships:
            key = (
                rel["source"].strip().lower(),
                rel["target"].strip().lower(),
                rel["type"].strip().upper(),
            )
            if key not in seen_rels:
                seen_rels.add(key)
                unique_rels.append({
                    "source": rel["source"].strip(),
                    "target": rel["target"].strip(),
                    "type": rel["type"].strip().upper().replace(" ", "_"),
                    "properties": {"document_id": document_id},
                })

        # Bulk create in Neo4j
        if unique_entities:
            total_entities = await self._graph_store.bulk_create_entities(
                entities=unique_entities,
                collection=collection,
            )

        if unique_rels:
            total_relationships = await self._graph_store.bulk_create_relationships(
                relationships=unique_rels,
                collection=collection,
            )

        return total_entities, total_relationships

    @staticmethod
    def _parse_entity_response(raw: str) -> Optional[dict]:
        """Parse LLM JSON response for entities and relationships."""
        text = raw.strip()
        # Remove code fence if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                entities = data.get("entities", [])
                relationships = data.get("relationships", [])
                # Validate structure
                valid_entities = [
                    e for e in entities
                    if isinstance(e, dict) and "name" in e and "type" in e
                ]
                valid_rels = [
                    r for r in relationships
                    if isinstance(r, dict)
                    and "source" in r and "target" in r and "type" in r
                ]
                return {"entities": valid_entities, "relationships": valid_rels}
        except json.JSONDecodeError:
            logger.debug("Failed to parse entity extraction JSON", extra={"raw": text[:200]})
        return None

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
