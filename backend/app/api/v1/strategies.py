"""
Strategy listing and recommendation endpoints.
"""

from fastapi import APIRouter

from app.schemas.strategy import (
    RecommendationRequest,
    RecommendationResponse,
    StrategyInfo,
    StrategyListResponse,
)
from app.strategies.advisor import recommend_strategy

router = APIRouter(tags=["strategies"])

STRATEGY_DETAILS = [
    StrategyInfo(
        id="naive",
        name="Simple RAG",
        description="Straightforward vector similarity search",
        complexity=1,
        latency="low",
        accuracy="medium",
    ),
    StrategyInfo(
        id="hybrid",
        name="Hybrid RAG",
        description="Dense + Sparse retrieval with re-ranking",
        complexity=3,
        latency="low-medium",
        accuracy="high",
    ),
    StrategyInfo(
        id="graph",
        name="Graph RAG",
        description="Knowledge graph-enhanced retrieval",
        complexity=4,
        latency="medium",
        accuracy="high",
    ),
    StrategyInfo(
        id="agentic",
        name="Agentic RAG",
        description="Autonomous multi-step reasoning with tool use",
        complexity=5,
        latency="medium-high",
        accuracy="very-high",
    ),
    StrategyInfo(
        id="memo",
        name="MemoRAG",
        description="Dual-system RAG with global memory and clue-guided retrieval",
        complexity=4,
        latency="medium",
        accuracy="high",
    ),
    StrategyInfo(
        id="corrective",
        name="Corrective RAG",
        description="Self-correcting retrieval with relevance grading and web fallback",
        complexity=3,
        latency="medium",
        accuracy="high",
    ),
]


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies():
    """List all available RAG strategies with details."""
    return StrategyListResponse(strategies=STRATEGY_DETAILS)


@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendation(request: RecommendationRequest):
    """Get AI-powered strategy recommendation."""
    return recommend_strategy(request)
