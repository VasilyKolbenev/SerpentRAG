"""
SERPENT RAG PLATFORM — Application Factory
FastAPI application with multi-strategy RAG support.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware, setup_logging

logger = logging.getLogger("serpent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — initialize and cleanup services."""
    setup_logging()
    logger.info("Starting Serpent RAG Platform...")

    # Initialize services
    from app.services.cache import RedisService
    from app.services.embedding import EmbeddingService
    from app.services.graph_store import Neo4jService
    from app.services.llm import LLMService
    from app.services.tracing import TracingService
    from app.services.vector_store import QdrantService
    from app.strategies.factory import StrategyFactory

    # Cache (Redis)
    cache = RedisService()
    await cache.initialize()
    app.state.cache = cache

    # Embedding
    embedding = EmbeddingService()
    await embedding.initialize()
    app.state.embedding_service = embedding

    # Vector store (Qdrant)
    vector_store = QdrantService()
    await vector_store.initialize()
    app.state.vector_store = vector_store

    # Graph store (Neo4j)
    graph_store = Neo4jService()
    try:
        await graph_store.initialize()
    except Exception as e:
        logger.warning(f"Neo4j unavailable (Graph RAG disabled): {e}")
    app.state.graph_store = graph_store

    # LLM
    llm = LLMService()
    app.state.llm_service = llm

    # Tracing
    tracing = TracingService(cache=cache)
    app.state.tracing_service = tracing

    # Strategy factory
    factory = StrategyFactory(
        embedding_service=embedding,
        llm_service=llm,
        vector_store=vector_store,
        graph_store=graph_store,
        cache=cache,
    )
    app.state.strategy_factory = factory

    logger.info("All services initialized")
    yield

    # Cleanup
    logger.info("Shutting down Serpent RAG Platform...")
    await vector_store.close()
    await graph_store.close()
    await cache.close()
    from app.models.base import close_db
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Serpent RAG Platform",
        description="Universal self-hosted RAG platform with Agentic, Graph, Hybrid, and Simple strategies",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        max_age=3600,
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Tenant isolation (multi-tenancy)
    if settings.multi_tenancy_enabled:
        from app.middleware.tenant import TenantMiddleware
        app.add_middleware(TenantMiddleware)

    # Trusted hosts (production)
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[settings.domain],
        )

    # Telemetry (must be added before app starts — cannot add middleware in lifespan)
    from app.middleware.telemetry import setup_telemetry
    setup_telemetry(app)

    # Routers
    from app.api.router import api_router
    app.include_router(api_router)

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level=settings.log_level,
        access_log=True,
    )
