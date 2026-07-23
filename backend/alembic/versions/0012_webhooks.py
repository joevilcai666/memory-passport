"""Signed tenant webhooks — endpoints + immutable delivery records (issue #33).

Revision ID: 0012_webhooks
Revises: 0011_operator_rbac
Create Date: 2026-07-23 00:00:12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

from alembic import op

revision: str = "0012_webhooks"
down_revision: str | None = "0011_operator_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_AUDIT_ACTIONS = (
    "webhook.created",
    "webhook.delivered",
    "webhook.failed",
)


def _create_enum_type(name: str, values: tuple[str, ...]) -> None:
    """Create a Postgres enum type idempotently (DO/EXCEPTION, as in 0001)."""
    literals = ", ".join(f"'{v}'" for v in values)
    op.execute(
        f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({literals}); "
        f"EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )


def upgrade() -> None:
    for action in _AUDIT_ACTIONS:
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{action}'")

    _create_enum_type(
        "webhook_event_type",
        (
            "memory.created",
            "memory.needs_confirmation",
            "memory.deleted",
            "migration.completed",
            "migration.failed",
            "device.bound",
            "device.unbound",
        ),
    )
    _create_enum_type(
        "webhook_delivery_status",
        ("pending", "delivered", "failed"),
    )

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("signing_secret_hash", sa.String(64), nullable=False),
        sa.Column("events", sa.dialects.postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
    )
    op.create_index("ix_webhook_endpoints_tenant_id", "webhook_endpoints", ["tenant_id"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "endpoint_id",
            sa.String(64),
            sa.ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            PG_ENUM(name="webhook_event_type", create_type=False),
            nullable=False,
        ),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            PG_ENUM(name="webhook_delivery_status", create_type=False),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_webhook_deliveries_tenant_id", "webhook_deliveries", ["tenant_id"]
    )
    op.create_index(
        "ix_webhook_deliveries_tenant_status",
        "webhook_deliveries",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_tenant_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_tenant_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index("ix_webhook_endpoints_tenant_id", table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")
    op.execute("DROP TYPE IF EXISTS webhook_delivery_status")
    op.execute("DROP TYPE IF EXISTS webhook_event_type")
    # PostgreSQL enum values cannot be removed safely; the audit_action literals
    # remain unused after downgrade.
