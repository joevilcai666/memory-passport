"""Add provisioning audit_action values.

Revision ID: 0002_audit_actions
Revises: 0001_initial
Create Date: 2026-07-20 00:00:01

Slice 2 introduces five new ``audit_action`` enum literals for the provisioning
endpoints (one per created entity):

    app.created, agent.created, user.created,
    relationship.created, device.registered

``ALTER TYPE ... ADD VALUE IF NOT EXISTS`` is idempotent and safe inside a
transaction on PG 12+. Downgrade is a no-op: Postgres can't remove individual
enum values without rebuilding the type, and ``downgrade base`` (exercised by
``test_migrations.py``) drops the whole ``audit_action`` type anyway, so there's
nothing meaningful to reverse here.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_audit_actions"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_VALUES = (
    "app.created",
    "agent.created",
    "user.created",
    "relationship.created",
    "device.registered",
)


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres cannot DROP an individual enum value. ``downgrade base`` drops
    # the entire ``audit_action`` type via 0001_initial's downgrade, which
    # clears these values too. No-op here is the documented, safe choice.
    pass
