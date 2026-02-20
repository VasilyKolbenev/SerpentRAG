"""
Tests for Strategy Advisor — pure function, no mocks needed.
"""

from app.schemas.query import RAGStrategy
from app.schemas.strategy import RecommendationRequest
from app.strategies.advisor import recommend_strategy


class TestRecommendStrategy:
    """recommend_strategy() — rule-based scoring logic."""

    def test_simple_query_recommends_naive(self):
        req = RecommendationRequest(
            domain="support",
            query_complexity="simple",
            data_structure="flat",
            priority="speed",
        )
        result = recommend_strategy(req)
        assert result.recommended == RAGStrategy.NAIVE
        assert result.scores["naive"] >= result.scores["agentic"]

    def test_complex_query_recommends_agentic(self):
        req = RecommendationRequest(
            domain="research",
            query_complexity="complex",
            data_structure="mixed",
            priority="accuracy",
        )
        result = recommend_strategy(req)
        assert result.recommended == RAGStrategy.AGENTIC

    def test_structured_data_recommends_graph(self):
        req = RecommendationRequest(
            domain="legal",
            query_complexity="moderate",
            data_structure="structured",
            priority="explainability",
        )
        result = recommend_strategy(req)
        assert result.recommended == RAGStrategy.GRAPH

    def test_scores_are_normalized(self):
        req = RecommendationRequest(
            domain="enterprise",
            query_complexity="moderate",
            data_structure="flat",
            priority="speed",
        )
        result = recommend_strategy(req)
        assert max(result.scores.values()) == 1.0
        assert all(0 <= v <= 1 for v in result.scores.values())

    def test_reasoning_contains_domain_and_priority(self):
        req = RecommendationRequest(
            domain="medical",
            query_complexity="very_complex",
            data_structure="structured",
            priority="accuracy",
        )
        result = recommend_strategy(req)
        assert "medical" in result.reasoning
        assert "accuracy" in result.reasoning
        assert isinstance(result.reasoning, str)
