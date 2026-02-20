"""
Health check endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Request

from app.schemas.metrics import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint with real service connectivity checks."""
    app = request.app
    services = {"api": "healthy"}

    # Check each service
    for name, check_fn in [
        ("vector_store", lambda: app.state.vector_store.health_check()),
        ("graph_store", lambda: app.state.graph_store.health_check()),
        ("cache", lambda: app.state.cache.health_check()),
    ]:
        try:
            is_healthy = await check_fn()
            services[name] = "healthy" if is_healthy else "unhealthy"
        except Exception:
            services[name] = "unhealthy"

    # Check database
    try:
        from app.models.base import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"

    return HealthResponse(
        status=overall,
        version="1.0.0",
        services=services,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/readyz")
async def readiness_check():
    """Kubernetes-style readiness probe."""
    return {"status": "ready"}
