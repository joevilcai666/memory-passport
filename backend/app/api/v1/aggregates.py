"""Read-only audit-log and usage aggregate endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.models.enums import AuditAction
from app.schemas.aggregates import AuditLogListResponse, UsageResponse
from app.services.aggregates import AuditFilters, query_audit_logs, query_usage

router = APIRouter(prefix="/v1", tags=["aggregates"])


@router.get("/audit_logs", response_model=AuditLogListResponse)
def get_audit_logs(
    db: Session = DbDep,
    tenant=TenantDep,
    actor: str | None = None,
    action: AuditAction | None = None,
    target: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AuditLogListResponse:
    result = query_audit_logs(
        db,
        tenant.tenant.id,
        AuditFilters(actor=actor, action=action, target=target, since=since, until=until),
        page,
        page_size,
    )
    return AuditLogListResponse(**result.__dict__)


@router.get("/usage", response_model=UsageResponse)
def get_usage(
    db: Session = DbDep,
    tenant=TenantDep,
    since: datetime | None = None,
    until: datetime | None = None,
) -> UsageResponse:
    return query_usage(db, tenant.tenant.id, since, until)


__all__ = ["router"]
