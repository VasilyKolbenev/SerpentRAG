"""
Embedding service — unified interface for local and cloud embedding models.
Supports: sentence-transformers (BGE-M3), OpenAI (text-embedding-3-small).
"""

import logging
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger("serpent.embedding")


class EmbeddingService:
    """Manages embedding model loading and inference."""

    def __init__(self) -> None:
        self._model = None
        self._provider = settings.embedding_provider
        self._model_name = settings.embedding_model
        self._dimensions = settings.embedding_dimensions
        self._openai_client = None

    async def initialize(self) -> None:
        """Load the embedding model. Call once at startup."""
        if self._provider == "openai":
            from openai import AsyncOpenAI

            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(
                "Embedding service initialized with OpenAI",
                extra={"model": self._model_name},
            )
        else:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._model_name,
                trust_remote_code=True,
            )
            logger.info(
                "Embedding service initialized with local model",
                extra={"model": self._model_name},
            )

    async def embed(
        self,
        texts: list[str],
        batch_size: int = 64,
    ) -> list[list[float]]:
        """Embed a list of texts. Returns list of embedding vectors."""
        if not texts:
            return []

        if self._provider == "openai":
            return await self._embed_openai(texts, batch_size)
        return await self._embed_local(texts, batch_size)

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        results = await self.embed([query])
        return results[0]

    async def _embed_local(
        self, texts: list[str], batch_size: int
    ) -> list[list[float]]:
        """Embed using local sentence-transformers model."""
        if self._model is None:
            raise RuntimeError("Embedding model not initialized. Call initialize() first.")

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = self._model.encode(
                batch,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            all_embeddings.extend(embeddings.tolist())

        return all_embeddings

    async def _embed_openai(
        self, texts: list[str], batch_size: int
    ) -> list[list[float]]:
        """Embed using OpenAI API."""
        if self._openai_client is None:
            raise RuntimeError("OpenAI client not initialized. Call initialize() first.")

        all_embeddings: list[list[float]] = []
        model = self._model_name if "embedding" in self._model_name else "text-embedding-3-small"

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._openai_client.embeddings.create(
                input=batch,
                model=model,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    @property
    def dimensions(self) -> int:
        return self._dimensions
