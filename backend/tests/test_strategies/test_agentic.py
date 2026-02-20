"""
Tests for AgenticRAGStrategy — plan, tool selection, reflect loop.
"""

from unittest.mock import AsyncMock

from app.services.graph_store import GraphNode
from app.services.tracing import TraceRecorder
from app.strategies.agentic import AgenticRAGStrategy


def _make_strategy(
    mock_embedding_service: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_graph_store: AsyncMock,
) -> AgenticRAGStrategy:
    """Helper to create AgenticRAGStrategy with mocks."""
    return AgenticRAGStrategy(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service,
        vector_store=mock_vector_store,
    )


class TestAgenticPlan:
    """Planning — decompose query into sub-questions."""

    async def test_plan_parses_json_array(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = '["What is X?", "How does Y work?"]'
        strategy = AgenticRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        subs = await strategy._plan("Complex question about X and Y")
        assert len(subs) == 2

    async def test_plan_falls_back_on_json_error(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = "broken json"
        strategy = AgenticRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        subs = await strategy._plan("Query")
        assert subs == ["Query"]


class TestAgenticToolSelection:
    """Tool selection via LLM."""

    async def test_select_tool_returns_valid_tool(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = "vector_search"
        strategy = AgenticRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        tool = await strategy._select_tool("question", [])
        assert tool == "vector_search"

    async def test_select_tool_defaults_on_invalid(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = "invalid_tool"
        strategy = AgenticRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        tool = await strategy._select_tool("question", [])
        assert tool == "vector_search"


class TestAgenticReflection:
    """Reflection — evaluate context sufficiency."""

    async def test_reflect_returns_true_on_yes(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = "yes"
        strategy = AgenticRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        context = [{"content": "some info", "score": 0.9, "metadata": {}}]
        result = await strategy._reflect("question", context)
        assert result is True

    async def test_reflect_returns_false_on_no(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = "no"
        strategy = AgenticRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        result = await strategy._reflect("question", [{"content": "c", "score": 0.5, "metadata": {}}])
        assert result is False


class TestAgenticRetrieve:
    """Full agentic retrieve pipeline."""

    async def test_retrieve_with_planning_and_reflection(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_graph_store: AsyncMock,
    ):
        mock_llm = AsyncMock()

        # Plan returns sub-questions
        # Select tool returns vector_search
        # Reflect returns yes (sufficient after 1 iteration)
        mock_llm.structured_extract.side_effect = [
            '["Sub Q1", "Sub Q2"]',  # plan
            "vector_search",  # select tool for sub Q1
            "vector_search",  # select tool for sub Q2
            "yes",  # reflect — sufficient
        ]

        strategy = _make_strategy(
            mock_embedding_service, mock_llm, mock_vector_store, mock_graph_store
        )
        trace = TraceRecorder(query="q", strategy="agentic", collection="c")

        results = await strategy.retrieve(
            query="Complex question",
            collection="default",
            trace=trace,
            max_iterations=3,
        )

        assert len(results) > 0
        step_names = [s["name"] for s in trace.steps]
        assert "planning" in step_names

    async def test_retrieve_without_planning(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_graph_store: AsyncMock,
    ):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.side_effect = [
            "vector_search",  # select tool
            "yes",  # reflect — sufficient
        ]

        strategy = _make_strategy(
            mock_embedding_service, mock_llm, mock_vector_store, mock_graph_store
        )
        trace = TraceRecorder(query="q", strategy="agentic", collection="c")

        results = await strategy.retrieve(
            query="Simple question",
            collection="default",
            trace=trace,
            enable_planning=False,
        )

        step_names = [s["name"] for s in trace.steps]
        assert "planning" not in step_names

    async def test_retrieve_respects_max_iterations(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_graph_store: AsyncMock,
    ):
        mock_llm = AsyncMock()
        # Always returns "no" for reflection, forcing all iterations
        mock_llm.structured_extract.side_effect = [
            '["Q1"]',  # plan
        ] + [
            "vector_search",  # tool
            "no",  # reflect
            '["Q2"]',  # replan
        ] * 10  # enough for many iterations

        strategy = _make_strategy(
            mock_embedding_service, mock_llm, mock_vector_store, mock_graph_store
        )
        trace = TraceRecorder(query="q", strategy="agentic", collection="c")

        results = await strategy.retrieve(
            query="Hard question",
            collection="default",
            trace=trace,
            max_iterations=2,
        )

        # Count iteration steps
        iteration_steps = [s for s in trace.steps if s["name"].startswith("iteration_")]
        assert len(iteration_steps) <= 2


class TestAgenticDeduplicate:
    """Deduplication — pure logic."""

    def test_deduplicate_removes_duplicates(self):
        context = [
            {"content": "Same content here and more text after", "score": 0.9, "metadata": {}},
            {"content": "Same content here and more text after", "score": 0.8, "metadata": {}},
            {"content": "Different content entirely", "score": 0.7, "metadata": {}},
        ]
        result = AgenticRAGStrategy._deduplicate(context)
        assert len(result) == 2
