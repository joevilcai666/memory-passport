"""RetrievalTrace — the persisted retrieval event chain for debugging.

Every ``POST /v1/memories/retrieve`` (Slice 4) writes one row here keyed by a
generated ``trace_id`` (returned in the response). ``GET /v1/debug/traces/{id}``
returns the saved chain so an operator can see exactly which HMS memories were
recalled, which MP records were projected, and which models touched them — the
"why did the model see this?" debug anchor (PRD §8, P0).

TTL: rows are retained for ≥7 days (PRD §8). Enforcement is by row age — a
cleanup job (later slice) deletes rows older than the configured TTL; until
then the rows simply accumulate, which is fine for V0.1's single-node shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, jsonb


class RetrievalTrace(Base):
    """One retrieval's full event chain, keyed by trace_id."""

    __tablename__ = "retrieval_traces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    # The caller context that drove the retrieve (user/agent/device/relationship
    # ids + the model id). Stored whole — read by the debug endpoint, never
    # queried into.
    caller: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)
    # The raw HMS recall response (results array + any trace fields HMS sent).
    hms_results: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)
    # The final projected MP records actually returned to the caller (after
    # scope filtering + sensitivity masking + cap).
    projected: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)
    # Per-model RetrievalEvent rows appended to each returned memory's
    # model_provenance.retrieval_history — the cross-model parity data.
    retrieval_events: Mapped[dict[str, Any]] = mapped_column(jsonb(), nullable=False)
    # Latest operator feedback for one projected memory in this trace.
    feedback: Mapped[dict[str, Any] | None] = mapped_column(jsonb(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        Index("ix_retrieval_traces_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RetrievalTrace {self.id}>"
