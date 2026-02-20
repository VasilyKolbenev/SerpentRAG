"""
Naive (Simple) RAG Strategy.
Pipeline: Query → Embed → Vector Search → Top-K → LLM
"""

from app.services.tracing import TraceRecorder
from app.strategies.base import BaseRAGStrategy


class NaiveRAGStrategy(BaseRAGStrategy):
    """Simple vector similarity search — fast, predictable, easy to debug."""

    async def retrieve(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        top_k: int = 5,
        **kwargs,
    ) -> list[dict]:
        # 1. Embed query
        trace.start_step("embedding", input_summary=f"query_length={len(query)}")
        query_vector = await self.embedding.embed_query(query)
        trace.end_step(
            output_summary=f"dimensions={len(query_vector)}",
            details={"model": self.embedding._model_name},
        )

        # 2. Vector search
        trace.start_step("vector_search", input_summary=f"top_k={top_k}")
        results = await self.vector_store.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=0.5,
        )
        trace.end_step(
            output_summary=f"found={len(results)}, top_score={results[0].score:.3f}" if results else "found=0",
            result_count=len(results),
            details={
                "scores": [round(r.score, 3) for r in results[:5]],
            },
        )

        return [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ]
