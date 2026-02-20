"""
Tests for trace endpoints — GET /traces/{trace_id}.
"""

import pytest
from httpx import AsyncClient


class TestTracesEndpoint:
    """GET /traces/{trace_id} — RAG Debugger data."""

    async def test_get_trace_not_found(self, client: AsyncClient, app):
        app.state.tracing_service._cache.get_trace.return_value = None
        response = await client.get("/traces/nonexistent-id")
        assert response.status_code == 404

    async def test_get_trace_returns_data(self, client: AsyncClient, app):
        trace_data = {
            "trace_id": "test-trace-1",
            "query": "What is Python?",
            "strategy": "naive",
            "collection": "default",
            "total_latency_ms": 150.5,
            "steps": [
                {
                    "name": "embedding",
                    "duration_ms": 10.2,
                    "input_summary": "len=17",
                    "output_summary": "dim=1024",
                    "result_count": 1,
                    "details": {},
                },
                {
                    "name": "vector_search",
                    "duration_ms": 50.3,
                    "input_summary": "top_k=5",
                    "output_summary": "found=3",
                    "result_count": 3,
                    "details": {},
                },
            ],
            "chunks_retrieved": 3,
            "answer_length": 200,
            "model": "gpt-4o",
        }
        app.state.tracing_service._cache.get_trace.return_value = trace_data

        response = await client.get("/traces/test-trace-1")
        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == "test-trace-1"
        assert data["strategy"] == "naive"
        assert len(data["steps"]) == 2
        assert data["chunks_retrieved"] == 3
