"""
Pipeline trace endpoints for RAG Debugger.
"""

from fastapi import APIRouter, HTTPException, Request

from app.schemas.trace import PipelineTraceResponse

router = APIRouter(tags=["traces"])


@router.get("/traces/{trace_id}", response_model=PipelineTraceResponse)
async def get_trace(trace_id: str, req: Request):
    """Get a pipeline trace for the RAG Debugger."""
    tracing = req.app.state.tracing_service
    trace_data = await tracing.get_trace(trace_id)

    if not trace_data:
        raise HTTPException(404, f"Trace {trace_id} not found")

    return PipelineTraceResponse(**trace_data)
