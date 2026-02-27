"""
MemoRAG Strategy — Dual-system RAG with global memory.
Pipeline: Build/Load Memory → Generate Clues → Clue-Guided Retrieval → LLM

The light LLM (default: claude-3-haiku-20240307) builds a global memory of the collection,
then generates retrieval clues for each query. The heavy LLM generates the final answer.
"""

import hashlib
import json
import logging
from typing import Optional

from app.services.cache import RedisService
from app.services.embedding import EmbeddingService
from app.services.llm import LLMService
from app.services.tracing import TraceRecorder
from app.services.vector_store import QdrantService
from app.strategies.base import BaseRAGStrategy

logger = logging.getLogger("serpent.memo_rag")

MEMORY_BUILD_PROMPT = """You are a knowledge analyst. Given the following document chunks from a
collection, create a comprehensive global memory summary that captures:
1. Key topics and themes
2. Important entities and relationships
3. Core facts and concepts
4. Domain-specific terminology

Be thorough but concise. This memory will be used to guide retrieval for future queries.

Document chunks:
{chunks}

Global memory summary:"""

CLUE_GENERATION_PROMPT = """You are a retrieval assistant. Given the global memory of a document
collection and a user query, generate 3-5 specific retrieval clues that would help find the most
relevant documents.

Each clue should be a short, focused search query that targets a different aspect of the answer.

Global memory:
{memory}

User query: {query}

Return ONLY a JSON array of clue strings, like:
["clue 1", "clue 2", "clue 3"]

Clues:"""

MEMORY_BATCH_SIZE = 50
MEMORY_SUMMARY_MAX_CHUNKS = 200


