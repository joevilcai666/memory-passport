"""Add retry/rollback fields and enum literals for the migration lifecycle.

Revision ID: 0005_migration_lifecycle
Revises: 0004_audit_actions_v2
Create Date: 2026-07-20 00:00:04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0005_migration_lifecycle"
down_revision: str | None = "0004_audit_actions_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE migration_status ADD VALUE IF NOT EXISTS 'rolled_back'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'migration.rolled_back'")
    op.add_column(
        "migrations",
        sa.Column(
            "failed_memory_ids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "migrations",
        sa.Column(
            "rollback_snapshot",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("migrations", sa.Column("rolled_back_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("migrations", "rolled_back_at")
    op.drop_column("migrations", "rollback_snapshot")
    op.drop_column("migrations", "failed_memory_ids")
