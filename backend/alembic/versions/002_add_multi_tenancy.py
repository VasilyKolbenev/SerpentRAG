"""Add multi-tenancy support

Revision ID: 002_multi_tenancy
Revises: 001_initial
Create Date: 2025-01-15 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "002_multi_tenancy"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("slug", sa.String(128), unique=True, nullable=False),
        sa.Column("settings", sa.JSON, server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. Add tenant_id to existing tables
    for table_name in ["collections", "documents", "query_logs", "pipeline_traces"]:
        op.add_column(
            table_name,
            sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
        )
        op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"])

    # 3. Remove old unique constraint on collections.name, add composite unique
    op.drop_constraint("collections_name_key", "collections", type_="unique")
    op.create_unique_constraint(
        "uq_collections_tenant_name",
        "collections",
        ["tenant_id", "name"],
    )


def downgrade() -> None:
    # Remove composite unique, restore old unique
    op.drop_constraint("uq_collections_tenant_name", "collections", type_="unique")
    op.create_unique_constraint("collections_name_key", "collections", ["name"])

    # Remove tenant_id columns
    for table_name in ["collections", "documents", "query_logs", "pipeline_traces"]:
        op.drop_index(f"ix_{table_name}_tenant_id", table_name)
        op.drop_column(table_name, "tenant_id")

    # Drop tenants table
    op.drop_table("tenants")
