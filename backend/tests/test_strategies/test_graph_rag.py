"""
Tests for GraphRAGStrategy — entity extraction, traversal, merge.
"""

from unittest.mock import AsyncMock

from app.services.graph_store import GraphEdge, GraphNode, Neo4jService
from app.services.tracing import TraceRecorder
from app.strategies.graph_rag import GraphRAGStrategy


class TestGraphRAGEntityExtraction:
    """Entity extraction from query via LLM."""

    async def test_extract_entities_parses_json_array(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = '["Python", "FastAPI"]'
        strategy = GraphRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        entities = await strategy._extract_entities("Tell me about Python and FastAPI")
        assert entities == ["Python", "FastAPI"]

    async def test_extract_entities_handles_markdown_code_block(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = '```json\n["Python"]\n```'
        strategy = GraphRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        entities = await strategy._extract_entities("Python info")
        assert entities == ["Python"]

    async def test_extract_entities_returns_empty_on_json_error(self):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = "not valid json"
        strategy = GraphRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=AsyncMock(),
            llm_service=mock_llm,
            vector_store=AsyncMock(),
        )
        entities = await strategy._extract_entities("test")
        assert entities == []


class TestGraphRAGMerge:
    """Context merging — pure logic."""

    def test_merge_deduplicates_by_content_prefix(self):
        graph_ctx = [
            {"content": "Entity: Python (type: Technology)", "score": 0.9, "metadata": {}},
        ]
        vector_ctx = [
            {"content": "Entity: Python (type: Technology)", "score": 0.8, "metadata": {}},
            {"content": "Different content about Python", "score": 0.7, "metadata": {}},
        ]
        merged = GraphRAGStrategy._merge_contexts(graph_ctx, vector_ctx, limit=10)
        assert len(merged) == 2  # One duplicate removed


class TestGraphRAGRetrieve:
    """Full retrieve pipeline with mocks."""

    async def test_retrieve_combines_graph_and_vector(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_graph_store: AsyncMock,
    ):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = '["Python", "FastAPI"]'

        strategy = GraphRAGStrategy(
            graph_store=mock_graph_store,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm,
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="graph", collection="c")

        results = await strategy.retrieve(
            query="Tell me about Python and FastAPI",
            collection="default",
            trace=trace,
            top_k=10,
        )

        # Should have results from both graph and vector
        assert len(results) > 0

        step_names = [s["name"] for s in trace.steps]
        assert "entity_extraction" in step_names
        assert "graph_traversal" in step_names
        assert "vector_search" in step_names
        assert "context_merge" in step_names

    async def test_retrieve_skips_graph_when_no_entities(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        mock_llm = AsyncMock()
        mock_llm.structured_extract.return_value = "not json"

        strategy = GraphRAGStrategy(
            graph_store=AsyncMock(),
            embedding_service=mock_embedding_service,
            llm_service=mock_llm,
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="graph", collection="c")

        results = await strategy.retrieve(
            query="something without entities",
            collection="default",
            trace=trace,
        )

        step_names = [s["name"] for s in trace.steps]
        assert "entity_extraction" in step_names
        assert "graph_traversal" not in step_names
        assert "vector_search" in step_names
