"""Add structured usage events for billing aggregates.

Revision ID: 0006_usage_events
Revises: 0005_migration_lifecycle
Create Date: 2026-07-20 00:00:05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

from alembic import op

revision: str = "0006_usage_events"
down_revision: str | None = "0005_migration_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE usage_operation AS ENUM "
        "('ingest', 'retrieve', 'update', 'delete'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "operation",
            PG_ENUM(name="usage_operation", create_type=False),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_usage_events_tenant_id", "usage_events", ["tenant_id"])
    op.create_index("ix_usage_events_user_id", "usage_events", ["user_id"])
    op.create_index("ix_usage_events_timestamp", "usage_events", ["timestamp"])
    op.create_index(
        "ix_usage_events_tenant_timestamp",
        "usage_events",
        ["tenant_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_events_tenant_timestamp", table_name="usage_events")
    op.drop_index("ix_usage_events_timestamp", table_name="usage_events")
    op.drop_index("ix_usage_events_user_id", table_name="usage_events")
    op.drop_index("ix_usage_events_tenant_id", table_name="usage_events")
    op.drop_table("usage_events")
    op.execute("DROP TYPE IF EXISTS usage_operation")
