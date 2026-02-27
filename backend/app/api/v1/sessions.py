"""
Chat session management endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    req: Request,
    current_user: dict = Depends(get_current_user),
):
    """List all active chat sessions for the current user."""
    user_id = current_user["sub"] if current_user else "anonymous"
    cache = req.app.state.cache
    sessions = await cache.list_chat_sessions(user_id)
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    req: Request,
    current_user: dict = Depends(get_current_user),
):
    """Delete a specific chat session."""
    user_id = current_user["sub"] if current_user else "anonymous"
    cache = req.app.state.cache
    deleted = await cache.delete_chat_session(user_id, session_id)
    return {"deleted": deleted, "session_id": session_id}


@router.post("")
async def create_session():
    """Create a new empty session ID (optional — auto-created on first query)."""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}
