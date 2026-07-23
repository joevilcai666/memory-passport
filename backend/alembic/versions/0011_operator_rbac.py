"""Link API keys to team members/roles for operator RBAC enforcement.

Revision ID: 0011_operator_rbac
Revises: 0010_validation_remediation
Create Date: 2026-07-23 00:00:11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

from alembic import op

revision: str = "0011_operator_rbac"
down_revision: str | None = "0010_validation_remediation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # An API key may be linked to a console team member whose role authorises
    # operator actions (policy mutation, sensitive reveal). Nullable so legacy
    # and customer backend-to-backend keys keep working; a null role is treated
    # as Owner by the local-evaluation sandbox boundary.
    op.add_column(
        "api_keys",
        sa.Column(
            "team_member_id",
            sa.String(64),
            sa.ForeignKey("team_members.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "api_keys",
        sa.Column(
            "role",
            PG_ENUM(name="team_role", create_type=False),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_api_keys_team_member_id", "api_keys", ["team_member_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_team_member_id", table_name="api_keys")
    op.drop_column("api_keys", "role")
    op.drop_column("api_keys", "team_member_id")
    # PostgreSQL enum values cannot be removed safely; team_role is shared and
    # unaffected by this downgrade.
