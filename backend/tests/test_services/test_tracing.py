"""
Tests for TraceRecorder (pure logic) and TracingService (save/get).
"""

import time
from unittest.mock import AsyncMock

from app.services.tracing import TraceRecorder, TracingService


class TestTraceRecorder:
    """TraceRecorder — pure logic, no external deps."""

    def test_init_generates_uuid(self):
        trace = TraceRecorder(query="test", strategy="naive", collection="default")
        assert trace.trace_id is not None
        assert len(trace.trace_id) == 36  # UUID format
        assert trace.query == "test"
        assert trace.strategy == "naive"

    def test_start_end_step_records(self):
        trace = TraceRecorder(query="q", strategy="hybrid", collection="c")
        trace.start_step("embedding", input_summary="len=10")
        time.sleep(0.01)
        trace.end_step(output_summary="dim=1024", result_count=1)

        assert len(trace.steps) == 1
        step = trace.steps[0]
        assert step["name"] == "embedding"
        assert step["input_summary"] == "len=10"
        assert step["output_summary"] == "dim=1024"
        assert step["result_count"] == 1
        assert step["duration_ms"] > 0

    def test_end_step_without_start_does_nothing(self):
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        trace.end_step(output_summary="orphan")
        assert len(trace.steps) == 0

    def test_total_latency_ms_increases(self):
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        time.sleep(0.01)
        latency = trace.total_latency_ms
        assert latency > 0

    def test_to_dict_serializes_correctly(self):
        trace = TraceRecorder(query="test query", strategy="graph", collection="docs")
        trace.start_step("step1")
        trace.end_step(result_count=5)

        result = trace.to_dict(chunks_retrieved=10, answer_length=200, model="gpt-4o")
        assert result["trace_id"] == trace.trace_id
        assert result["query"] == "test query"
        assert result["strategy"] == "graph"
        assert result["collection"] == "docs"
        assert result["chunks_retrieved"] == 10
        assert result["answer_length"] == 200
        assert result["model"] == "gpt-4o"
        assert len(result["steps"]) == 1

    def test_multiple_steps(self):
        trace = TraceRecorder(query="q", strategy="hybrid", collection="c")
        for name in ["embedding", "dense", "sparse", "fusion", "reranking"]:
            trace.start_step(name)
            trace.end_step(result_count=1)
        assert len(trace.steps) == 5
        assert [s["name"] for s in trace.steps] == [
            "embedding", "dense", "sparse", "fusion", "reranking"
        ]


class TestTracingService:
    """TracingService — save/get with mock cache."""

    async def test_create_recorder(self):
        cache = AsyncMock()
        svc = TracingService(cache=cache)
        recorder = svc.create_recorder("q", "naive", "default")
        assert isinstance(recorder, TraceRecorder)
        assert recorder.query == "q"

    async def test_save_trace_calls_cache(self):
        cache = AsyncMock()
        svc = TracingService(cache=cache)
        trace = TraceRecorder(query="q", strategy="naive", collection="c")
        await svc.save_trace(trace, chunks_retrieved=5, answer_length=100, model="gpt-4o")
        cache.store_trace.assert_called_once()
        call_args = cache.store_trace.call_args
        assert call_args[0][0] == trace.trace_id

    async def test_get_trace_returns_cache_result(self):
        cache = AsyncMock()
        cache.get_trace.return_value = {"trace_id": "abc", "query": "test"}
        svc = TracingService(cache=cache)
        result = await svc.get_trace("abc")
        assert result["trace_id"] == "abc"
        cache.get_trace.assert_called_once_with("abc")

    async def test_get_trace_returns_none_when_missing(self):
        cache = AsyncMock()
        cache.get_trace.return_value = None
        svc = TracingService(cache=cache)
        result = await svc.get_trace("nonexistent")
        assert result is None
