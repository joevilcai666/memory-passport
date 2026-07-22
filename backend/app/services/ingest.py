"""Ingest pipeline — turns a raw event into MP MemoryRecords backed by HMS.

Flow (PRD v2.0 §8 ``POST /v1/events/ingest``):

1. Resolve user / agent / relationship / device in-tenant (404 cross-tenant).
2. Load the agent's MemoryPolicy + AutoWriteRules; classify the event
   (memory_type, sensitivity, action).
3. S3 / block path: write an ``AuditLog(action=memory.blocked)`` and return
   ``{event_id, results:[{id:event_id, action:"BLOCKED"}]}``. **No HMS call,
   no MP row** — the safety path (PRD §7).
4. Otherwise: ``HmsClient.retain`` one item carrying ``document_id = event_id``
   as the correlation key. HMS extracts N facts via its internal LLM.
5. ``HmsClient.list_memories`` filtered to ``document_id == event_id`` to
   discover the created units (HMS retain returns no ids).
6. For each HMS unit: create one MP ``MemoryRecord`` (status = active for S0/S1,
   candidate for S2) + one :class:`MemoryRecordHmsUnit` mapping row.
7. On HMS failure: rollback, surface as 502 ``hms_retain_failed`` — no partial
   MP rows survive (issue criterion).
8. One ``AuditLog(action=memory.created)`` per created record.
9. Return ``{event_id, results:[{id, action}]}`` — matches the frontend's
   ``runTestEvent`` quickstart action shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import memory_disabled, not_found
from app.auth import TenantContext
from app.hms import HmsClient, HmsError
from app.models.enums import (
    AuditAction,
    MemoryScope,
    MemoryStatus,
    UsageOperation,
)
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.tenant import App
from app.services.audit import api_actor, write_audit
from app.services.ids import new_event_id, new_memory_id
from app.services.policy import (
    classify,
    is_blocked,
    resolve_policy,
    status_for_sensitivity,
)
from app.services.usage import write_usage


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class IngestOutcome:
    """What the ingest pipeline produced for one event."""

    event_id: str
    results: list[tuple[str, str]]  # (memory_id, action) — action ∈ ADD/UPDATE/NOOP/BLOCKED
    blocked: bool


async def ingest_event(
    db: Session,
    context: TenantContext,
    *,
    hms_client: HmsClient,
    user_id: str,
    agent_id: str,
    relationship_id: str,
    source_type: str,
    content: str,
    quote: str | None,
    event_id: str | None,
    device_id: str | None = None,
) -> IngestOutcome:
    """Run the full ingest pipeline for one event.

    The caller (the route handler) is responsible for committing on success /
    rolling back on failure; this function raises :class:`HmsError` on HMS
    failure so the handler can map it to 502.
    """
    tenant = context.tenant

    # 1. Resolve context in-tenant. Each lookup raises not_found (404) on
    #    cross-tenant references so existence isn't leaked.
    user = _get_user_in_tenant(db, tenant.id, user_id)
    if not user.memory_enabled:
        raise memory_disabled(user.id)
    agent = _get_agent_in_tenant(db, tenant.id, agent_id)
    relationship = _get_relationship_in_tenant(db, tenant.id, relationship_id)
    device = None
    if device_id is not None:
        device = _get_device_in_tenant(db, tenant.id, device_id)

    # 2. Policy + classification.
    resolved = resolve_policy(db, agent_id)
    if resolved is None:
        # _get_agent_in_tenant already raised; this is defensive.
        raise not_found("Agent", agent_id)
    classification = classify(resolved, source_type=source_type, content=content)

    event_id = event_id or new_event_id()
    quote_text = quote if quote is not None else content

    # 3. S3 / block path — no HMS call, no MP row.
    if is_blocked(classification):
        write_audit(
            db,
            tenant_id=tenant.id,
            actor=api_actor(context.api_key.id),
            action=AuditAction.MEMORY_BLOCKED,
            target=event_id,
            detail=(
                f"Blocked {classification.sensitivity.value} event "
                f"(source_type={source_type}); no HMS call, no MP record"
            ),
        )
        return IngestOutcome(
            event_id=event_id,
            results=[(event_id, "BLOCKED")],
            blocked=True,
        )

    # 4. HMS retain — one item, document_id = event_id (correlation key).
    #    The tags carry the relationship_id + scope so recall can filter.
    #    Scope is relationship_only by default (device-scoped iff a device is
    #    present and the rule/policy says so); the prototype's quickstart uses
    #    relationship_only, which we keep as the V0.1 default.
    scope = MemoryScope.DEVICE_ONLY if device is not None else MemoryScope.RELATIONSHIP_ONLY

    retain_item = {
        "content": content,
        "context": source_type,
        "timestamp": _now().isoformat(),
        "document_id": event_id,  # the correlation key for list_memories
        "tags": [f"rel:{relationship_id}", f"scope:{scope.value}"],
        "metadata": {
            "event_id": event_id,
            "sensitivity": classification.sensitivity.value,
            "memory_type": classification.memory_type.value,
        },
    }
    try:
        await hms_client.retain(bank_id=user.id, items=[retain_item], async_=False)
    except HmsError:
        # Roll back any pending flushes so no half-created rows survive.
        db.rollback()
        raise

    # 5. Reconcile via list_memories (HMS retain returns no ids). HMS's ``q``
    #    is text-ILIKE, so we list a wide window and filter on document_id.
    listing = await hms_client.list_memories(bank_id=user.id, limit=100)
    units = [u for u in listing.get("items", []) if u.get("document_id") == event_id]

    # 6. One MP record + mapping per HMS unit.
    now = _now()
    status = status_for_sensitivity(classification.sensitivity, classification.action)
    results: list[tuple[str, str]] = []

    for unit in units:
        mp_id = new_memory_id()
        record = _build_record(
            mp_id=mp_id,
            tenant_id=tenant.id,
            app_id=agent.app_id,
            user=user,
            agent_id=agent.id,
            relationship_id=relationship.id,
            device_id=device.id if device is not None else None,
            unit=unit,
            classification=classification,
            status=status,
            scope=scope,
            quote_text=quote_text,
            event_id=event_id,
            source_type=source_type,
            portability=resolved.portability,
            created_by_model=resolved.created_by_model,
            now=now,
        )
        db.add(record)
        db.flush()  # populate mp_id

        db.add(
            MemoryRecordHmsUnit(
                mp_memory_id=mp_id,
                tenant_id=tenant.id,
                hms_unit_id=str(unit.get("id")),
                hms_bank_id=user.id,
                hms_document_id=event_id,
                created_at=now,
            )
        )

        write_audit(
            db,
            tenant_id=tenant.id,
            actor=api_actor(context.api_key.id),
            action=AuditAction.MEMORY_CREATED,
            target=mp_id,
            detail=(
                f"Auto-written from {source_type} event {event_id} "
                f"({classification.memory_type.value}/{classification.sensitivity.value})"
            ),
        )
        results.append((mp_id, "ADD"))

    # If HMS produced no units (dedup, empty content), the event is a NOOP.
    if not results:
        results.append((event_id, "NOOP"))

    write_usage(db, tenant.id, user.id, UsageOperation.INGEST)

    return IngestOutcome(event_id=event_id, results=results, blocked=False)


def _build_record(
    *,
    mp_id: str,
    tenant_id: str,
    app_id: str,
    user: User,
    agent_id: str,
    relationship_id: str,
    device_id: str | None,
    unit: dict[str, Any],
    classification,
    status: MemoryStatus,
    scope: MemoryScope,
    quote_text: str,
    event_id: str,
    source_type: str,
    portability: dict[str, Any],
    created_by_model: str,
    now: datetime,
) -> MemoryRecord:
    """Build a MemoryRecord row mirroring the HMS unit + carrying MP fields."""
    return MemoryRecord(
        id=mp_id,
        tenant_id=tenant_id,
        app_id=app_id,
        passport_id=user.passport_id,
        user_id=user.id,
        relationship_id=relationship_id,
        agent_id=agent_id,
        device_id=device_id,
        type=classification.memory_type,
        content=unit.get("text") or "",
        scope=scope,
        sensitivity=classification.sensitivity,
        status=status,
        confidence=_confidence_from(unit),
        portability=dict(portability),
        source={
            "event_id": event_id,
            "source_type": source_type,
            "timestamp": now.isoformat(),
            "quote": quote_text,
        },
        valid_from=now,
        expires_at=None,
        version=1,
        supersedes=None,
        last_used_at=None,
        usage_count=0,
        model_provenance={
            "created_by_model": created_by_model,
            "retrieval_history": [],
        },
    )


def _confidence_from(unit: dict[str, Any]) -> float:
    """HMS doesn't expose a relevance score, so use a neutral default.

    A later slice can derive a confidence from HMS's consolidation state or
    proof_count; for now 0.9 mirrors the prototype's quickstart confidence.
    """
    # proof_count > 0 is a weak signal the fact was corroborated — nudge up.
    proof_count = unit.get("proof_count") or 0
    return min(1.0, 0.85 + 0.05 * min(proof_count, 3))


# ---------------------------------------------------------------------------
# In-tenant lookups (mirror Slice 2's helpers; kept here so the ingest module
# is self-contained and the cross-tenant 404 contract is in one place).
# ---------------------------------------------------------------------------


def _get_user_in_tenant(db: Session, tenant_id: str, user_id: str) -> User:
    row = db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    if row is None:
        raise not_found("User", user_id)
    return row


def _get_agent_in_tenant(db: Session, tenant_id: str, agent_id: str) -> Agent:
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
