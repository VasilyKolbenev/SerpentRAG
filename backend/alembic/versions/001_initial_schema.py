"""Initial schema — collections, documents, chunks, query_logs, pipeline_traces.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Collections
    op.create_table(
        "collections",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("document_count", sa.Integer, server_default="0"),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(32), server_default="processing"),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column(
            "collection_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("collections.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_documents_collection_status", "documents", ["collection_id", "status"]
    )

    # Chunks
    op.create_table(
        "chunks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("token_count", sa.Integer, server_default="0"),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("metadata", sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column(
            "document_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_chunks_document", "chunks", ["document_id"])

    # Query logs
    op.create_table(
        "query_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("collection", sa.String(255), server_default="default"),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("chunks_retrieved", sa.Integer, server_default="0"),
        sa.Column("token_count", sa.Integer, server_default="0"),
        sa.Column("faithfulness", sa.Float, nullable=True),
        sa.Column("context_precision", sa.Float, nullable=True),
        sa.Column("context_recall", sa.Float, nullable=True),
        sa.Column("answer_relevancy", sa.Float, nullable=True),
        sa.Column(
            "trace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("metadata", sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_query_logs_strategy", "query_logs", ["strategy"])
    op.create_index(
        "ix_query_logs_created", "query_logs", ["created_at"]
    )

    # Pipeline traces
    op.create_table(
        "pipeline_traces",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            unique=True,
            nullable=False,
        ),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("collection", sa.String(255), server_default="default"),
        sa.Column("total_latency_ms", sa.Float, nullable=False),
        sa.Column("steps", sa.JSON, server_default=sa.text("'[]'::json")),
        sa.Column("chunks_retrieved", sa.Integer, server_default="0"),
        sa.Column("answer_length", sa.Integer, server_default="0"),
        sa.Column("model", sa.String(128), server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_traces_strategy", "pipeline_traces", ["strategy"])
    op.create_index("ix_traces_created", "pipeline_traces", ["created_at"])


def downgrade() -> None:
    op.drop_table("pipeline_traces")
    op.drop_table("query_logs")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("collections")
