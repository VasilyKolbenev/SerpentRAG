"""
Pipeline trace schemas for RAG Debugger.
"""

from pydantic import BaseModel


class TraceStep(BaseModel):
    name: str
    duration_ms: float
    input_summary: str = ""
    output_summary: str = ""
    result_count: int = 0
    details: dict = {}


class PipelineTraceResponse(BaseModel):
    trace_id: str
    query: str
    strategy: str
    collection: str
    total_latency_ms: float
    steps: list[TraceStep]
    chunks_retrieved: int
    answer_length: int
    model: str
