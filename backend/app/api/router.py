"""
Main API router — aggregates all v1 sub-routers.
"""

from fastapi import APIRouter

from app.api.v1 import (
    advisor,
    collections,
    documents,
    graph,
    health,
    metrics,
    query,
    sessions,
    strategies,
    traces,
)

api_router = APIRouter()

# Health (no prefix)
api_router.include_router(health.router)

# V1 endpoints
api_router.include_router(query.router)
api_router.include_router(documents.router)
api_router.include_router(collections.router)
api_router.include_router(strategies.router)
api_router.include_router(traces.router)
api_router.include_router(graph.router)
api_router.include_router(metrics.router)
api_router.include_router(advisor.router)
api_router.include_router(sessions.router)
