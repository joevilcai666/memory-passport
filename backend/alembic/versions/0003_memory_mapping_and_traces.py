"""Add memory_record_hms_units + retrieval_traces tables.

Revision ID: 0003_memory_mapping_and_traces
Revises: 0002_audit_actions
Create Date: 2026-07-20 00:00:02

Slice 3 introduces the MP↔HMS mapping table (1:1 link between an MP
``MemoryRecord`` and the HMS ``memory_unit`` it mirrors) so Slice 4's retrieve
pipeline can join HMS ``recall`` results back to MP rows. Slice 4 adds the
``retrieval_traces`` table for the debug-trace endpoint (PRD §8 P0, ≥7d TTL).

Both tables are dialect-aware: JSONB on Postgres, JSON on sqlite (tests).
Downgrade drops both — they have no data the rest of the schema depends on.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0003_memory_mapping_and_traces"
down_revision: str | None = "0002_audit_actions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json():
    """JSONB on Postgres, JSON on sqlite — mirrors app.db.base.jsonb()."""
    return JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "memory_record_hms_units",
        sa.Column("mp_memory_id", sa.String(64), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hms_unit_id", sa.String(64), nullable=False),
        sa.Column("hms_bank_id", sa.String(64), nullable=False),
        sa.Column("hms_document_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKey(
            ["mp_memory_id"], ["memory_records.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_memory_record_hms_units_tenant_id",
        "memory_record_hms_units",
        ["tenant_id"],
    )
    op.create_index(
        "ix_memory_record_hms_units_hms_unit_id",
        "memory_record_hms_units",
        ["hms_unit_id"],
    )
    op.create_index(
        "ix_memory_record_hms_units_hms_bank_id",
        "memory_record_hms_units",
        ["hms_bank_id"],
    )
    op.create_index(
        "ix_memory_record_hms_units_hms_document_id",
        "memory_record_hms_units",
        ["hms_document_id"],
    )
    op.create_index(
        "ix_hms_mapping_unit",
        "memory_record_hms_units",
        ["hms_unit_id", "hms_bank_id"],
    )

    op.create_table(
        "retrieval_traces",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("caller", _json(), nullable=False),
        sa.Column("hms_results", _json(), nullable=False),
        sa.Column("projected", _json(), nullable=False),
        sa.Column("retrieval_events", _json(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_retrieval_traces_tenant_id",
        "retrieval_traces",
        ["tenant_id"],
    )
    op.create_index(
        "ix_retrieval_traces_created_at",
        "retrieval_traces",
        ["created_at"],
    )
    op.create_index(
        "ix_retrieval_traces_tenant_created",
        "retrieval_traces",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_retrieval_traces_tenant_created", table_name="retrieval_traces")
    op.drop_index("ix_retrieval_traces_created_at", table_name="retrieval_traces")
    op.drop_index("ix_retrieval_traces_tenant_id", table_name="retrieval_traces")
    op.drop_table("retrieval_traces")

    op.drop_index("ix_hms_mapping_unit", table_name="memory_record_hms_units")
    op.drop_index(
        "ix_memory_record_hms_units_hms_document_id", table_name="memory_record_hms_units"
    )
    op.drop_index(
        "ix_memory_record_hms_units_hms_bank_id", table_name="memory_record_hms_units"
    )
    op.drop_index(
        "ix_memory_record_hms_units_hms_unit_id", table_name="memory_record_hms_units"
    )
    op.drop_index(
        "ix_memory_record_hms_units_tenant_id", table_name="memory_record_hms_units"
    )
    op.drop_table("memory_record_hms_units")
