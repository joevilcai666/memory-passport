"""Schemas for tenant team members and one-time invitations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import TeamRole
from app.schemas.common import ID, _OrmModel


class TeamMemberResponse(_OrmModel):
    id: ID
    name: str
    email: str
    role: TeamRole
    avatar_color: str
    joined_at: datetime
    last_active: datetime


class TeamInviteResponse(_OrmModel):
    id: ID
    email: str
    role: TeamRole
    created_by: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None


class TeamResponse(BaseModel):
    members: list[TeamMemberResponse]
    pending_invites: list[TeamInviteResponse]


class TeamInviteCreateRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    role: TeamRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("email must be a valid address")
        return normalized


class TeamInviteCreateResponse(BaseModel):
    invite: TeamInviteResponse
    token: str


class PublicTeamInviteResponse(BaseModel):
    tenant_name: str
    email: str
    role: TeamRole
    expires_at: datetime


class TeamInviteAcceptRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    avatar_color: str = Field(default="#6366f1", min_length=4, max_length=32)


__all__ = [
    "PublicTeamInviteResponse",
    "TeamInviteAcceptRequest",
    "TeamInviteCreateRequest",
    "TeamInviteCreateResponse",
    "TeamInviteResponse",
    "TeamMemberResponse",
    "TeamResponse",
]
