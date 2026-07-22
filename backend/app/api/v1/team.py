"""Authenticated tenant team routes plus public invite preview/accept."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.auth import TenantContext
from app.schemas.team import (
    PublicTeamInviteResponse,
    TeamInviteAcceptRequest,
    TeamInviteCreateRequest,
    TeamInviteCreateResponse,
    TeamInviteResponse,
    TeamMemberResponse,
    TeamResponse,
)
from app.services import team

router = APIRouter(prefix="/v1", tags=["team"])


@router.get("/team", response_model=TeamResponse)
def get_team(
    db: Session = DbDep,
    tenant: TenantContext = TenantDep,
) -> TeamResponse:
    members, pending = team.list_team(db, tenant.tenant.id)
    return TeamResponse(
        members=[TeamMemberResponse.model_validate(row) for row in members],
        pending_invites=[TeamInviteResponse.model_validate(row) for row in pending],
    )


@router.post(
    "/team/invites",
    response_model=TeamInviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    body: TeamInviteCreateRequest,
    db: Session = DbDep,
    tenant: TenantContext = TenantDep,
) -> TeamInviteCreateResponse:
    invite, token = team.create_invite(
        db,
        tenant,
        email=body.email,
        role=body.role,
    )
    db.commit()
    db.refresh(invite)
    return TeamInviteCreateResponse(
        invite=TeamInviteResponse.model_validate(invite),
        token=token,
    )


@router.get(
    "/public/team-invites/{token}",
    response_model=PublicTeamInviteResponse,
)
def preview_team_invite(token: str, db: Session = DbDep) -> PublicTeamInviteResponse:
    invite, tenant = team.preview_invite(db, token)
    return PublicTeamInviteResponse(
        tenant_name=tenant.name,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
    )


@router.post(
    "/public/team-invites/{token}/accept",
    response_model=TeamMemberResponse,
)
def accept_team_invite(
    token: str,
    body: TeamInviteAcceptRequest,
    db: Session = DbDep,
) -> TeamMemberResponse:
    member = team.accept_invite(
        db,
        token,
        name=body.name,
        avatar_color=body.avatar_color,
    )
    db.commit()
    db.refresh(member)
    return TeamMemberResponse.model_validate(member)
