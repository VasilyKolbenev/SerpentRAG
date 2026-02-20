"""
SERPENT RAG PLATFORM — Configuration
Uses pydantic-settings for type-safe environment variable loading.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://serpent:serpent@localhost:5432/serpent"
    redis_url: str = "redis://localhost:6379/0"

    # Vector Store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Graph Store
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Application
    environment: str = "development"
    upload_dir: str = "/app/uploads"
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    frontend_url: str = "http://localhost:3000"
    domain: str = "localhost"
    log_level: str = "info"

    # Embedding
    embedding_provider: str = "local"  # local | openai
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024

    # Web Search (CRAG)
    web_search_api_key: str = ""
    web_search_provider: str = "tavily"  # tavily | serpapi

    # Multi-Tenancy
    multi_tenancy_enabled: bool = False

    # Sync database URL for Celery workers
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg2").replace(
            "postgresql+psycopg2", "postgresql"
        )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
