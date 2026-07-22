"""Tenant-scoped console members and one-time invitations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PG_TEAM_ROLE, TeamRole


class TeamMember(Base):
    """A named console member displayed in the V0.1 tenant settings surface."""

    __tablename__ = "team_members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[TeamRole] = mapped_column(PG_TEAM_ROLE, nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(32), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(nullable=False)
    last_active: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_team_members_tenant_email"),
        Index("ix_team_members_tenant_role", "tenant_id", "role"),
    )


class TeamInvite(Base):
    """A time-limited, single-use invitation; only its token hash is stored."""

    __tablename__ = "team_invites"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[TeamRole] = mapped_column(PG_TEAM_ROLE, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    accepted_member_id: Mapped[str | None] = mapped_column(
        ForeignKey("team_members.id", ondelete="SET NULL"), nullable=True, unique=True
    )

    __table_args__ = (Index("ix_team_invites_tenant_email", "tenant_id", "email"),)


__all__ = ["TeamInvite", "TeamMember"]
