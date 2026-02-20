"""
Tests for StrategyFactory — creation, caching, unknown strategy.
"""

from unittest.mock import AsyncMock

import pytest

from app.schemas.query import RAGStrategy
from app.strategies.agentic import AgenticRAGStrategy
from app.strategies.corrective import CorrectiveRAGStrategy
from app.strategies.factory import StrategyFactory
from app.strategies.graph_rag import GraphRAGStrategy
from app.strategies.hybrid import HybridRAGStrategy
from app.strategies.memo_rag import MemoRAGStrategy
from app.strategies.naive import NaiveRAGStrategy


class TestStrategyFactory:
    """StrategyFactory.get() — creates correct types, caches instances."""

    def test_get_naive_returns_naive_strategy(self, mock_strategy_factory: StrategyFactory):
        strategy = mock_strategy_factory.get(RAGStrategy.NAIVE)
        assert isinstance(strategy, NaiveRAGStrategy)

    def test_get_hybrid_returns_hybrid_strategy(self, mock_strategy_factory: StrategyFactory):
        strategy = mock_strategy_factory.get(RAGStrategy.HYBRID)
        assert isinstance(strategy, HybridRAGStrategy)

    def test_get_graph_returns_graph_strategy(self, mock_strategy_factory: StrategyFactory):
        strategy = mock_strategy_factory.get(RAGStrategy.GRAPH)
        assert isinstance(strategy, GraphRAGStrategy)

    def test_get_agentic_returns_agentic_strategy(self, mock_strategy_factory: StrategyFactory):
        strategy = mock_strategy_factory.get(RAGStrategy.AGENTIC)
        assert isinstance(strategy, AgenticRAGStrategy)

    def test_get_memo_returns_memo_strategy(self, mock_strategy_factory: StrategyFactory):
        strategy = mock_strategy_factory.get(RAGStrategy.MEMO)
        assert isinstance(strategy, MemoRAGStrategy)

    def test_get_corrective_returns_corrective_strategy(self, mock_strategy_factory: StrategyFactory):
        strategy = mock_strategy_factory.get(RAGStrategy.CORRECTIVE)
        assert isinstance(strategy, CorrectiveRAGStrategy)

    def test_get_caches_instances(self, mock_strategy_factory: StrategyFactory):
        s1 = mock_strategy_factory.get(RAGStrategy.NAIVE)
        s2 = mock_strategy_factory.get(RAGStrategy.NAIVE)
        assert s1 is s2

    def test_different_strategies_are_different_instances(
        self, mock_strategy_factory: StrategyFactory
    ):
        naive = mock_strategy_factory.get(RAGStrategy.NAIVE)
        hybrid = mock_strategy_factory.get(RAGStrategy.HYBRID)
        assert naive is not hybrid

    def test_unknown_strategy_raises(
        self,
        mock_embedding_service: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_vector_store: AsyncMock,
        mock_graph_store: AsyncMock,
        mock_cache_service: AsyncMock,
    ):
        factory = StrategyFactory(
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            cache=mock_cache_service,
        )
        with pytest.raises(ValueError, match="Unknown strategy"):
            factory._create("nonexistent")
