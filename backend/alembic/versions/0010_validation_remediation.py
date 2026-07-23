"""Add V0.1 console team records and retrieval feedback.

Revision ID: 0010_validation_remediation
Revises: 0009_tenant_hms_credentials
Create Date: 2026-07-22 00:00:10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0010_validation_remediation"
down_revision: str | None = "0009_tenant_hms_credentials"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_AUDIT_ACTIONS = (
    "api_key.created",
    "api_key.rotated",
    "user.consent_changed",
    "retrieval.feedback_recorded",
    "team.invited",
    "team.joined",
)


def upgrade() -> None:
    for action in _AUDIT_ACTIONS:
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{action}'")

    op.add_column(
        "retrieval_traces",
        sa.Column("feedback", JSONB(), nullable=True),
    )

    op.create_table(
        "team_members",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", PG_ENUM(name="team_role", create_type=False), nullable=False),
        sa.Column("avatar_color", sa.String(32), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.Column("last_active", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "email", name="uq_team_members_tenant_email"
        ),
    )
    op.create_index("ix_team_members_tenant_id", "team_members", ["tenant_id"])
    op.create_index(
        "ix_team_members_tenant_role", "team_members", ["tenant_id", "role"]
    )

    op.create_table(
        "team_invites",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", PG_ENUM(name="team_role", create_type=False), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "accepted_member_id",
            sa.String(64),
            sa.ForeignKey("team_members.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
    )
    op.create_index("ix_team_invites_tenant_id", "team_invites", ["tenant_id"])
    op.create_index("ix_team_invites_expires_at", "team_invites", ["expires_at"])
    op.create_index(
        "ix_team_invites_tenant_email", "team_invites", ["tenant_id", "email"]
    )


def downgrade() -> None:
    op.drop_index("ix_team_invites_tenant_email", table_name="team_invites")
    op.drop_index("ix_team_invites_expires_at", table_name="team_invites")
    op.drop_index("ix_team_invites_tenant_id", table_name="team_invites")
    op.drop_table("team_invites")
    op.drop_index("ix_team_members_tenant_role", table_name="team_members")
    op.drop_index("ix_team_members_tenant_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_column("retrieval_traces", "feedback")
    # PostgreSQL enum values cannot be removed safely while preserving the
    # audit_action type. The added literals remain unused after downgrade.
