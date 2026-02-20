"""
Tests for NaiveRAGStrategy — embed → search → results, trace steps.
"""

from unittest.mock import AsyncMock

from app.services.tracing import TraceRecorder
from app.services.vector_store import SearchResult
from app.strategies.naive import NaiveRAGStrategy


class TestNaiveRAGStrategy:
    """NaiveRAGStrategy.retrieve() — embedding and vector search pipeline."""

    async def test_retrieve_returns_context_dicts(
        self, mock_embedding_service: AsyncMock, mock_vector_store: AsyncMock
    ):
        mock_llm = AsyncMock()
        strategy = NaiveRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=mock_llm,
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="test", strategy="naive", collection="default")

        results = await strategy.retrieve(
            query="What is Python?",
            collection="default",
            trace=trace,
            top_k=5,
        )

        assert len(results) == 2  # from mock fixture
        assert all("content" in r for r in results)
        assert all("score" in r for r in results)
        assert all("metadata" in r for r in results)

    async def test_retrieve_calls_embed_query(
        self, mock_embedding_service: AsyncMock, mock_vector_store: AsyncMock
    ):
        strategy = NaiveRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=AsyncMock(),
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        await strategy.retrieve(query="test query", collection="default", trace=trace)
        mock_embedding_service.embed_query.assert_called_once_with("test query")

    async def test_retrieve_records_trace_steps(
        self, mock_embedding_service: AsyncMock, mock_vector_store: AsyncMock
    ):
        strategy = NaiveRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=AsyncMock(),
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        await strategy.retrieve(query="test", collection="default", trace=trace)

        assert len(trace.steps) == 2
        assert trace.steps[0]["name"] == "embedding"
        assert trace.steps[1]["name"] == "vector_search"

    async def test_retrieve_handles_empty_results(
        self, mock_embedding_service: AsyncMock
    ):
        mock_vs = AsyncMock()
        mock_vs.search.return_value = []
        strategy = NaiveRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=AsyncMock(),
            vector_store=mock_vs,
        )
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        results = await strategy.retrieve(query="nothing", collection="empty", trace=trace)
        assert results == []
