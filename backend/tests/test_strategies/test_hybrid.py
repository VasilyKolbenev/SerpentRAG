"""
Tests for HybridRAGStrategy — dense + sparse + RRF + reranking pipeline.
"""

from unittest.mock import AsyncMock, patch

from app.services.tracing import TraceRecorder
from app.services.vector_store import SearchResult
from app.strategies.hybrid import HybridRAGStrategy


class TestHybridBM25:
    """BM25 sparse search — pure logic."""

    def test_bm25_search_returns_scored_results(self):
        strategy = HybridRAGStrategy(
            embedding_service=AsyncMock(),
            llm_service=AsyncMock(),
            vector_store=AsyncMock(),
        )
        documents = [
            "Python is a programming language",
            "Java is another language",
            "Python web frameworks like FastAPI",
        ]
        results = strategy._bm25_search("Python programming", documents, top_k=3)
        assert len(results) == 3
        assert all("index" in r for r in results)
        assert all("bm25_score" in r for r in results)
        # "Python" appears in docs 0 and 2, so they should rank higher
        top_indices = [r["index"] for r in results[:2]]
        assert 0 in top_indices

    def test_bm25_search_empty_documents(self):
        strategy = HybridRAGStrategy(
            embedding_service=AsyncMock(),
            llm_service=AsyncMock(),
            vector_store=AsyncMock(),
        )
        results = strategy._bm25_search("query", [], top_k=5)
        assert results == []


class TestHybridRRF:
    """Reciprocal Rank Fusion — pure logic."""

    def test_rrf_fusion_merges_results(self):
        strategy = HybridRAGStrategy(
            embedding_service=AsyncMock(),
            llm_service=AsyncMock(),
            vector_store=AsyncMock(),
        )
        dense = [
            SearchResult(id="1", content="chunk 1", score=0.9, metadata={}),
            SearchResult(id="2", content="chunk 2", score=0.8, metadata={}),
        ]
        sparse = [
            {"index": 1, "bm25_score": 5.0},  # chunk 2 ranked higher in BM25
            {"index": 0, "bm25_score": 3.0},
        ]
        fused = strategy._reciprocal_rank_fusion(dense, sparse, sparse_weight=0.3)
        assert len(fused) == 2
        assert all("rrf_score" in r for r in fused)
        assert all("content" in r for r in fused)


class TestHybridRetrieve:
    """Full retrieve pipeline with mocked services."""

    async def test_retrieve_runs_all_steps(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        strategy = HybridRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=AsyncMock(),
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="hybrid", collection="c")

        # Patch reranker to avoid loading real model
        with patch.object(
            HybridRAGStrategy,
            "_cross_encoder_rerank",
            new_callable=AsyncMock,
            return_value=[
                {"content": "chunk", "score": 0.9, "metadata": {}, "rerank_score": 0.95}
            ],
        ):
            results = await strategy.retrieve(
                query="Python frameworks",
                collection="default",
                trace=trace,
                top_k=5,
                sparse_weight=0.3,
                enable_reranking=True,
            )

        step_names = [s["name"] for s in trace.steps]
        assert "embedding" in step_names
        assert "dense_retrieval" in step_names
        assert "sparse_retrieval" in step_names
        assert "rrf_fusion" in step_names
        assert "reranking" in step_names

    async def test_retrieve_without_reranking(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        strategy = HybridRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=AsyncMock(),
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="hybrid", collection="c")

        results = await strategy.retrieve(
            query="test",
            collection="default",
            trace=trace,
            enable_reranking=False,
        )

        step_names = [s["name"] for s in trace.steps]
        assert "reranking" not in step_names

    async def test_cross_encoder_fallback_on_import_error(self):
        strategy = HybridRAGStrategy(
            embedding_service=AsyncMock(),
            llm_service=AsyncMock(),
            vector_store=AsyncMock(),
        )
        # Reset class-level reranker
        original = HybridRAGStrategy._reranker
        HybridRAGStrategy._reranker = None

        candidates = [{"content": "test", "score": 0.9, "metadata": {}}]
        with patch("builtins.__import__", side_effect=ImportError("no model")):
            result = await strategy._cross_encoder_rerank("query", candidates)
            assert result == candidates

        HybridRAGStrategy._reranker = original

    async def test_colbert_reranker_called(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """When reranker_type=colbert, _colbert_rerank is dispatched."""
        strategy = HybridRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=AsyncMock(),
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="hybrid", collection="c")

        with patch.object(
            strategy,
            "_colbert_rerank",
            new_callable=AsyncMock,
            return_value=[
                {"content": "chunk", "score": 0.9, "metadata": {}, "rerank_score": 0.8}
            ],
        ) as mock_colbert:
            results = await strategy.retrieve(
                query="test",
                collection="default",
                trace=trace,
                top_k=5,
                enable_reranking=True,
                reranker_type="colbert",
            )
            mock_colbert.assert_called_once()

        # Check trace records the reranker type
        rerank_step = [s for s in trace.steps if s["name"] == "reranking"][0]
        assert rerank_step["details"]["reranker_type"] == "colbert"

    async def test_colbert_fallback_on_import_error(self):
        """ImportError for ragatouille → falls back to cross-encoder."""
        strategy = HybridRAGStrategy(
            embedding_service=AsyncMock(),
            llm_service=AsyncMock(),
            vector_store=AsyncMock(),
        )
        candidates = [{"content": "test doc", "score": 0.9, "metadata": {}}]

        # Patch cross-encoder to avoid loading real model
        with patch.object(
            strategy,
            "_cross_encoder_rerank",
            new_callable=AsyncMock,
            return_value=candidates,
        ) as mock_ce:
            with patch("builtins.__import__", side_effect=ImportError("no ragatouille")):
                result = await strategy._colbert_rerank("query", candidates)
                mock_ce.assert_called_once_with("query", candidates)
                assert result == candidates

    async def test_reranker_type_in_trace(
        self,
        mock_embedding_service: AsyncMock,
        mock_vector_store: AsyncMock,
    ):
        """Trace captures which reranker type was used."""
        strategy = HybridRAGStrategy(
            embedding_service=mock_embedding_service,
            llm_service=AsyncMock(),
            vector_store=mock_vector_store,
        )
        trace = TraceRecorder(query="q", strategy="hybrid", collection="c")

        with patch.object(
            HybridRAGStrategy,
            "_cross_encoder_rerank",
            new_callable=AsyncMock,
            return_value=[
                {"content": "c", "score": 0.9, "metadata": {}, "rerank_score": 0.95}
            ],
        ):
            await strategy.retrieve(
                query="test",
                collection="default",
                trace=trace,
                top_k=5,
                enable_reranking=True,
                reranker_type="cross-encoder",
            )

        rerank_step = [s for s in trace.steps if s["name"] == "reranking"][0]
        assert rerank_step["details"]["reranker_type"] == "cross-encoder"
