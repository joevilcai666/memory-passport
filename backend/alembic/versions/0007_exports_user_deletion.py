"""Add export jobs, passport deletion fields, and user.deleted audit action.

Revision ID: 0007_exports_user_deletion
Revises: 0006_usage_events
Create Date: 2026-07-20 00:00:06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

from alembic import op

revision: str = "0007_exports_user_deletion"
down_revision: str | None = "0006_usage_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_enum(name: str, values: tuple[str, ...]) -> None:
    vals = ", ".join(f"'{value}'" for value in values)
    op.execute(
        f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({vals}); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )


def upgrade() -> None:
    _create_enum("passport_status", ("active", "deleted"))
    _create_enum("export_status", ("pending", "completed", "failed"))
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'user.deleted'")
    op.add_column(
        "users",
        sa.Column(
            "passport_status",
            PG_ENUM(name="passport_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "users", sa.Column("passport_deleted_at", sa.DateTime(), nullable=True)
    )
    op.create_table(
        "export_jobs",
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
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column(
            "status",
            PG_ENUM(name="export_status", create_type=False),
            nullable=False,
        ),
        sa.Column("download_token_hash", sa.String(64), nullable=False),
        sa.Column("download_token_expires_at", sa.DateTime(), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_export_jobs_tenant_id", "export_jobs", ["tenant_id"])
    op.create_index("ix_export_jobs_user_id", "export_jobs", ["user_id"])
    op.create_index(
        "ix_export_jobs_tenant_created", "export_jobs", ["tenant_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_export_jobs_tenant_created", table_name="export_jobs")
    op.drop_index("ix_export_jobs_user_id", table_name="export_jobs")
    op.drop_index("ix_export_jobs_tenant_id", table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_column("users", "passport_deleted_at")
    op.drop_column("users", "passport_status")
    op.execute("DROP TYPE IF EXISTS export_status")
    op.execute("DROP TYPE IF EXISTS passport_status")
