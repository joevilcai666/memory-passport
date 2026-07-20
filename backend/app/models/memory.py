"""MemoryRecord, MemoryPolicy, AutoWriteRule — the heart of the data model.

Mirrors ``MemoryRecord`` / ``MemoryPolicy`` / ``AutoWriteRule`` (plus the
nested ``Portability`` / ``MemorySource`` / ``RetrievalEvent`` /
``model_provenance`` shapes) in ``src/lib/types.ts``.

Composite/nested shapes are stored as JSONB — they're read whole (never queried
into), and JSONB keeps the round-trip faithful to the TypeScript interface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, jsonb
from app.models.enums import (
    PG_AUTOWRITE_ACTION,
    PG_MEMORY_SCOPE,
    PG_MEMORY_SENSITIVITY,
    PG_MEMORY_STATUS,
    PG_MEMORY_TYPE,
    AutoWriteAction,
    MemoryScope,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
)


class MemoryRecord(Base):
    """A single memory. The unit that travels (or doesn't) across devices/models."""

    __tablename__ = "memory_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_id: Mapped[str] = mapped_column(
        ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    passport_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_id: Mapped[str] = mapped_column(
        ForeignKey("relationships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )

    type: Mapped[MemoryType] = mapped_column(PG_MEMORY_TYPE, nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    scope: Mapped[MemoryScope] = mapped_column(PG_MEMORY_SCOPE, nullable=False)
    sensitivity: Mapped[MemorySensitivity] = mapped_column(PG_MEMORY_SENSITIVITY, nullable=False)
    status: Mapped[MemoryStatus] = mapped_column(PG_MEMORY_STATUS, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Composite nested objects — stored whole, faithful to types.ts.
    # {
    #   "layer": "portable" | "device_local",
    #   "cross_device": bool, "cross_role": bool,
    #   "cross_model": bool, "cross_brand_app": bool,
    # }
    portability: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)
    # {
    #   "event_id": str, "source_type": "chat"|"voice"|...,
    #   "timestamp": iso, "quote": str,
    # }
    source: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)

    valid_from: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # {
    #   "created_by_model": "gpt-4o",
    #   "retrieval_history": [{"model": str, "used": bool, "timestamp": iso}, ...],
    # }
    model_provenance: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)

    __table_args__ = (
        Index("ix_memory_records_user_type", "user_id", "type"),
        Index("ix_memory_records_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<MemoryRecord {self.id} ({self.type})>"


class MemoryPolicy(Base):
    """Per-agent policy: auto-write rules + the 4-axis portability toggles."""

    __tablename__ = "memory_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_id: Mapped[str] = mapped_column(
        ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # use_alter=True breaks the circular FK with agents.memory_policy_id so
    # SQLAlchemy can emit/drop both tables deterministically (the migration
    # handles the same cycle explicitly via create_foreign_key post-creation).
    agent_id: Mapped[str] = mapped_column(
        ForeignKey(
            "agents.id",
            ondelete="CASCADE",
            use_alter=True,
            name="fk_memory_policies_agent_id_agents",
        ),
        nullable=False,
        index=True,
    )
    # Rules live as a separate table (AutoWriteRule) for queryability, but the
    # portability toggles + retrieval config are read whole as JSONB.
    portability: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)
    retrieval: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)

    auto_write_rules: Mapped[list[AutoWriteRule]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MemoryPolicy {self.id}>"


class AutoWriteRule(Base):
    """One rule: how a memory type of a given sensitivity should be handled."""

    __tablename__ = "auto_write_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_id: Mapped[str] = mapped_column(
        ForeignKey("memory_policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_type: Mapped[MemoryType] = mapped_column(PG_MEMORY_TYPE, nullable=False)
    action: Mapped[AutoWriteAction] = mapped_column(PG_AUTOWRITE_ACTION, nullable=False)
    sensitivity: Mapped[MemorySensitivity] = mapped_column(PG_MEMORY_SENSITIVITY, nullable=False)
    # null = no expiry (daysAgo(-n) semantics from mock-data.ts)
    ttl_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    policy: Mapped[MemoryPolicy] = relationship(back_populates="auto_write_rules")

    def __repr__(self) -> str:
        return f"<AutoWriteRule {self.id} ({self.memory_type}/{self.action})>"
