"""
Root test fixtures — mock services, test app, httpx client.
All tests run without Docker (pure mocks, ~5s total).
"""

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.dependencies import AuthService
from app.schemas.query import RAGStrategy
from app.services.cache import RedisService
from app.services.embedding import EmbeddingService
from app.services.graph_store import GraphEdge, GraphNode, Neo4jService
from app.services.llm import LLMService
from app.services.tracing import TracingService
from app.services.vector_store import QdrantService, SearchResult
from app.strategies.factory import StrategyFactory


# ── Settings ──


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with safe defaults (no real connections)."""
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        qdrant_url="http://localhost:6333",
        neo4j_uri="bolt://localhost:7687",
        neo4j_password="test",
        openai_api_key="sk-test-key",
        anthropic_api_key="test-anthropic-key",
        jwt_secret="test-secret-key-for-jwt",
        environment="testing",
        upload_dir="/tmp/serpent-test-uploads",
        embedding_provider="local",
        embedding_model="test-model",
        embedding_dimensions=1024,
    )


# ── Mock Services ──


@pytest.fixture
def mock_embedding_service() -> AsyncMock:
    """Mock EmbeddingService — returns fixed 1024-dim vectors."""
    svc = AsyncMock(spec=EmbeddingService)
    svc.embed.return_value = [[0.1] * 1024]
    svc.embed_query.return_value = [0.1] * 1024
    svc._model_name = "test-model"
    svc.dimensions = 1024
    return svc


@pytest.fixture
def mock_llm_service() -> AsyncMock:
    """Mock LLMService — returns fixed answers."""
    svc = AsyncMock(spec=LLMService)
    svc.generate.return_value = "Test answer based on context."

    async def _stream_gen(*args, **kwargs):
        for token in ["Test ", "answer ", "based ", "on ", "context."]:
            yield token

    svc.stream_generate = _stream_gen
    svc.structured_extract.return_value = '["entity1", "entity2"]'
    svc._build_prompt = LLMService._build_prompt.__get__(svc, LLMService)
    svc._resolve_model = LLMService._resolve_model.__get__(svc, LLMService)
    return svc


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Mock QdrantService — returns 2 search results."""
    svc = AsyncMock(spec=QdrantService)
    svc.search.return_value = [
        SearchResult(
            id="chunk_1",
            content="First relevant chunk about the topic.",
            score=0.92,
            metadata={"source": "doc1.pdf", "page": 1},
        ),
        SearchResult(
            id="chunk_2",
            content="Second relevant chunk with more details.",
            score=0.85,
            metadata={"source": "doc1.pdf", "page": 3},
        ),
    ]
    svc.health_check.return_value = True
    svc.get_collections.return_value = ["default", "test-collection"]
    svc.collection_info.return_value = {
        "name": "default",
        "points_count": 150,
        "status": "green",
    }
    svc.ensure_collection.return_value = None
    svc.upsert.return_value = None
    svc.delete_collection.return_value = None
    return svc


@pytest.fixture
def mock_graph_store() -> AsyncMock:
    """Mock Neo4jService — returns test nodes and edges."""
    svc = AsyncMock(spec=Neo4jService)
    svc.traverse.return_value = (
        [
            GraphNode(id="n1", name="Python", type="Technology", properties={"popularity": "high"}),
            GraphNode(id="n2", name="FastAPI", type="Framework", properties={"language": "Python"}),
        ],
        [
            GraphEdge(source="FastAPI", target="Python", type="BUILT_WITH", properties={}),
        ],
    )
    svc.find_entities.return_value = [
        GraphNode(id="n1", name="Python", type="Technology", properties={}),
    ]
    svc.get_subgraph.return_value = {
        "nodes": [
            {"id": "n1", "name": "Python", "type": "Technology"},
            {"id": "n2", "name": "FastAPI", "type": "Framework"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "type": "BUILT_WITH"},
        ],
    }
    svc.health_check.return_value = True
    return svc


@pytest.fixture
def mock_cache_service() -> AsyncMock:
    """Mock RedisService — all gets return None, all sets succeed."""
    svc = AsyncMock(spec=RedisService)
    svc.get_query_cache.return_value = None
    svc.set_query_cache.return_value = None
    svc.invalidate_collection_cache.return_value = None
    svc.store_trace.return_value = None
    svc.get_trace.return_value = None
    svc.get_embedding_cache.return_value = None
    svc.set_embedding_cache.return_value = None
    # MemoRAG
    svc.get_memo_memory.return_value = None
    svc.set_memo_memory.return_value = None
    # Advisor
    svc.get_advisor_session.return_value = None
    svc.set_advisor_session.return_value = None
    svc.health_check.return_value = True
    return svc


# ── Strategy Factory (with mocks) ──


@pytest.fixture
def mock_strategy_factory(
    mock_embedding_service: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_graph_store: AsyncMock,
    mock_cache_service: AsyncMock,
) -> StrategyFactory:
    """Real StrategyFactory wired with mock services."""
    return StrategyFactory(
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service,
        vector_store=mock_vector_store,
        graph_store=mock_graph_store,
        cache=mock_cache_service,
    )


# ── Tracing ──


@pytest.fixture
def mock_tracing_service(mock_cache_service: AsyncMock) -> TracingService:
    """Real TracingService with mock cache."""
    return TracingService(cache=mock_cache_service)


# ── FastAPI Test App ──


@pytest.fixture
def app(
    mock_vector_store: AsyncMock,
    mock_graph_store: AsyncMock,
    mock_cache_service: AsyncMock,
    mock_embedding_service: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_strategy_factory: StrategyFactory,
    mock_tracing_service: TracingService,
) -> FastAPI:
    """Bare FastAPI app with mock services injected (no lifespan)."""
    from app.api.router import api_router

    test_app = FastAPI()
    test_app.include_router(api_router)

    # Inject mock services into app.state
    test_app.state.vector_store = mock_vector_store
    test_app.state.graph_store = mock_graph_store
    test_app.state.cache = mock_cache_service
    test_app.state.embedding_service = mock_embedding_service
    test_app.state.llm_service = mock_llm_service
    test_app.state.strategy_factory = mock_strategy_factory
    test_app.state.tracing_service = mock_tracing_service

    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Auth ──


@pytest.fixture
def auth_token() -> str:
    """Valid JWT token for test user."""
    with patch("app.dependencies.settings") as mock_settings:
        mock_settings.jwt_secret = "test-secret-key-for-jwt"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_expire_hours = 24
        return AuthService.create_token(user_id="test-user", role="user")


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization headers with valid Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}
