"""Retrieve pipeline — the read-side counterpart to Slice 3's ingest.

Flow (PRD v2.0 §8 ``POST /v1/memories/retrieve``):

1. Resolve caller context in-tenant (404 cross-tenant).
2. Load policy (``retrieval.max_memories_per_response`` + the
   ``include_sensitive_in_prompt`` masking toggle).
3. ``HmsClient.recall`` against the user's bank (``bank_id == user.id``).
4. Join HMS results -> MP MemoryRecords via :class:`MemoryRecordHmsUnit`
   (hms_unit_id == the recall result's id). Orphans (HMS unit with no MP row)
   are skipped — they pre-date the mapping or came from outside MP.
5. Apply the scope-filter matrix (``app.services.scopes.is_readable``) +
   cap at ``max_memories_per_response``.
6. Append a ``RetrievalEvent{model, used:true, timestamp}`` to EACH returned
   record's ``model_provenance.retrieval_history`` (the cross-model parity
   moat — PRD §9.4). Increment ``usage_count``, set ``last_used_at``.
7. Persist a :class:`RetrievalTrace` row (query, raw HMS, projected, events).
8. ``AuditLog(action=retrieval.performed)``.
9. Return ``{trace_id, results: [projected records]}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth import TenantContext
from app.hms import HmsClient, HmsError
from app.models.enums import AuditAction, MemoryStatus, PassportStatus, UsageOperation
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.retrieval_trace import RetrievalTrace
from app.services.audit import api_actor, write_audit
from app.services.ids import new_trace_id
from app.services.policy import resolve_policy
from app.services.scopes import is_readable, project_record
from app.services.usage import write_usage


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class RetrieveOutcome:
    """What the retrieve pipeline produced for one call."""

    trace_id: str
    projected: list[dict[str, Any]]
    hms_results: dict[str, Any]
    retrieval_events: dict[str, Any]
    caller: dict[str, Any]


async def retrieve_memories(
    db: Session,
    context: TenantContext,
    *,
    hms_client: HmsClient,
    user_id: str,
    agent_id: str,
    relationship_id: str,
    query: str,
    model: str,
    device_id: str | None = None,
) -> RetrieveOutcome:
    """Run the full retrieve pipeline for one call.

    Raises :class:`HmsError` on HMS failure so the route handler can map it to
    a 502. Does NOT commit — the route handler commits on success.
    """
    tenant = context.tenant

    # 1. Resolve caller context in-tenant.
    user = _get_user_in_tenant(db, tenant.id, user_id)
    if user.passport_status == PassportStatus.DELETED:
        return _deleted_passport_outcome(
            db,
            context,
            user_id=user_id,
            agent_id=agent_id,
            relationship_id=relationship_id,
            device_id=device_id,
            query=query,
            model=model,
        )
    _get_agent_in_tenant(db, tenant.id, agent_id)
    _get_relationship_in_tenant(db, tenant.id, relationship_id)
    device_status: str | None = None
    if device_id is not None:
        device = _get_device_in_tenant(db, tenant.id, device_id)
        device_status = (
            device.status.value if hasattr(device.status, "value") else str(device.status)
        )

    # 2. Policy — max_per_response + include_sensitive_in_prompt.
    resolved = resolve_policy(db, agent_id)
    if resolved is None:
        raise not_found("Agent", agent_id)
    max_per_response = int(resolved.retrieval.get("max_memories_per_response", 8))
    include_sensitive = bool(resolved.retrieval.get("include_sensitive_in_prompt", False))

    # 3. HMS recall against the user's bank. tags_match="any" so we get the
    #    broadest candidate set; MP filters by scope client-side (HMS tags only
    #    carry a coarse relationship/scope marker, not the full matrix).
    try:
        hms_response = await hms_client.recall(
            bank_id=user.id,
            query=query,
            tags=[f"rel:{relationship_id}"],
            tags_match="any",
        )
    except HmsError:
        db.rollback()
        raise

    hms_results_list: list[dict[str, Any]] = hms_response.get("results", [])

    # 4. Join HMS results -> MP records via the mapping table.
    hms_unit_ids = [r.get("id") for r in hms_results_list if r.get("id")]
    if not hms_unit_ids:
        candidate_records: list[MemoryRecord] = []
    else:
        rows = db.execute(
            select(MemoryRecord, MemoryRecordHmsUnit.hms_unit_id)
            .join(
                MemoryRecordHmsUnit,
                MemoryRecordHmsUnit.mp_memory_id == MemoryRecord.id,
            )
            .where(
                MemoryRecordHmsUnit.hms_unit_id.in_(hms_unit_ids),
                MemoryRecord.tenant_id == tenant.id,
                MemoryRecord.status == MemoryStatus.ACTIVE,
            )
        ).all()
        # Preserve HMS's rank order (the recall result order).
        rank = {r.get("id"): i for i, r in enumerate(hms_results_list)}
        candidate_records = [
            rec for rec, _unit_id in sorted(rows, key=lambda r: rank.get(r[1], 1 << 30))
        ]

    # 5. Scope filter (PRD §9.1 matrix) + cap.
    readable = [
        rec
        for rec in candidate_records
        if is_readable(
            rec,
            caller_agent_id=agent_id,
            caller_relationship_id=relationship_id,
            caller_device_id=device_id,
            caller_device_status=device_status,
        )
    ][:max_per_response]

    # 6. Append a RetrievalEvent to each returned record's retrieval_history
    #    and bump usage_count/last_used_at (the cross-model parity moat).
    now = _now()
    retrieval_events_by_id: dict[str, dict[str, Any]] = {}
    for rec in readable:
        event = {"model": model, "used": True, "timestamp": now.isoformat()}
        history = list(rec.model_provenance.get("retrieval_history", []))
        history.append(event)
        # JSONB columns are mutated in place — SQLAlchemy needs the attribute
        # reassigned so the change is detected (MutableDict would do this
        # automatically; we keep the models free of mutability tracking).
        rec.model_provenance = {
            **rec.model_provenance,
            "retrieval_history": history,
        }
        rec.usage_count = (rec.usage_count or 0) + 1
        rec.last_used_at = now
        retrieval_events_by_id[rec.id] = event
    db.flush()

    # 7. Persist the retrieval trace (the full event chain for debugging).
    projected = [
        project_record(rec, include_sensitive=include_sensitive) for rec in readable
    ]
    caller_ctx = {
        "user_id": user_id,
        "agent_id": agent_id,
        "relationship_id": relationship_id,
        "device_id": device_id,
        "device_status": device_status,
        "model": model,
    }
    trace_id = new_trace_id()
    db.add(
        RetrievalTrace(
            id=trace_id,
            tenant_id=tenant.id,
            query=query,
            caller=caller_ctx,
            hms_results={"results": hms_results_list},
            projected={"results": projected},
            retrieval_events={"events": retrieval_events_by_id},
            created_at=now,
        )
    )

    # 8. AuditLog.
    write_audit(
        db,
        tenant_id=tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.RETRIEVAL_PERFORMED,
        target=trace_id,
        detail=(
            f"Retrieved {len(readable)} memories for user {user_id} "
            f"(query={query!r}, model={model})"
        ),
    )
    write_usage(db, tenant.id, user.id, UsageOperation.RETRIEVE)

    return RetrieveOutcome(
        trace_id=trace_id,
        projected=projected,
        hms_results={"results": hms_results_list},
        retrieval_events={"events": retrieval_events_by_id},
        caller=caller_ctx,
    )


def _deleted_passport_outcome(
    db: Session,
    context: TenantContext,
    *,
    user_id: str,
    agent_id: str,
    relationship_id: str,
    device_id: str | None,
    query: str,
    model: str,
) -> RetrieveOutcome:
    """Trace an empty result without contacting HMS for a deleted passport."""
    now = _now()
    trace_id = new_trace_id()
    caller = {
        "user_id": user_id,
        "agent_id": agent_id,
        "relationship_id": relationship_id,
        "device_id": device_id,
        "device_status": None,
        "model": model,
        "passport_status": PassportStatus.DELETED.value,
    }
    empty_results = {"results": []}
    db.add(
        RetrievalTrace(
            id=trace_id,
            tenant_id=context.tenant.id,
            query=query,
            caller=caller,
            hms_results=empty_results,
            projected=empty_results,
            retrieval_events={"events": {}},
            created_at=now,
        )
    )
    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.RETRIEVAL_PERFORMED,
        target=trace_id,
        detail=f"Skipped HMS recall for deleted passport user {user_id}",
    )
    write_usage(db, context.tenant.id, user_id, UsageOperation.RETRIEVE, now)
    return RetrieveOutcome(
        trace_id=trace_id,
        projected=[],
        hms_results=empty_results,
        retrieval_events={"events": {}},
        caller=caller,
    )


# ---------------------------------------------------------------------------
# Debug trace lookup (GET /v1/debug/traces/{trace_id})
# ---------------------------------------------------------------------------


def get_trace(db: Session, tenant_id: str, trace_id: str) -> RetrievalTrace:
    """Return the trace iff it belongs to ``tenant_id``; else 404."""
    row = db.scalar(
        select(RetrievalTrace).where(
            RetrievalTrace.id == trace_id, RetrievalTrace.tenant_id == tenant_id
        )
    )
    if row is None:
        raise not_found("Trace", trace_id)
    return row


# ---------------------------------------------------------------------------
# In-tenant lookups (mirror ingest.py's helpers).
# ---------------------------------------------------------------------------


def _get_user_in_tenant(db: Session, tenant_id: str, user_id: str) -> User:
    row = db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    if row is None:
        raise not_found("User", user_id)
    return row


def _get_agent_in_tenant(db: Session, tenant_id: str, agent_id: str) -> Agent:
    from app.models.tenant import App

    row = db.scalar(
        select(Agent)
        .join(App, App.id == Agent.app_id)
        .where(Agent.id == agent_id, App.tenant_id == tenant_id)
    )
    if row is None:
        raise not_found("Agent", agent_id)
    return row


def _get_relationship_in_tenant(db: Session, tenant_id: str, relationship_id: str) -> Relationship:
    row = db.scalar(
        select(Relationship).where(
            Relationship.id == relationship_id, Relationship.tenant_id == tenant_id
        )
    )
    if row is None:
        raise not_found("Relationship", relationship_id)
    return row


def _get_device_in_tenant(db: Session, tenant_id: str, device_id: str) -> Device:
    row = db.scalar(
        select(Device).where(Device.id == device_id, Device.tenant_id == tenant_id)
    )
    if row is None:
        raise not_found("Device", device_id)
    return row
