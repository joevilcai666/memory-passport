"""Persistent asynchronous export jobs and short-lived download metadata."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PG_EXPORT_STATUS, ExportStatus


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ExportStatus] = mapped_column(PG_EXPORT_STATUS, nullable=False)
    download_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    download_token_expires_at: Mapped[datetime] = mapped_column(nullable=False)
    # Plaintext download token, persisted so the status endpoint can build the
    # ``download_url`` across processes/restarts (the hash alone is unrecoverable).
    # One-shot: cleared on successful download, and on job failure. See issue #13.
    download_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (Index("ix_export_jobs_tenant_created", "tenant_id", "created_at"),)


__all__ = ["ExportJob"]
