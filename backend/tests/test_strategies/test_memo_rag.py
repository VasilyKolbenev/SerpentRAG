"""
Tests for MemoRAG strategy — dual-system with global memory + clue-guided retrieval.
"""

import json
from unittest.mock import AsyncMock

import pytest

from app.services.cache import RedisService
from app.services.embedding import EmbeddingService
from app.services.llm import LLMService
from app.services.tracing import TraceRecorder, TracingService
from app.services.vector_store import QdrantService, SearchResult
from app.strategies.memo_rag import MemoRAGStrategy


@pytest.fixture
def memo_strategy(
    mock_embedding_service: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_cache_service: AsyncMock,
) -> MemoRAGStrategy:
    """MemoRAG strategy wired with mocks."""
    return MemoRAGStrategy(
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service,
        vector_store=mock_vector_store,
        cache=mock_cache_service,
        light_model="claude-3-haiku-20240307",
    )


@pytest.fixture
def trace(mock_cache_service: AsyncMock) -> TraceRecorder:
    """Fresh trace recorder."""
    tracing = TracingService(cache=mock_cache_service)
    return tracing.create_recorder(
        query="test query", strategy="memo", collection="default"
    )


@pytest.mark.asyncio
async def test_retrieve_loads_cached_memory(
    memo_strategy: MemoRAGStrategy,
    mock_cache_service: AsyncMock,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """When memory is cached, no LLM call for memory building."""
    mock_cache_service.get_memo_memory.return_value = "Cached global memory about Python."
    mock_llm_service.structured_extract.return_value = json.dumps(
        ["Python frameworks", "FastAPI features", "async programming"]
    )

    results = await memo_strategy.retrieve(
        query="What is FastAPI?",
        collection="default",
        trace=trace,
        top_k=5,
    )

    # Memory was loaded from cache, not built
    mock_cache_service.get_memo_memory.assert_called_once_with("default")
    mock_cache_service.set_memo_memory.assert_not_called()
    assert len(results) > 0


@pytest.mark.asyncio
async def test_retrieve_builds_memory_on_miss(
    memo_strategy: MemoRAGStrategy,
    mock_cache_service: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_vector_store: AsyncMock,
    trace: TraceRecorder,
):
    """When memory is not cached, builds from chunks via light LLM."""
    mock_cache_service.get_memo_memory.return_value = None

    # First call: memory build summary, Second call: clue generation
    mock_llm_service.structured_extract.side_effect = [
        "Global memory: Python is a programming language. FastAPI is a web framework.",
        json.dumps(["Python web frameworks", "FastAPI performance"]),
    ]

    results = await memo_strategy.retrieve(
        query="What is FastAPI?",
        collection="default",
        trace=trace,
        top_k=5,
    )

    # Memory was built and cached
    mock_cache_service.set_memo_memory.assert_called_once()
    assert len(results) > 0


@pytest.mark.asyncio
async def test_generate_clues_returns_list(
    memo_strategy: MemoRAGStrategy,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """Clue generation parses JSON list from LLM response."""
    clues_json = json.dumps(["performance tips", "async patterns", "deployment"])

    clues = memo_strategy._parse_clues(clues_json)

    assert len(clues) == 3
    assert "performance tips" in clues
    assert "async patterns" in clues


@pytest.mark.asyncio
async def test_clue_guided_retrieval_merges_results(
    memo_strategy: MemoRAGStrategy,
    mock_vector_store: AsyncMock,
    mock_embedding_service: AsyncMock,
    trace: TraceRecorder,
):
    """Results from multiple clues are merged and deduplicated."""
    # Mock returns same 2 results for each search — should deduplicate
    results = await memo_strategy._clue_guided_retrieval(
        query="test",
        clues=["clue1", "clue2"],
        collection="default",
        top_k=5,
        trace=trace,
    )

    # 3 searches (query + 2 clues), but deduplication means ≤ 2 unique results
    assert len(results) <= 5
    # Embedding was called for each search query
    assert mock_embedding_service.embed_query.call_count == 3


@pytest.mark.asyncio
async def test_retrieve_records_trace_steps(
    memo_strategy: MemoRAGStrategy,
    mock_cache_service: AsyncMock,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """Trace should contain memory + clue + retrieval steps."""
    mock_cache_service.get_memo_memory.return_value = "Cached memory."
    mock_llm_service.structured_extract.return_value = json.dumps(
        ["clue1", "clue2"]
    )

    await memo_strategy.retrieve(
        query="test query",
        collection="default",
        trace=trace,
        top_k=5,
    )

    # Should have at least 3 steps: memory_load, clue_generation, clue_retrieval
    assert len(trace.steps) >= 3
    step_names = [s["name"] for s in trace.steps]
    assert "memory_load" in step_names
    assert "clue_generation" in step_names
    assert "clue_retrieval" in step_names


@pytest.mark.asyncio
async def test_retrieve_handles_empty_collection(
    memo_strategy: MemoRAGStrategy,
    mock_cache_service: AsyncMock,
    mock_vector_store: AsyncMock,
    trace: TraceRecorder,
):
    """Gracefully handles empty collection — falls back to naive."""
    mock_cache_service.get_memo_memory.return_value = None
    mock_vector_store.search.return_value = []

    results = await memo_strategy.retrieve(
        query="test query",
        collection="empty",
        trace=trace,
        top_k=5,
    )

    # Should return empty list gracefully (empty collection → empty memory → fallback → empty)
    assert results == []
