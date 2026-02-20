"""
Tests for BaseRAGStrategy — generate, stream_generate, and context sufficiency check.
"""

import json
from unittest.mock import AsyncMock

from app.services.tracing import TraceRecorder
from app.strategies.naive import NaiveRAGStrategy


class TestBaseRAGGenerate:
    """BaseRAGStrategy.generate() via NaiveRAGStrategy."""

    async def test_generate_calls_llm_and_records_trace(
        self,
        mock_embedding_service: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        strategy = NaiveRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        context = [{"content": "ctx", "metadata": {}}]

        result = await strategy.generate(
            query="test question",
            context=context,
            trace=trace,
            model="gpt-4o",
            temperature=0.1,
        )

        assert result == "Test answer based on context."
        mock_llm_service.generate.assert_called_once()
        assert len(trace.steps) == 1
        assert trace.steps[0]["name"] == "generation"


class TestBaseRAGStreamGenerate:
    """BaseRAGStrategy.stream_generate() via NaiveRAGStrategy."""

    async def test_stream_generate_yields_tokens(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        mock_llm = AsyncMock()

        async def _stream(*args, **kwargs):
            for token in ["Hello ", "world"]:
                yield token

        mock_llm.stream_generate = _stream

        strategy = NaiveRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=mock_llm,
            vector_store=mock_vector_store,
        )
        context = [{"content": "ctx", "metadata": {}}]
        tokens = []
        async for token in strategy.stream_generate(
            query="test", context=context
        ):
            tokens.append(token)

        assert tokens == ["Hello ", "world"]


class TestContextSufficiency:
    """BaseRAGStrategy.check_context_sufficiency() via NaiveRAGStrategy."""

    def _make_strategy(self, mock_embedding_service, mock_llm_service, mock_vector_store):
        return NaiveRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            vector_store=mock_vector_store,
        )

    async def test_sufficiency_sufficient(
        self,
        mock_embedding_service: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """Score above threshold → sufficient."""
        strategy = self._make_strategy(
            mock_embedding_service, mock_llm_service, mock_vector_store
        )
        mock_llm_service.structured_extract.return_value = json.dumps(
            {"score": 0.85, "reasoning": "Context directly answers the query"}
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        context = [{"content": "Python is a programming language.", "metadata": {}}]

        is_sufficient, score = await strategy.check_context_sufficiency(
            query="What is Python?",
            context=context,
            trace=trace,
            threshold=0.5,
        )

        assert is_sufficient is True
        assert score == 0.85

    async def test_sufficiency_insufficient(
        self,
        mock_embedding_service: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """Score below threshold → insufficient."""
        strategy = self._make_strategy(
            mock_embedding_service, mock_llm_service, mock_vector_store
        )
        mock_llm_service.structured_extract.return_value = json.dumps(
            {"score": 0.2, "reasoning": "Context is unrelated to the query"}
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        context = [{"content": "Weather is sunny today.", "metadata": {}}]

        is_sufficient, score = await strategy.check_context_sufficiency(
            query="What is quantum physics?",
            context=context,
            trace=trace,
            threshold=0.5,
        )

        assert is_sufficient is False
        assert score == 0.2

    async def test_sufficiency_empty_context(
        self,
        mock_embedding_service: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """Empty context → (False, 0.0) without LLM call."""
        strategy = self._make_strategy(
            mock_embedding_service, mock_llm_service, mock_vector_store
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")

        is_sufficient, score = await strategy.check_context_sufficiency(
            query="test",
            context=[],
            trace=trace,
        )

        assert is_sufficient is False
        assert score == 0.0
        mock_llm_service.structured_extract.assert_not_called()

    async def test_sufficiency_trace_step(
        self,
        mock_embedding_service: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """Sufficiency check adds a trace step."""
        strategy = self._make_strategy(
            mock_embedding_service, mock_llm_service, mock_vector_store
        )
        mock_llm_service.structured_extract.return_value = json.dumps(
            {"score": 0.7, "reasoning": "Adequate context"}
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        context = [{"content": "Relevant content.", "metadata": {}}]

        await strategy.check_context_sufficiency(
            query="test", context=context, trace=trace
        )

        assert len(trace.steps) == 1
        assert trace.steps[0]["name"] == "sufficiency_check"

    async def test_sufficiency_handles_parse_error(
        self,
        mock_embedding_service: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """Malformed LLM response → fallback score 0.5."""
        strategy = self._make_strategy(
            mock_embedding_service, mock_llm_service, mock_vector_store
        )
        mock_llm_service.structured_extract.return_value = "invalid json response"
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        context = [{"content": "Some content.", "metadata": {}}]

        is_sufficient, score = await strategy.check_context_sufficiency(
            query="test", context=context, trace=trace, threshold=0.5
        )

        # Fallback: 0.5 score, which equals threshold → sufficient
        assert score == 0.5
        assert is_sufficient is True
