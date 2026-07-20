"""Tenant-scoped, side-effect-free audit and usage aggregate queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction, MemoryStatus, UsageOperation
from app.models.memory import MemoryRecord
from app.models.usage import UsageEvent
from app.schemas.aggregates import MemoryOpsResponse, UsageResponse


@dataclass(frozen=True)
class AuditFilters:
    actor: str | None = None
    action: AuditAction | None = None
    target: str | None = None
    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True)
class AuditPage:
    items: list[AuditLog]
    total: int
    page: int
    page_size: int
    pages: int


def query_audit_logs(
    db: Session,
    tenant_id: str,
    filters: AuditFilters,
    page: int,
    page_size: int,
) -> AuditPage:
    since, until = _validated_bounds(filters.since, filters.until, defaults=False)
    conditions = [AuditLog.tenant_id == tenant_id]
    for column, value in (
        (AuditLog.actor, filters.actor),
        (AuditLog.action, filters.action),
        (AuditLog.target, filters.target),
    ):
        if value is not None:
            conditions.append(column == value)
    if since is not None:
        conditions.append(AuditLog.timestamp >= since)
    if until is not None:
        conditions.append(AuditLog.timestamp <= until)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*conditions)) or 0
    items = list(
        db.scalars(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return AuditPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def query_usage(
    db: Session,
    tenant_id: str,
    since: datetime | None,
    until: datetime | None,
) -> UsageResponse:
    start, end = _validated_bounds(since, until, defaults=True)
    assert start is not None and end is not None
    usage_conditions = [
        UsageEvent.tenant_id == tenant_id,
        UsageEvent.timestamp >= start,
        UsageEvent.timestamp <= end,
    ]
    memory_mau = (
        db.scalar(
            select(func.count(distinct(UsageEvent.user_id))).where(*usage_conditions)
        )
        or 0
    )
    rows = db.execute(
        select(UsageEvent.operation, func.count())
        .where(*usage_conditions)
        .group_by(UsageEvent.operation)
    ).all()
    counts = {operation.value: count for operation, count in rows}
    storage = (
        db.scalar(
            select(func.count())
            .select_from(MemoryRecord)
            .where(
                MemoryRecord.tenant_id == tenant_id,
                MemoryRecord.status != MemoryStatus.DELETED,
            )
        )
        or 0
    )
    device_activations = _audit_count(
        db, tenant_id, AuditAction.DEVICE_BOUND, start, end
    )
    migration_count = _audit_count(
        db, tenant_id, AuditAction.MIGRATION_STARTED, start, end
    )
    return UsageResponse(
        since=start,
        until=end,
        memory_mau=memory_mau,
        memory_ops=MemoryOpsResponse(
            ingest=counts.get(UsageOperation.INGEST.value, 0),
            retrieve=counts.get(UsageOperation.RETRIEVE.value, 0),
            update=counts.get(UsageOperation.UPDATE.value, 0),
            delete=counts.get(UsageOperation.DELETE.value, 0),
        ),
        storage=storage,
        device_activations=device_activations,
        migration_count=migration_count,
    )


def _audit_count(
    db: Session,
    tenant_id: str,
    action: AuditAction,
    since: datetime,
    until: datetime,
) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action == action,
                AuditLog.timestamp >= since,
                AuditLog.timestamp <= until,
            )
        )
        or 0
    )


def _validated_bounds(
    since: datetime | None,
    until: datetime | None,
    *,
    defaults: bool,
) -> tuple[datetime | None, datetime | None]:
    end = _aware(until) if until is not None else (datetime.now(tz=UTC) if defaults else None)
    start = _aware(since) if since is not None else (end - timedelta(days=30) if defaults else None)
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="since must be earlier than or equal to until",
        )
    return start, end


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


__all__ = ["AuditFilters", "AuditPage", "query_audit_logs", "query_usage"]
