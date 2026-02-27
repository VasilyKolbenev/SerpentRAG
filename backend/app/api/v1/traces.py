"""
Pipeline trace endpoints for RAG Debugger.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import require_auth_in_production
from app.schemas.trace import PipelineTraceResponse

router = APIRouter(tags=["traces"])


@router.get("/traces/{trace_id}", response_model=PipelineTraceResponse)
async def get_trace(
    trace_id: str,
    req: Request,
    current_user: Optional[dict] = Depends(require_auth_in_production),
):
    """Get a pipeline trace for the RAG Debugger."""
    tracing = req.app.state.tracing_service
    trace_data = await tracing.get_trace(trace_id)

    if not trace_data:
        raise HTTPException(404, f"Trace {trace_id} not found")

    return PipelineTraceResponse(**trace_data)