class MemoRAGStrategy(BaseRAGStrategy):
    """Dual-system RAG: light LLM builds memory + clues, heavy LLM generates answer."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        vector_store: QdrantService,
        cache: RedisService,
        light_model: str = "claude-3-haiku-20240307",
    ) -> None:
        super().__init__(
            embedding_service=embedding_service,
            llm_service=llm_service,
            vector_store=vector_store,
        )
        self.cache = cache
        self.light_model = light_model

    async def retrieve(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        top_k: int = 10,
        light_model: Optional[str] = None,
        **kwargs,
    ) -> list[dict]:
        """MemoRAG retrieval: memory → clues → guided search."""
        model = light_model or self.light_model

        # 1. Get or build global memory
        memory = await self._get_or_build_memory(collection, trace, model)
        if not memory:
            logger.warning("Empty memory for collection %s, falling back to naive", collection)
            return await self._naive_fallback(query, collection, trace, top_k)

        # 2. Generate retrieval clues
        clues = await self._generate_clues(query, memory, trace, model)
        if not clues:
            logger.warning("No clues generated, falling back to naive retrieval")
            return await self._naive_fallback(query, collection, trace, top_k)

        # 3. Clue-guided retrieval
        results = await self._clue_guided_retrieval(
            query, clues, collection, top_k, trace
        )

        return results

    async def _get_or_build_memory(
        self, collection: str, trace: TraceRecorder, model: str
    ) -> str:
        """Load memory from cache or build from collection chunks."""
        trace.start_step("memory_load", input_summary=f"collection={collection}")

        cached = await self.cache.get_memo_memory(collection)
        if cached:
            trace.end_step(
                output_summary=f"cache_hit, memory_length={len(cached)}",
                details={"source": "cache"},
            )
            return cached

        trace.end_step(output_summary="cache_miss, building memory")

        # Build memory from scratch
        memory = await self._build_collection_memory(collection, trace, model)
        if memory:
            await self.cache.set_memo_memory(collection, memory, ttl=86400)

        return memory

    async def _build_collection_memory(
        self, collection: str, trace: TraceRecorder, model: str
    ) -> str:
        """Build global memory by summarizing collection chunks."""
        trace.start_step(
            "memory_build",
            input_summary=f"collection={collection}, model={model}",
        )

        # C32: Use scroll API instead of zero-vector search hack
        all_results = await self.vector_store.scroll(
            collection_name=collection,
            limit=MEMORY_SUMMARY_MAX_CHUNKS,
        )

        if not all_results:
            trace.end_step(output_summary="empty_collection")
            return ""

        # Summarize in batches
        batch_summaries = []
        for i in range(0, len(all_results), MEMORY_BATCH_SIZE):
            batch = all_results[i:i + MEMORY_BATCH_SIZE]
            chunks_text = "\n\n---\n\n".join(
                f"[{j+1}] {r.content[:500]}" for j, r in enumerate(batch)
            )
            prompt = MEMORY_BUILD_PROMPT.format(chunks=chunks_text)
            summary = await self.llm.structured_extract(
                prompt=prompt, model=model, temperature=0.1
            )
            batch_summaries.append(summary)

        # Merge batch summaries into one global memory
        if len(batch_summaries) == 1:
            memory = batch_summaries[0]
        else:
            merge_prompt = (
                "Merge the following partial summaries into one cohesive global memory:\n\n"
                + "\n\n---\n\n".join(batch_summaries)
                + "\n\nMerged global memory:"
            )
            memory = await self.llm.structured_extract(
                prompt=merge_prompt, model=model, temperature=0.1
            )

        trace.end_step(
            output_summary=f"memory_built, length={len(memory)}, batches={len(batch_summaries)}",
            details={"chunks_processed": len(all_results)},
        )
        return memory

    async def _generate_clues(
        self,
        query: str,
        memory: str,
        trace: TraceRecorder,
        model: str,
    ) -> list[str]:
        """Generate retrieval clues from query + global memory."""
        trace.start_step("clue_generation", input_summary=f"query_length={len(query)}")

        prompt = CLUE_GENERATION_PROMPT.format(memory=memory[:4000], query=query)
        raw = await self.llm.structured_extract(
            prompt=prompt, model=model, temperature=0.3
        )

        # Parse JSON array
        clues = self._parse_clues(raw)

        trace.end_step(
            output_summary=f"clues_generated={len(clues)}",
            details={"clues": clues},
        )
        return clues

    async def _clue_guided_retrieval(
        self,
        query: str,
        clues: list[str],
        collection: str,
        top_k: int,
        trace: TraceRecorder,
    ) -> list[dict]:
        """Retrieve using each clue, merge and deduplicate results."""
        trace.start_step(
            "clue_retrieval",
            input_summary=f"clues={len(clues)}, top_k={top_k}",
        )

        all_results: dict[str, dict] = {}
        per_clue_k = max(top_k // len(clues), 3) if clues else top_k

        # Also include the original query as a search
        search_queries = [query] + clues

        for sq in search_queries:
            vector = await self.embedding.embed_query(sq)
            results = await self.vector_store.search(
                collection_name=collection,
                query_vector=vector,
                limit=per_clue_k,
            )

            for r in results:
                content_hash = hashlib.md5(r.content.encode()).hexdigest()
                if content_hash not in all_results:
                    all_results[content_hash] = {
                        "content": r.content,
                        "score": r.score,
                        "metadata": r.metadata,
                    }
                else:
                    # Boost score for documents found by multiple clues
                    existing = all_results[content_hash]
                    existing["score"] = max(existing["score"], r.score) * 1.1

        # Sort by score and return top_k
        sorted_results = sorted(
            all_results.values(), key=lambda x: x["score"], reverse=True
        )[:top_k]

        trace.end_step(
            output_summary=f"unique_results={len(all_results)}, returned={len(sorted_results)}",
            result_count=len(sorted_results),
            details={"search_queries": len(search_queries)},
        )
        return sorted_results

    async def _naive_fallback(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        top_k: int,
    ) -> list[dict]:
        """Fallback to simple vector search when memory/clues unavailable."""
        trace.start_step("naive_fallback", input_summary="memory unavailable")
        vector = await self.embedding.embed_query(query)
        results = await self.vector_store.search(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
        )
        output = [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ]
        trace.end_step(
            output_summary=f"fallback_results={len(output)}",
            result_count=len(output),
        )
        return output

    @staticmethod
    def _parse_clues(raw: str) -> list[str]:
        """Parse clue list from LLM response (JSON array or line-separated)."""
        # Try JSON parsing first
        try:
            # Find JSON array in response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                if isinstance(parsed, list):
                    return [str(c).strip() for c in parsed if c]
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: line-separated parsing
        lines = [
            line.strip().lstrip("0123456789.-) ").strip('"')
            for line in raw.strip().split("\n")
            if line.strip() and len(line.strip()) > 5
        ]
        return lines[:5]
