"""Structured tenant/user operation events used for billing aggregates."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PG_USAGE_OPERATION, UsageOperation


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation: Mapped[UsageOperation] = mapped_column(PG_USAGE_OPERATION, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        Index("ix_usage_events_tenant_timestamp", "tenant_id", "timestamp"),
    )


__all__ = ["UsageEvent"]
