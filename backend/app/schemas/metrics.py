"""
Quality metrics schemas (RAGAS).
"""

from typing import Optional

from pydantic import BaseModel


class QualityScores(BaseModel):
    faithfulness: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    answer_relevancy: Optional[float] = None


class QualityMetricsResponse(BaseModel):
    strategy: str
    period: str
    total_queries: int
    avg_scores: QualityScores
    avg_latency_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
    timestamp: str
