"""
Tests for Corrective RAG (CRAG) strategy — relevance grading + web search fallback.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.cache import RedisService
from app.services.embedding import EmbeddingService
from app.services.llm import LLMService
from app.services.tracing import TraceRecorder, TracingService
from app.services.vector_store import QdrantService, SearchResult
from app.strategies.corrective import CorrectiveRAGStrategy


@pytest.fixture
def crag_strategy(
    mock_embedding_service: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_vector_store: AsyncMock,
) -> CorrectiveRAGStrategy:
    """CRAG strategy wired with mocks."""
    return CorrectiveRAGStrategy(
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service,
        vector_store=mock_vector_store,
    )


@pytest.fixture
def trace(mock_cache_service: AsyncMock) -> TraceRecorder:
    """Fresh trace recorder."""
    tracing = TracingService(cache=mock_cache_service)
    return tracing.create_recorder(
        query="test query", strategy="corrective", collection="default"
    )


@pytest.mark.asyncio
async def test_retrieve_with_relevant_docs(
    crag_strategy: CorrectiveRAGStrategy,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """High relevance scores → use documents directly."""
    # LLM grades all docs as highly relevant
    grades = json.dumps([
        {"index": 0, "score": 0.9, "reasoning": "Directly relevant"},
        {"index": 1, "score": 0.85, "reasoning": "Very relevant"},
    ])
    mock_llm_service.structured_extract.return_value = grades

    results = await crag_strategy.retrieve(
        query="What is Python?",
        collection="default",
        trace=trace,
        top_k=5,
        relevance_threshold=0.7,
    )

    assert len(results) > 0
    # All docs should pass the high threshold
    step_names = [s["name"] for s in trace.steps]
    assert "grading" in step_names
    assert "decision" in step_names


@pytest.mark.asyncio
async def test_retrieve_supplements_on_ambiguous(
    crag_strategy: CorrectiveRAGStrategy,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """Medium relevance scores → supplements with medium docs."""
    # Only medium-quality grades
    grades = json.dumps([
        {"index": 0, "score": 0.5, "reasoning": "Partially relevant"},
        {"index": 1, "score": 0.45, "reasoning": "Somewhat related"},
    ])
    mock_llm_service.structured_extract.return_value = grades

    results = await crag_strategy.retrieve(
        query="What is Python?",
        collection="default",
        trace=trace,
        top_k=5,
        relevance_threshold=0.7,
    )

    assert len(results) > 0
    # Check that decision step shows supplementation
    decision_steps = [s for s in trace.steps if s["name"] == "decision"]
    assert len(decision_steps) == 1


@pytest.mark.asyncio
async def test_retrieve_web_fallback_on_irrelevant(
    crag_strategy: CorrectiveRAGStrategy,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """Low relevance scores with web search disabled → uses what's available."""
    # All docs graded as irrelevant
    grades = json.dumps([
        {"index": 0, "score": 0.1, "reasoning": "Not relevant"},
        {"index": 1, "score": 0.15, "reasoning": "Irrelevant"},
    ])
    mock_llm_service.structured_extract.return_value = grades

    results = await crag_strategy.retrieve(
        query="What is quantum physics?",
        collection="default",
        trace=trace,
        top_k=5,
        relevance_threshold=0.7,
        web_search_enabled=False,
    )

    # Even without web search, should return something
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_grade_documents_parses_scores(
    crag_strategy: CorrectiveRAGStrategy,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """LLM grade output is correctly parsed into score map."""
    grades_json = json.dumps([
        {"index": 0, "score": 0.95, "reasoning": "Perfect match"},
        {"index": 1, "score": 0.3, "reasoning": "Weak match"},
    ])
    mock_llm_service.structured_extract.return_value = grades_json

    documents = [
        {"content": "Python is a programming language.", "score": 0.9, "metadata": {}},
        {"content": "Weather forecast for tomorrow.", "score": 0.4, "metadata": {}},
    ]

    graded = await crag_strategy._grade_documents("What is Python?", documents, trace)

    assert len(graded) == 2
    # First doc should have high score
    assert graded[0][1] == 0.95
    # Second doc should have low score
    assert graded[1][1] == 0.3


@pytest.mark.asyncio
async def test_web_search_disabled_skips(
    crag_strategy: CorrectiveRAGStrategy,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """When web_search_enabled=False, no web search is performed."""
    # All docs irrelevant
    grades = json.dumps([
        {"index": 0, "score": 0.1, "reasoning": "Not relevant"},
        {"index": 1, "score": 0.05, "reasoning": "Irrelevant"},
    ])
    mock_llm_service.structured_extract.return_value = grades

    results = await crag_strategy.retrieve(
        query="test",
        collection="default",
        trace=trace,
        top_k=5,
        web_search_enabled=False,
    )

    # No web_search step in trace
    step_names = [s["name"] for s in trace.steps]
    assert "web_search" not in step_names


@pytest.mark.asyncio
async def test_trace_steps_include_grading(
    crag_strategy: CorrectiveRAGStrategy,
    mock_llm_service: AsyncMock,
    trace: TraceRecorder,
):
    """Trace should contain embedding, retrieval, grading, decision, refinement steps."""
    grades = json.dumps([
        {"index": 0, "score": 0.9, "reasoning": "Relevant"},
        {"index": 1, "score": 0.8, "reasoning": "Relevant"},
    ])
    mock_llm_service.structured_extract.return_value = grades

    await crag_strategy.retrieve(
        query="test",
        collection="default",
        trace=trace,
        top_k=5,
    )

    step_names = [s["name"] for s in trace.steps]
    assert "embedding" in step_names
    assert "initial_retrieval" in step_names
    assert "grading" in step_names
    assert "decision" in step_names
    assert "refinement" in step_names
