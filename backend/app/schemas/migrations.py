"""Schemas for migration preview, execution, lookup, and rollback."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MigrationStatus, OldDeviceAccess
from app.schemas.common import ID, _OrmModel


class MigrationPreviewRequest(BaseModel):
    user_id: ID
    source_relationship_id: ID
    target_relationship_id: ID
    source_device_id: ID
    target_device_id: ID


class MigrationBucket(BaseModel):
    memory_ids: list[ID]


class MigrationCounts(BaseModel):
    recommended: int
    needs_review: int
    not_moved: int


class MigrationPreviewResponse(BaseModel):
    migration_id: ID
    status: MigrationStatus
    recommended: MigrationBucket
    needs_review: MigrationBucket
    not_moved: MigrationBucket
    counts: MigrationCounts


class MigrationExecuteRequest(BaseModel):
    migration_id: ID
    selected_memory_ids: list[ID] = Field(min_length=1)
    old_device_access: OldDeviceAccess


class MigrationResponse(_OrmModel):
    id: ID
    user_id: ID
    source_relationship_id: ID
    target_relationship_id: ID
    source_device_id: ID
    target_device_id: ID
    status: MigrationStatus
    selected_memory_ids: list[ID]
    skipped_memory_ids: list[ID]
    failed_memory_ids: list[ID]
    old_device_access: OldDeviceAccess
    audit_log_id: ID | None
    created_at: datetime
    completed_at: datetime | None
    rolled_back_at: datetime | None


__all__ = [
    "MigrationBucket",
    "MigrationCounts",
    "MigrationExecuteRequest",
    "MigrationPreviewRequest",
    "MigrationPreviewResponse",
    "MigrationResponse",
]
