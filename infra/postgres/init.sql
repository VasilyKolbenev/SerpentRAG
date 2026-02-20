-- Serpent RAG — PostgreSQL initialization
-- Enables pgvector extension for vector embeddings

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
