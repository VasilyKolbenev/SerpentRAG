"""
Query request/response schemas.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RAGStrategy(str, Enum):
    AGENTIC = "agentic"
    CORRECTIVE = "corrective"
    GRAPH = "graph"
    HYBRID = "hybrid"
    MEMO = "memo"
    NAIVE = "naive"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    strategy: RAGStrategy = RAGStrategy.HYBRID
    collection: str = "default"
    top_k: int = Field(default=10, ge=1, le=50)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    model: str = "gpt-4o"
    filters: Optional[dict] = None

    # Agentic-specific
    max_iterations: int = Field(default=5, ge=1, le=20)
    enable_planning: bool = True
    enable_reflection: bool = True

    # Graph-specific
    max_hops: int = Field(default=3, ge=1, le=10)
    entity_types: Optional[list[str]] = None

    # Hybrid-specific
    sparse_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    enable_reranking: bool = True
    reranker_type: str = "cross-encoder"  # cross-encoder | colbert

    # MemoRAG-specific
    light_model: str = "claude-3-haiku-20240307"

    # CRAG-specific
    relevance_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    web_search_enabled: bool = False

    # Sufficient Context Check
    check_sufficiency: bool = False
    sufficiency_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    sufficiency_action: str = "abstain"  # abstain | retry

    # Conversation history
    session_id: Optional[str] = Field(None, description="Chat session ID for conversation context")


class SourceInfo(BaseModel):
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    strategy_used: RAGStrategy
    metadata: dict
    latency_ms: float
    trace_id: str
    session_id: Optional[str] = None


class StreamChunk(BaseModel):
    event: str  # status | sources | token | done
    data: dict


class CompareRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    strategies: list[RAGStrategy] = Field(
        ..., min_length=2, max_length=4
    )
    collection: str = "default"
    top_k: int = Field(default=10, ge=1, le=50)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    model: str = "gpt-4o"


class CompareResult(BaseModel):
    strategy: RAGStrategy
    answer: str
    sources: list[SourceInfo]
    latency_ms: float
    trace_id: str
    quality_scores: Optional[dict] = None


class CompareResponse(BaseModel):
    query: str
    results: list[CompareResult]
