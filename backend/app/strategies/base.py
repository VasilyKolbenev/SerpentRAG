"""
Base RAG strategy with tracing hooks and context sufficiency check.
"""

import json
import logging
from abc import ABC, abstractmethod

from app.services.embedding import EmbeddingService
from app.services.llm import LLMService
from app.services.tracing import TraceRecorder
from app.services.vector_store import QdrantService

logger = logging.getLogger("serpent.base_strategy")

SUFFICIENCY_PROMPT = """You are a context evaluator. Given a user query and retrieved context,
assess whether the context contains sufficient information to answer the query confidently.

Score from 0.0 to 1.0:
- 1.0: Context fully and directly answers the query
- 0.7: Context mostly answers the query with minor gaps
- 0.5: Context partially addresses the query
- 0.3: Context is tangentially related but insufficient
- 0.0: Context is completely irrelevant

Query: {query}

Retrieved context:
{context}

Return ONLY a JSON object: {{"score": 0.X, "reasoning": "brief explanation"}}

Assessment:"""


class BaseRAGStrategy(ABC):
    """Abstract base class for all RAG retrieval strategies."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        vector_store: QdrantService,
    ) -> None:
        self.embedding = embedding_service
        self.llm = llm_service
        self.vector_store = vector_store

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        collection: str,
        trace: TraceRecorder,
        **kwargs,
    ) -> list[dict]:
        """Retrieve relevant context chunks for a query."""
        ...

    async def generate(
        self,
        query: str,
        context: list[dict],
        trace: TraceRecorder,
        model: str = "gpt-4o",
        temperature: float = 0.1,
    ) -> str:
        """Generate answer from context using LLM."""
        trace.start_step(
            "generation",
            input_summary=f"model={model}, context_chunks={len(context)}",
        )

        answer = await self.llm.generate(
            query=query,
            context=context,
            model=model,
            temperature=temperature,
        )

        trace.end_step(
            output_summary=f"answer_length={len(answer)}",
            details={"model": model},
        )
        return answer

    async def stream_generate(
        self,
        query: str,
        context: list[dict],
        model: str = "gpt-4o",
        temperature: float = 0.1,
    ):
        """Stream answer tokens from LLM."""
        async for token in self.llm.stream_generate(
            query=query,
            context=context,
            model=model,
            temperature=temperature,
        ):
            yield token

    async def check_context_sufficiency(
        self,
        query: str,
        context: list[dict],
        trace: TraceRecorder,
        threshold: float = 0.5,
        model: str = "gpt-4o",
    ) -> tuple[bool, float]:
        """Evaluate whether retrieved context is sufficient to answer the query.

        Returns:
            Tuple of (is_sufficient, score) where score is 0.0-1.0.
        """
        if not context:
            return False, 0.0

        trace.start_step(
            "sufficiency_check",
            input_summary=f"chunks={len(context)}, threshold={threshold}",
        )

        # Build context summary for evaluation
        context_text = "\n\n".join(
            f"[{i+1}] {c['content'][:400]}" for i, c in enumerate(context[:10])
        )

        prompt = SUFFICIENCY_PROMPT.format(query=query, context=context_text)

        try:
            raw = await self.llm.structured_extract(
                prompt=prompt, model=model, temperature=0.0
            )
            score, reasoning = self._parse_sufficiency(raw)
        except Exception as e:
            logger.warning("Sufficiency check failed: %s", e)
            score = 0.5
            reasoning = "evaluation_error"

        is_sufficient = score >= threshold

        trace.end_step(
            output_summary=f"score={score:.2f}, sufficient={is_sufficient}",
            details={
                "score": score,
                "threshold": threshold,
                "reasoning": reasoning,
            },
        )
        return is_sufficient, score

    @staticmethod
    def _parse_sufficiency(raw: str) -> tuple[float, str]:
        """Parse sufficiency check LLM response."""
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                score = float(parsed.get("score", 0.5))
                score = max(0.0, min(1.0, score))
                reasoning = parsed.get("reasoning", "")
                return score, reasoning
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return 0.5, "parse_error"
