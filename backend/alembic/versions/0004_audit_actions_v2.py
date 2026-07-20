"""Add pipeline audit_action values (memory.blocked, retrieval.performed, device.wiped).

Revision ID: 0004_audit_actions_v2
Revises: 0003_memory_mapping_and_traces
Create Date: 2026-07-20 00:00:03

Slices 3/4/7 add three new ``audit_action`` literals:

    memory.blocked        — S3-sensitivity event blocked end-to-end (Slice 3)
    retrieval.performed   — a retrieve call completed (Slice 4)
    device.wiped          — a device was factory-reset + device_only tombstoned (Slice 7)

``ALTER TYPE ... ADD VALUE IF NOT EXISTS`` is idempotent and PG-12+-safe inside
a transaction. Downgrade is a no-op (PG can't drop individual enum values;
``downgrade base`` drops the whole ``audit_action`` type via 0001's downgrade).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_audit_actions_v2"
down_revision: str | None = "0003_memory_mapping_and_traces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_VALUES = (
    "memory.blocked",
    "retrieval.performed",
    "device.wiped",
)


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    pass
