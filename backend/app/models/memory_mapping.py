"""MemoryRecordHmsUnit — the MP↔HMS mapping table.

Every MP ``MemoryRecord`` created by the ingest pipeline is backed by exactly
one HMS ``memory_unit`` (HMS does the LLM fact extraction; MP owns the rich
domain fields HMS doesn't know about). This table records that 1:1 link so the
retrieve pipeline (Slice 4) can join HMS ``recall`` results back to their MP
rows and attach sensitivity / scope / portability / provenance.

HMS ``retain`` does NOT return created unit ids, so the ingest pipeline
discovers them post-retail via ``GET /memories/list`` filtered by the
``document_id`` correlation key (set to the event_id on retain) — see
``app.services.ingest``. This row is written once that lookup resolves.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemoryRecordHmsUnit(Base):
    """One row per MP MemoryRecord ↔ HMS memory_unit link."""

    __tablename__ = "memory_record_hms_units"

    # The MP side — 1:1 (one MP record maps to one HMS unit).
    mp_memory_id: Mapped[str] = mapped_column(
        ForeignKey("memory_records.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The HMS side.
    hms_unit_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hms_bank_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # The document_id correlation key we sent on retain (= event_id). Useful
    # for re-reconciliation / debugging.
    hms_document_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_hms_mapping_unit", "hms_unit_id", "hms_bank_id"),
    )

    def __repr__(self) -> str:
        return f"<MemoryRecordHmsUnit {self.mp_memory_id} -> {self.hms_unit_id}>"
