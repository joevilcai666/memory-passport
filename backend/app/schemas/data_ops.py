"""Schemas for asynchronous exports and delete-user."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ExportStatus, PassportStatus
from app.schemas.common import ID


class ExportCreateRequest(BaseModel):
    user_id: ID
    format: Literal["json"] = "json"


class ExportCreateResponse(BaseModel):
    export_id: ID


class ExportStatusResponse(BaseModel):
    export_id: ID
    status: ExportStatus
    download_url: str | None = None
    expires_at: datetime | None = None
    error: str | None = None


class DeleteUserRequest(BaseModel):
    user_id: ID


class DeleteUserResponse(BaseModel):
    user_id: ID
    tombstoned_memories: int
    hms_bank_deleted: bool
    passport_status: PassportStatus


__all__ = [
    "DeleteUserRequest",
    "DeleteUserResponse",
    "ExportCreateRequest",
    "ExportCreateResponse",
    "ExportStatusResponse",
]
