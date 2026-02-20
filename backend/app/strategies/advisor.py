"""
Strategy Advisor — rule-based recommendation engine.
Transferred from original main.py:299-357 with no logic changes.
"""

from app.schemas.query import RAGStrategy
from app.schemas.strategy import RecommendationRequest, RecommendationResponse


def recommend_strategy(req: RecommendationRequest) -> RecommendationResponse:
    """AI-powered strategy recommendation based on user's requirements."""
    scores = {
        "agentic": 0.0, "graph": 0.0, "hybrid": 0.0,
        "naive": 0.0, "memo": 0.0, "corrective": 0.0,
    }

    # Complexity scoring
    complexity_map = {
        "simple": {"naive": 3, "hybrid": 1},
        "moderate": {"hybrid": 3, "graph": 1, "memo": 2},
        "complex": {"agentic": 3, "graph": 2, "corrective": 2},
        "very_complex": {"agentic": 3, "graph": 1, "memo": 1},
    }
    for strategy, score in complexity_map.get(req.query_complexity, {}).items():
        scores[strategy] += score

    # Data structure scoring
    data_map = {
        "flat": {"naive": 2, "hybrid": 2, "memo": 1},
        "structured": {"graph": 3, "hybrid": 1},
        "mixed": {"hybrid": 2, "agentic": 2, "corrective": 1},
        "code": {"agentic": 2, "hybrid": 1},
    }
    for strategy, score in data_map.get(req.data_structure, {}).items():
        scores[strategy] += score

    # Domain scoring
    domain_map = {
        "legal": {"graph": 2, "agentic": 1, "corrective": 2},
        "medical": {"graph": 2, "agentic": 1, "corrective": 2},
        "enterprise": {"hybrid": 2, "naive": 1, "memo": 2},
        "research": {"agentic": 3, "corrective": 1},
        "support": {"hybrid": 2, "naive": 2, "memo": 1},
    }
    for strategy, score in domain_map.get(req.domain, {}).items():
        scores[strategy] += score

    # Priority scoring
    priority_map = {
        "speed": {"naive": 3, "hybrid": 1},
        "accuracy": {"agentic": 2, "graph": 2, "corrective": 2, "memo": 1},
        "cost": {"naive": 3, "memo": 1},
        "explainability": {"graph": 3, "agentic": 1, "corrective": 1},
    }
    for strategy, score in priority_map.get(req.priority, {}).items():
        scores[strategy] += score

    # Normalize
    max_score = max(scores.values()) or 1
    normalized = {k: round(v / max_score, 2) for k, v in scores.items()}
    best = max(scores, key=scores.get)

    reasoning = (
        f"Based on your {req.domain} domain with {req.query_complexity} queries "
        f"and {req.data_structure} data structure, "
        f"prioritizing {req.priority}: {best.upper()} RAG is recommended."
    )

    return RecommendationResponse(
        recommended=RAGStrategy(best),
        scores=normalized,
        reasoning=reasoning,
    )
