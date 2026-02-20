"""
Strategy recommendation schemas.
"""

from typing import Optional

from pydantic import BaseModel

from app.schemas.query import RAGStrategy


class RecommendationRequest(BaseModel):
    domain: str
    query_complexity: str
    data_structure: str
    priority: str
    description: Optional[str] = None


class RecommendationResponse(BaseModel):
    recommended: RAGStrategy
    scores: dict[str, float]
    reasoning: str


class StrategyInfo(BaseModel):
    id: str
    name: str
    description: str
    complexity: int
    latency: str
    accuracy: str


class StrategyListResponse(BaseModel):
    strategies: list[StrategyInfo]
