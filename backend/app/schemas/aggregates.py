"""Response schemas for audit-log and usage read aggregates."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AuditAction
from app.schemas.common import ID, _OrmModel


class AuditLogResponse(_OrmModel):
    id: ID
    tenant_id: ID
    actor: str
    action: AuditAction
    target: str
    detail: str
    timestamp: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MemoryOpsResponse(BaseModel):
    ingest: int
    retrieve: int
    update: int
    delete: int


class UsageResponse(BaseModel):
    since: datetime
    until: datetime
    memory_mau: int
    memory_ops: MemoryOpsResponse
    storage: int
    device_activations: int
    migration_count: int


__all__ = [
    "AuditLogListResponse",
    "AuditLogResponse",
    "MemoryOpsResponse",
    "UsageResponse",
]
