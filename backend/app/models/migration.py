"""Migration — the v1→v2 device migration wedge.

Mirrors ``Migration`` in ``src/lib/types.ts``. ``selected_memory_ids`` /
``skipped_memory_ids`` are stored as JSONB arrays (the set of memory ids the
user picked / explicitly skipped during the migration preview).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, jsonb
from app.models.enums import (
    PG_MIGRATION_STATUS,
    PG_OLD_DEVICE_ACCESS,
    MigrationStatus,
    OldDeviceAccess,
)


class Migration(Base):
    """A device-to-device memory migration (the hero flow)."""

    __tablename__ = "migrations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_relationship_id: Mapped[str] = mapped_column(
        ForeignKey("relationships.id", ondelete="RESTRICT"), nullable=False
    )
    target_relationship_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    target_device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[MigrationStatus] = mapped_column(PG_MIGRATION_STATUS, nullable=False)
    # JSONB arrays of memory ids — kept whole because they're a snapshot of
    # user intent at preview time, not a query target.
    selected_memory_ids: Mapped[list[Any]] = mapped_column(jsonb(), nullable=False, default=list)
    skipped_memory_ids: Mapped[list[Any]] = mapped_column(jsonb(), nullable=False, default=list)
    failed_memory_ids: Mapped[list[Any]] = mapped_column(jsonb(), nullable=False, default=list)
    rollback_snapshot: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False, default=dict)

    old_device_access: Mapped[OldDeviceAccess] = mapped_column(PG_OLD_DEVICE_ACCESS, nullable=False)
    audit_log_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<Migration {self.id} ({self.status})>"
