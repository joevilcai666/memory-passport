"""Schemas for listing and mutating MemoryRecord rows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import (
    MemoryScope,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
)
from app.schemas.common import ID, _OrmModel


class MemoryRecordResponse(_OrmModel):
    """The complete public MemoryRecord shape from ``src/lib/types.ts``."""

    id: ID
    tenant_id: ID
    app_id: ID
    passport_id: str
    user_id: ID
    relationship_id: ID
    agent_id: ID
    device_id: ID | None
    type: MemoryType
    content: str
    scope: MemoryScope
    sensitivity: MemorySensitivity
    status: MemoryStatus
    confidence: float
    portability: dict[str, Any]
    source: dict[str, Any]
    valid_from: datetime
    expires_at: datetime | None
    version: int
    supersedes: ID | None
    last_used_at: datetime | None
    usage_count: int
    model_provenance: dict[str, Any]


class MemoryListResponse(BaseModel):
    items: list[MemoryRecordResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MemoryPatch(BaseModel):
    """Exactly one content edit or state transition."""

    content: str | None = Field(default=None, min_length=1)
    status: MemoryStatus | None = None

    @model_validator(mode="after")
    def exactly_one_change(self):
        if (self.content is None) == (self.status is None):
            raise ValueError("provide exactly one of content or status")
        return self


__all__ = ["MemoryListResponse", "MemoryPatch", "MemoryRecordResponse"]
