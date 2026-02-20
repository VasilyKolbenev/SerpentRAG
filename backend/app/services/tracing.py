"""
Pipeline tracing service for RAG Debugger.
Records each step of the retrieval pipeline with timing and metadata.
"""

import time
import uuid
import logging
from typing import Optional

from app.services.cache import RedisService

logger = logging.getLogger("serpent.tracing")


class TraceRecorder:
    """Records steps for a single pipeline execution."""

    def __init__(self, query: str, strategy: str, collection: str) -> None:
        self.trace_id = str(uuid.uuid4())
        self.query = query
        self.strategy = strategy
        self.collection = collection
        self.steps: list[dict] = []
        self._start_time = time.perf_counter()
        self._step_start: Optional[float] = None

    def start_step(self, name: str, input_summary: str = "") -> None:
        """Mark the beginning of a pipeline step."""
        self._step_start = time.perf_counter()
        self._current_step_name = name
        self._current_input = input_summary

    def end_step(
        self,
        output_summary: str = "",
        result_count: int = 0,
        details: Optional[dict] = None,
    ) -> None:
        """Mark the end of a pipeline step and record it."""
        if self._step_start is None:
            return

        duration_ms = (time.perf_counter() - self._step_start) * 1000
        self.steps.append({
            "name": self._current_step_name,
            "duration_ms": round(duration_ms, 2),
            "input_summary": self._current_input,
            "output_summary": output_summary,
            "result_count": result_count,
            "details": details or {},
        })
        self._step_start = None

    @property
    def total_latency_ms(self) -> float:
        return round((time.perf_counter() - self._start_time) * 1000, 2)

    def to_dict(self, chunks_retrieved: int = 0, answer_length: int = 0, model: str = "") -> dict:
        """Serialize trace to dict for storage."""
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "strategy": self.strategy,
            "collection": self.collection,
            "total_latency_ms": self.total_latency_ms,
            "steps": self.steps,
            "chunks_retrieved": chunks_retrieved,
            "answer_length": answer_length,
            "model": model,
        }


class TracingService:
    """Manages pipeline traces — storage and retrieval."""

    def __init__(self, cache: RedisService) -> None:
        self._cache = cache

    def create_recorder(
        self, query: str, strategy: str, collection: str
    ) -> TraceRecorder:
        """Create a new trace recorder for a pipeline execution."""
        return TraceRecorder(query=query, strategy=strategy, collection=collection)

    async def save_trace(self, trace: TraceRecorder, **kwargs) -> None:
        """Save a completed trace to Redis."""
        trace_data = trace.to_dict(**kwargs)
        await self._cache.store_trace(trace.trace_id, trace_data)
        logger.info(
            "Trace saved",
            extra={
                "trace_id": trace.trace_id,
                "strategy": trace.strategy,
                "latency_ms": trace.total_latency_ms,
            },
        )

    async def get_trace(self, trace_id: str) -> Optional[dict]:
        """Retrieve a trace by ID."""
        return await self._cache.get_trace(trace_id)
