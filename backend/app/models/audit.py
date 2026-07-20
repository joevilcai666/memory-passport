"""AuditLog — every sensitive action (view/delete/migrate/export) is recorded.

Mirrors ``AuditLog`` in ``src/lib/types.ts``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PG_AUDIT_ACTION, AuditAction


class AuditLog(Base):
    """One audit row per sensitive operation. The B-side audit trail."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[AuditAction] = mapped_column(PG_AUDIT_ACTION, nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_audit_logs_tenant_action", "tenant_id", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} ({self.action})>"
