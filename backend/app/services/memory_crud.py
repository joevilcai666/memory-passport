"""Tenant-scoped memory list, versioning, state transitions, and tombstones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth import TenantContext
from app.hms import HmsClient, HmsError
from app.models.enums import (
    AuditAction,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    UsageOperation,
)
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.services.audit import api_actor, write_audit
from app.services.ids import new_event_id, new_memory_id
from app.services.usage import write_usage

LEGAL: dict[MemoryStatus, set[MemoryStatus]] = {
    MemoryStatus.CANDIDATE: {MemoryStatus.ACTIVE, MemoryStatus.NEEDS_REVIEW},
    MemoryStatus.ACTIVE: {
        MemoryStatus.ARCHIVED,
        MemoryStatus.NEEDS_REVIEW,
        MemoryStatus.DELETED,
        MemoryStatus.EXPIRED,
        MemoryStatus.FLAGGED_WRONG,
    },
}


@dataclass(frozen=True)
class MemoryFilters:
    user_id: str | None = None
    type: MemoryType | None = None
    status: MemoryStatus | None = None
    scope: MemoryScope | None = None
    relationship_id: str | None = None
    agent_id: str | None = None
    device_id: str | None = None


@dataclass(frozen=True)
class MemoryPage:
    items: list[MemoryRecord]
    total: int
    page: int
    page_size: int
    pages: int


def _now() -> datetime:
    return datetime.now(tz=UTC)


def list_memories(
    db: Session,
    tenant_id: str,
    filters: MemoryFilters,
    page: int,
    page_size: int,
    include_deleted: bool,
) -> MemoryPage:
    """Return a stable, tenant-scoped page and its metadata."""
    conditions = [MemoryRecord.tenant_id == tenant_id]
    if not include_deleted:
        conditions.append(MemoryRecord.status != MemoryStatus.DELETED)
    for column, value in (
        (MemoryRecord.user_id, filters.user_id),
        (MemoryRecord.type, filters.type),
        (MemoryRecord.status, filters.status),
        (MemoryRecord.scope, filters.scope),
        (MemoryRecord.relationship_id, filters.relationship_id),
        (MemoryRecord.agent_id, filters.agent_id),
        (MemoryRecord.device_id, filters.device_id),
    ):
        if value is not None:
            conditions.append(column == value)

    total = db.scalar(select(func.count()).select_from(MemoryRecord).where(*conditions)) or 0
    items = list(
        db.scalars(
            select(MemoryRecord)
            .where(*conditions)
            .order_by(MemoryRecord.valid_from.desc(), MemoryRecord.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return MemoryPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


async def edit_memory(
    db: Session,
    context: TenantContext,
    hms_client: HmsClient,
    memory_id: str,
    content: str,
) -> MemoryRecord:
    """Archive an active row and retain a fresh active version in HMS."""
    old = _get_memory(db, context.tenant.id, memory_id)
    if old.status != MemoryStatus.ACTIVE:
        raise _illegal_transition(old.status, MemoryStatus.ACTIVE, action="edit")
    old_mapping = db.get(MemoryRecordHmsUnit, old.id)
    if old_mapping is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "missing_hms_mapping",
                "message": f"memory {old.id} has no HMS mapping",
            },
        )

    document_id = new_event_id()
    tags = _tags(old, MemoryStatus.ACTIVE)
    try:
        await hms_client.retain(
            bank_id=old.user_id,
            items=[
                {
                    "content": content,
                    "context": old.source.get("source_type", "chat"),
                    "timestamp": _now().isoformat(),
                    "document_id": document_id,
                    "tags": tags,
                    "metadata": {
                        "supersedes": old.id,
                        "memory_type": old.type.value,
                        "sensitivity": old.sensitivity.value,
                    },
                }
            ],
            async_=False,
        )
        listing = await hms_client.list_memories(bank_id=old.user_id, limit=100)
        units = [
            item
            for item in listing.get("items", [])
            if item.get("document_id") == document_id
        ]
        if not units:
            raise HmsError(f"HMS retained no units for edited memory {old.id}")
        unit = next((item for item in units if item.get("text") == content), units[0])

        if not _has_other_live_document_mapping(db, old_mapping):
            await hms_client.delete_document(old_mapping.hms_bank_id, old_mapping.hms_document_id)
    except HmsError:
        db.rollback()
        raise

    now = _now()
    edited = MemoryRecord(
        id=new_memory_id(),
        tenant_id=old.tenant_id,
        app_id=old.app_id,
        passport_id=old.passport_id,
        user_id=old.user_id,
        relationship_id=old.relationship_id,
        agent_id=old.agent_id,
        device_id=old.device_id,
        type=old.type,
        content=content,
        scope=old.scope,
        sensitivity=old.sensitivity,
        status=MemoryStatus.ACTIVE,
        confidence=old.confidence,
        portability=dict(old.portability),
        source=dict(old.source),
        valid_from=now,
        expires_at=old.expires_at,
        version=old.version + 1,
        supersedes=old.id,
        last_used_at=None,
        usage_count=0,
        model_provenance={
            "created_by_model": old.model_provenance.get("created_by_model", "unknown"),
            "retrieval_history": [],
        },
    )
    old.status = MemoryStatus.ARCHIVED
    db.delete(old_mapping)
    db.add(edited)
    db.flush()
    db.add(
        MemoryRecordHmsUnit(
            mp_memory_id=edited.id,
            tenant_id=edited.tenant_id,
            hms_unit_id=str(unit["id"]),
            hms_bank_id=edited.user_id,
            hms_document_id=document_id,
            created_at=now,
        )
    )
    write_audit(
        db,
        tenant_id=edited.tenant_id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.MEMORY_EDITED,
        target=edited.id,
        detail=f"Edited memory {old.id}; created version {edited.version}",
    )
    write_usage(db, edited.tenant_id, edited.user_id, UsageOperation.UPDATE)
    return edited


async def transition_memory(
    db: Session,
    context: TenantContext,
    hms_client: HmsClient,
    memory_id: str,
    target_status: MemoryStatus,
) -> MemoryRecord:
    """Apply one legal state transition and mirror it into HMS tags."""
    record = _get_memory(db, context.tenant.id, memory_id)
    if target_status not in LEGAL.get(record.status, set()):
        raise _illegal_transition(record.status, target_status)
    if target_status == MemoryStatus.DELETED:
        return await delete_memory(db, context, hms_client, memory_id)

    mapping = db.get(MemoryRecordHmsUnit, record.id)
    if mapping is not None:
        try:
            await hms_client.update_document_tags(
                mapping.hms_bank_id,
                mapping.hms_document_id,
                _tags(record, target_status),
            )
        except HmsError:
            db.rollback()
            raise
    previous = record.status
    record.status = target_status
    write_audit(
        db,
        tenant_id=record.tenant_id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.MEMORY_EDITED,
        target=record.id,
        detail=f"Changed memory status {previous.value} -> {target_status.value}",
    )
    write_usage(db, record.tenant_id, record.user_id, UsageOperation.UPDATE)
    return record


async def delete_memory(
    db: Session,
    context: TenantContext,
    hms_client: HmsClient,
    memory_id: str,
) -> MemoryRecord:
    """Tombstone a live memory and suppress its HMS recall mapping."""
    record = _get_memory(db, context.tenant.id, memory_id)
    if record.status != MemoryStatus.ACTIVE:
        raise _illegal_transition(record.status, MemoryStatus.DELETED)
    mapping = db.get(MemoryRecordHmsUnit, record.id)
    if mapping is not None and not _has_other_live_document_mapping(db, mapping):
        try:
            await hms_client.delete_document(mapping.hms_bank_id, mapping.hms_document_id)
        except HmsError:
            db.rollback()
            raise
    record.status = MemoryStatus.DELETED
    if mapping is not None:
        db.delete(mapping)
    write_audit(
        db,
        tenant_id=record.tenant_id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.MEMORY_DELETED,
        target=record.id,
        detail=f"Tombstoned memory {record.id} and suppressed its HMS mapping",
    )
    write_usage(db, record.tenant_id, record.user_id, UsageOperation.DELETE)
    return record


def _get_memory(db: Session, tenant_id: str, memory_id: str) -> MemoryRecord:
    record = db.scalar(
        select(MemoryRecord).where(
            MemoryRecord.id == memory_id,
            MemoryRecord.tenant_id == tenant_id,
        )
    )
    if record is None:
        raise not_found("Memory", memory_id)
    return record


def _has_other_live_document_mapping(
    db: Session, mapping: MemoryRecordHmsUnit
) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(MemoryRecordHmsUnit)
            .join(MemoryRecord, MemoryRecord.id == MemoryRecordHmsUnit.mp_memory_id)
            .where(
                MemoryRecordHmsUnit.mp_memory_id != mapping.mp_memory_id,
                MemoryRecordHmsUnit.hms_bank_id == mapping.hms_bank_id,
                MemoryRecordHmsUnit.hms_document_id == mapping.hms_document_id,
                MemoryRecord.status.in_(
                    [
                        MemoryStatus.ACTIVE,
                        MemoryStatus.CANDIDATE,
                        MemoryStatus.NEEDS_REVIEW,
                    ]
                ),
            )
        )
        or 0
    ) > 0


def _tags(record: MemoryRecord, memory_status: MemoryStatus) -> list[str]:
    return [
        f"rel:{record.relationship_id}",
        f"scope:{record.scope.value}",
        f"status:{memory_status.value}",
    ]


def _illegal_transition(
    current: MemoryStatus,
    target: MemoryStatus,
    *,
    action: str = "transition",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "illegal_memory_transition",
            "message": f"cannot {action} memory from '{current.value}' to '{target.value}'",
            "current": current.value,
            "target": target.value,
        },
    )


__all__ = [
    "LEGAL",
    "MemoryFilters",
    "MemoryPage",
    "delete_memory",
    "edit_memory",
    "list_memories",
    "transition_memory",
]
