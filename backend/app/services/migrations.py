"""Luna migration preview buckets and reversible execution state machine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth import TenantContext
from app.models.enums import (
    AuditAction,
    DeviceStatus,
    MemoryStatus,
    MigrationStatus,
    OldDeviceAccess,
    WebhookEventType,
)
from app.models.identity import Device, Relationship, User
from app.models.memory import MemoryRecord
from app.models.migration import Migration
from app.schemas.migrations import (
    MigrationBucket,
    MigrationCounts,
    MigrationExecuteRequest,
    MigrationPreviewRequest,
    MigrationPreviewResponse,
)
from app.services.audit import api_actor, write_audit
from app.services.ids import new_migration_id
from app.services.webhook import record_event_for_tenant


@dataclass(frozen=True)
class PreviewOutcome:
    response: MigrationPreviewResponse
    created: bool


def _now() -> datetime:
    return datetime.now(tz=UTC)


def preview_migration(
    db: Session,
    context: TenantContext,
    request: MigrationPreviewRequest,
) -> PreviewOutcome:
    """Return the fixed three buckets and create the idempotent preview row."""
    _validate_preview_context(db, context.tenant.id, request)
    existing = db.scalar(
        select(Migration).where(
            Migration.tenant_id == context.tenant.id,
            Migration.user_id == request.user_id,
            Migration.source_relationship_id == request.source_relationship_id,
            Migration.target_relationship_id == request.target_relationship_id,
            Migration.source_device_id == request.source_device_id,
            Migration.target_device_id == request.target_device_id,
        )
    )
    created = existing is None
    migration = existing
    if migration is None:
        migration = Migration(
            id=new_migration_id(),
            tenant_id=context.tenant.id,
            user_id=request.user_id,
            source_relationship_id=request.source_relationship_id,
            target_relationship_id=request.target_relationship_id,
            source_device_id=request.source_device_id,
            target_device_id=request.target_device_id,
            status=MigrationStatus.PREVIEW,
            selected_memory_ids=[],
            skipped_memory_ids=[],
            failed_memory_ids=[],
            rollback_snapshot={},
            old_device_access=OldDeviceAccess.KEEP,
            audit_log_id=None,
            created_at=_now(),
            completed_at=None,
            rolled_back_at=None,
        )
        db.add(migration)
        db.flush()

    recommended, needs_review, not_moved = _bucket_ids(
        db, context.tenant.id, request.source_relationship_id
    )
    return PreviewOutcome(
        response=MigrationPreviewResponse(
            migration_id=migration.id,
            status=migration.status,
            recommended=MigrationBucket(memory_ids=recommended),
            needs_review=MigrationBucket(memory_ids=needs_review),
            not_moved=MigrationBucket(memory_ids=not_moved),
            counts=MigrationCounts(
                recommended=len(recommended),
                needs_review=len(needs_review),
                not_moved=len(not_moved),
            ),
        ),
        created=created,
    )


def execute_migration(
    db: Session,
    context: TenantContext,
    request: MigrationExecuteRequest,
) -> Migration:
    migration = get_migration(db, context.tenant.id, request.migration_id)
    if migration.status not in {MigrationStatus.PREVIEW, MigrationStatus.FAILED}:
        raise _migration_conflict(migration.status, "execute")

    source = _get_device(db, context.tenant.id, migration.source_device_id)
    target = _get_device(db, context.tenant.id, migration.target_device_id)
    requested = list(dict.fromkeys(request.selected_memory_ids))
    rows = list(
        db.scalars(
            select(MemoryRecord).where(
                MemoryRecord.id.in_(requested),
                MemoryRecord.tenant_id == context.tenant.id,
                MemoryRecord.user_id == migration.user_id,
                MemoryRecord.relationship_id == migration.source_relationship_id,
                MemoryRecord.status.notin_([MemoryStatus.DELETED, MemoryStatus.ARCHIVED]),
            )
        )
    )
    eligible = {
        record.id: record
        for record in rows
        if record.portability.get("layer") == "portable"
    }
    successful_ids = [memory_id for memory_id in requested if memory_id in eligible]
    failed_ids = [memory_id for memory_id in requested if memory_id not in eligible]

    migration.status = MigrationStatus.RUNNING
    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.MIGRATION_STARTED,
        target=migration.id,
        detail=f"Started migration of {len(requested)} selected memories",
    )
    migration.rollback_snapshot = {
        "memory_device_ids": {
            memory_id: eligible[memory_id].device_id for memory_id in successful_ids
        },
        "source_device_status": source.status.value,
        "source_bound_user_id": source.bound_user_id,
        "target_device_status": target.status.value,
        "target_bound_user_id": target.bound_user_id,
    }

    for memory_id in successful_ids:
        eligible[memory_id].device_id = migration.target_device_id
    if successful_ids:
        target.status = DeviceStatus.BOUND
        target.bound_user_id = migration.user_id
        if request.old_device_access == OldDeviceAccess.REMOVE:
            source.status = DeviceStatus.UNBOUND
            source.bound_user_id = None

    buckets = _bucket_ids(db, context.tenant.id, migration.source_relationship_id)
    all_live_ids = set(sum(buckets, []))
    migration.selected_memory_ids = successful_ids
    migration.skipped_memory_ids = sorted(all_live_ids - set(successful_ids))
    migration.failed_memory_ids = failed_ids
    migration.old_device_access = request.old_device_access
    migration.rolled_back_at = None

    if not successful_ids:
        migration.status = MigrationStatus.FAILED
        migration.completed_at = None
        migration.audit_log_id = None
        record_event_for_tenant(
            db,
            tenant_id=context.tenant.id,
            event_type=WebhookEventType.MIGRATION_FAILED,
            payload={
                "migration_id": migration.id,
                "failed_count": len(failed_ids),
            },
        )
    else:
        migration.status = (
            MigrationStatus.COMPLETED_WITH_WARNINGS
            if failed_ids
            else MigrationStatus.COMPLETED
        )
        migration.completed_at = _now()
        audit = write_audit(
            db,
            tenant_id=context.tenant.id,
            actor=api_actor(context.api_key.id),
            action=AuditAction.MIGRATION_COMPLETED,
            target=migration.id,
            detail=(
                f"Migrated {len(successful_ids)} memories; "
                f"{len(failed_ids)} failed"
            ),
        )
        migration.audit_log_id = audit.id
        record_event_for_tenant(
            db,
            tenant_id=context.tenant.id,
            event_type=WebhookEventType.MIGRATION_COMPLETED,
            payload={
                "migration_id": migration.id,
                "migrated_count": len(successful_ids),
                "failed_count": len(failed_ids),
                "status": migration.status.value,
            },
        )
    db.flush()
    return migration


def get_migration(db: Session, tenant_id: str, migration_id: str) -> Migration:
    migration = db.scalar(
        select(Migration).where(
            Migration.id == migration_id,
            Migration.tenant_id == tenant_id,
        )
    )
    if migration is None:
        raise not_found("Migration", migration_id)
    return migration


def rollback_migration(
    db: Session,
    context: TenantContext,
    migration_id: str,
) -> Migration:
    migration = get_migration(db, context.tenant.id, migration_id)
    if migration.status not in {
        MigrationStatus.COMPLETED,
        MigrationStatus.COMPLETED_WITH_WARNINGS,
    }:
        raise _migration_conflict(migration.status, "rollback")
    snapshot = migration.rollback_snapshot or {}
    memory_device_ids = snapshot.get("memory_device_ids", {})
    for record in db.scalars(
        select(MemoryRecord).where(
            MemoryRecord.id.in_(memory_device_ids),
            MemoryRecord.tenant_id == context.tenant.id,
        )
    ):
        record.device_id = memory_device_ids[record.id]

    source = _get_device(db, context.tenant.id, migration.source_device_id)
    target = _get_device(db, context.tenant.id, migration.target_device_id)
    source.status = DeviceStatus(snapshot["source_device_status"])
    source.bound_user_id = snapshot.get("source_bound_user_id")
    target.status = DeviceStatus(snapshot["target_device_status"])
    target.bound_user_id = snapshot.get("target_bound_user_id")
    migration.status = MigrationStatus.ROLLED_BACK
    migration.rolled_back_at = _now()
    audit = write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.MIGRATION_ROLLED_BACK,
        target=migration.id,
        detail=f"Rolled back migration {migration.id}",
    )
    migration.audit_log_id = audit.id
    db.flush()
    return migration


def _bucket_ids(db: Session, tenant_id: str, relationship_id: str):
    records = list(
        db.scalars(
            select(MemoryRecord)
            .where(
                MemoryRecord.tenant_id == tenant_id,
                MemoryRecord.relationship_id == relationship_id,
                MemoryRecord.status.notin_([MemoryStatus.DELETED, MemoryStatus.ARCHIVED]),
            )
            .order_by(MemoryRecord.id)
        )
    )
    portable = [record for record in records if record.portability.get("layer") == "portable"]
    recommended = [record.id for record in portable if record.confidence >= 0.7]
    needs_review = [record.id for record in portable if record.confidence < 0.7]
    not_moved = [
        record.id for record in records if record.portability.get("layer") == "device_local"
    ]
    return recommended, needs_review, not_moved


def _validate_preview_context(
    db: Session, tenant_id: str, request: MigrationPreviewRequest
) -> None:
    user = db.scalar(
        select(User).where(User.id == request.user_id, User.tenant_id == tenant_id)
    )
    relationship = db.scalar(
        select(Relationship).where(
            Relationship.id == request.source_relationship_id,
            Relationship.tenant_id == tenant_id,
            Relationship.user_id == request.user_id,
        )
    )
    source = db.scalar(
        select(Device).where(
            Device.id == request.source_device_id, Device.tenant_id == tenant_id
        )
    )
    target = db.scalar(
        select(Device).where(
            Device.id == request.target_device_id, Device.tenant_id == tenant_id
        )
    )
    if user is None or relationship is None or source is None or target is None:
        raise not_found("Migration context")


def _get_device(db: Session, tenant_id: str, device_id: str) -> Device:
    device = db.scalar(
        select(Device).where(Device.id == device_id, Device.tenant_id == tenant_id)
    )
    if device is None:
        raise not_found("Device", device_id)
    return device


def _migration_conflict(current: MigrationStatus, action: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "illegal_migration_transition",
            "message": f"cannot {action} migration in state '{current.value}'",
            "current": current.value,
            "action": action,
        },
    )


__all__ = [
    "PreviewOutcome",
    "execute_migration",
    "get_migration",
    "preview_migration",
    "rollback_migration",
]
