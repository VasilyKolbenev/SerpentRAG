"""
Quality metrics endpoints (RAGAS dashboard).
"""

from fastapi import APIRouter, Request

from app.schemas.metrics import QualityMetricsResponse, QualityScores

router = APIRouter(tags=["metrics"])


@router.get("/metrics/quality", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    req: Request,
    strategy: str = "all",
    period: str = "7d",
):
    """Get aggregated RAG quality metrics from query logs."""
    # Query from database
    # For now, return placeholder structure
    # Real implementation would aggregate from query_logs table

    return QualityMetricsResponse(
        strategy=strategy,
        period=period,
        total_queries=0,
        avg_scores=QualityScores(),
        avg_latency_ms=0,
    )
