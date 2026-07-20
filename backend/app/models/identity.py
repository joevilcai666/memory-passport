"""User, Agent, Device, Relationship — the identity graph.

Mirrors ``User`` / ``Agent`` / ``Device`` / ``Relationship`` in ``src/lib/types.ts``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, text_array
from app.models.enums import (
    PG_AGE_GROUP,
    PG_AGENT_TYPE,
    PG_DEVICE_STATUS,
    PG_PASSPORT_STATUS,
    PG_RELATIONSHIP_TYPE,
    AgeGroup,
    AgentType,
    DeviceStatus,
    MemoryType,
    PassportStatus,
    RelationshipType,
)


class User(Base):
    """An end user. passport_id is the memory-ownership anchor."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    passport_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    passport_status: Mapped[PassportStatus] = mapped_column(
        PG_PASSPORT_STATUS, nullable=False, default=PassportStatus.ACTIVE
    )
    passport_deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    age_group: Mapped[AgeGroup] = mapped_column(
        PG_AGE_GROUP, nullable=False, default=AgeGroup.UNKNOWN
    )
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(32), nullable=False)

    # Also the bank_id used by HMS — `bank_id == user_id` per the acceptance test.
    @property
    def bank_id(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"<User {self.id}>"


class Agent(Base):
    """An AI character/companion/robot under an app."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_id: Mapped[str] = mapped_column(
        ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AgentType] = mapped_column(PG_AGENT_TYPE, nullable=False)
    persona_version: Mapped[str] = mapped_column(String(64), nullable=False)
    memory_policy_id: Mapped[str] = mapped_column(
        ForeignKey("memory_policies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # PG array of memory_type enum — the types this agent may read.
    allowed_memory_types: Mapped[list[str]] = mapped_column(
        text_array(), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="🤖")

    def __repr__(self) -> str:
        return f"<Agent {self.id}>"


class Device(Base):
    """A hardware/software device. The migration wedge centres on these."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    generation: Mapped[str] = mapped_column(String(32), nullable=False)
    serial_number_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[DeviceStatus] = mapped_column(PG_DEVICE_STATUS, nullable=False)
    bound_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<Device {self.id} ({self.generation})>"


class Relationship(Base):
    """A long-term relationship between a user and an agent (+ optional device).

    Relationship memory is scoped per row — different AI personas don't share.
    """

    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        PG_RELATIONSHIP_TYPE, nullable=False
    )
    memory_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        return f"<Relationship {self.id}>"


# Re-export the enum so callers importing from this module don't need to know
# the MemoryType enum lives in enums.py.
__all__ = ["User", "Agent", "Device", "Relationship", "MemoryType"]
