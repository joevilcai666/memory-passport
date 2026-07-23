"""Tenant-scoped team listing and secure single-use invitations."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth import TenantContext
from app.models.enums import AuditAction, TeamRole
from app.models.team import TeamInvite, TeamMember
from app.models.tenant import Tenant
from app.services.audit import api_actor, write_audit
from app.services.ids import new_team_invite_id, new_team_member_id


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _conflict(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": code, "message": message},
    )


def list_team(db: Session, tenant_id: str) -> tuple[list[TeamMember], list[TeamInvite]]:
    now = _now()
    members = list(
        db.scalars(
            select(TeamMember)
            .where(TeamMember.tenant_id == tenant_id)
            .order_by(TeamMember.joined_at, TeamMember.id)
        )
    )
    pending = list(
        db.scalars(
            select(TeamInvite)
            .where(
                TeamInvite.tenant_id == tenant_id,
                TeamInvite.accepted_at.is_(None),
                TeamInvite.expires_at > now,
            )
            .order_by(TeamInvite.created_at, TeamInvite.id)
        )
    )
    return members, pending


def create_invite(
    db: Session,
    context: TenantContext,
    *,
    email: str,
    role: TeamRole,
) -> tuple[TeamInvite, str]:
    normalized = email.strip().lower()
    existing_member = db.scalar(
        select(TeamMember).where(
            TeamMember.tenant_id == context.tenant.id,
            TeamMember.email == normalized,
        )
    )
    if existing_member is not None:
        raise _conflict("member_exists", f"{normalized} is already a team member")

    now = _now()
    pending = db.scalar(
        select(TeamInvite).where(
            TeamInvite.tenant_id == context.tenant.id,
            TeamInvite.email == normalized,
            TeamInvite.accepted_at.is_(None),
            TeamInvite.expires_at > now,
        )
    )
    if pending is not None:
        raise _conflict("invite_exists", f"a pending invite already exists for {normalized}")

    token = secrets.token_urlsafe(32)
    invite = TeamInvite(
        id=new_team_invite_id(),
        tenant_id=context.tenant.id,
        email=normalized,
        role=role,
        token_hash=_token_hash(token),
        created_by=api_actor(context.api_key.id),
        created_at=now,
        expires_at=now + timedelta(days=7),
        accepted_at=None,
        accepted_member_id=None,
    )
    db.add(invite)
    db.flush()
    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.TEAM_INVITED,
        target=invite.id,
        detail=f"Invited {normalized} as {role.value}",
    )
    return invite, token


def _invite_for_token(db: Session, token: str, *, lock: bool) -> TeamInvite:
    digest = _token_hash(token)
    statement = select(TeamInvite).where(TeamInvite.token_hash == digest)
    if lock:
        statement = statement.with_for_update()
    invite = db.scalar(statement)
    if invite is None or not hmac.compare_digest(invite.token_hash, digest):
        raise not_found("Team invite")
    if invite.accepted_at is not None:
        raise _conflict("invite_used", "this invitation has already been accepted")
    if _aware(invite.expires_at) <= _now():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "invite_expired", "message": "this invitation has expired"},
        )
    return invite


def preview_invite(db: Session, token: str) -> tuple[TeamInvite, Tenant]:
    invite = _invite_for_token(db, token, lock=False)
    tenant = db.get(Tenant, invite.tenant_id)
    if tenant is None:
        raise not_found("Tenant")
    return invite, tenant


def accept_invite(
    db: Session,
    token: str,
    *,
    name: str,
    avatar_color: str,
) -> TeamMember:
    invite = _invite_for_token(db, token, lock=True)
    existing = db.scalar(
        select(TeamMember).where(
            TeamMember.tenant_id == invite.tenant_id,
            TeamMember.email == invite.email,
        )
    )
    if existing is not None:
        raise _conflict("member_exists", f"{invite.email} is already a team member")

    now = _now()
    member = TeamMember(
        id=new_team_member_id(),
        tenant_id=invite.tenant_id,
        name=name.strip(),
        email=invite.email,
        role=invite.role,
        avatar_color=avatar_color,
        joined_at=now,
        last_active=now,
    )
    db.add(member)
    db.flush()
    invite.accepted_at = now
    invite.accepted_member_id = member.id
    db.flush()
    write_audit(
        db,
        tenant_id=invite.tenant_id,
        actor=f"invite:{invite.id}",
        action=AuditAction.TEAM_JOINED,
        target=member.id,
        detail=f"{member.email} joined as {member.role.value}",
    )
    return member


__all__ = ["accept_invite", "create_invite", "list_team", "preview_invite"]
