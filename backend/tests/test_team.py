"""Tenant team-list and secure invitation-flow tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import AuditAction, TeamRole
from app.models.team import TeamInvite, TeamMember
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture()
def team_rows(sqlite_db):
    key_a = "mp_sandbox_team_team_team_team_team_a"
    key_b = "mp_sandbox_team_team_team_team_team_b"
    with session_scope() as db:
        for suffix, key in (("a", key_a), ("b", key_b)):
            tenant_id = f"ten_team_{suffix}"
            app_id = f"app_team_{suffix}"
            db.add(
                Tenant(
                    id=tenant_id,
                    name=f"Team {suffix.upper()}",
                    plan="Sandbox",
                    created_at=_now(),
                )
            )
            db.add(
                App(
                    id=app_id,
                    tenant_id=tenant_id,
                    name=app_id,
                    product_type="software",
                    environment="sandbox",
                    data_region="us-east-1",
                    show_powered_by=False,
                    status="active",
                    created_at=_now(),
                )
            )
            db.add(
                ApiKey(
                    id=f"key_team_{suffix}",
                    app_id=app_id,
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=_now(),
                    last_used_at=_now(),
                )
            )
            db.add(
                TeamMember(
                    id=f"tm_team_{suffix}",
                    tenant_id=tenant_id,
                    name=f"Owner {suffix.upper()}",
                    email=f"owner_{suffix}@example.com",
                    role=TeamRole.OWNER,
                    avatar_color="#1E3A8A",
                    joined_at=_now(),
                    last_active=_now(),
                )
            )
    return {"key_a": key_a, "key_b": key_b}


def test_team_list_and_pending_invites_are_tenant_scoped(team_rows, app_client):
    response = app_client.get("/v1/team", headers=_auth(team_rows["key_a"]))

    assert response.status_code == 200, response.text
    assert [member["email"] for member in response.json()["members"]] == [
        "owner_a@example.com"
    ]
    assert response.json()["pending_invites"] == []


def test_invite_normalizes_email_stores_only_hash_and_returns_token_once(
    team_rows, app_client
):
    headers = _auth(team_rows["key_a"])
    created = app_client.post(
        "/v1/team/invites",
        headers=headers,
        json={"email": "  New.Member@Example.COM ", "role": "Support"},
    )

    assert created.status_code == 201, created.text
    body = created.json()
    token = body["token"]
    assert token
    assert body["invite"]["email"] == "new.member@example.com"
    assert body["invite"]["role"] == "Support"

    with session_scope() as db:
        invite = db.get(TeamInvite, body["invite"]["id"])
        assert invite.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert invite.token_hash != token
        assert invite.created_by == "api:key_team_a"

    listed = app_client.get("/v1/team", headers=headers)
    assert listed.status_code == 200, listed.text
    pending = listed.json()["pending_invites"]
    assert [row["email"] for row in pending] == ["new.member@example.com"]
    assert "token" not in pending[0]
    assert "token_hash" not in pending[0]

    with session_scope() as db:
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.TEAM_INVITED)
            .count()
            == 1
        )


def test_public_invite_preview_and_single_use_accept(team_rows, app_client):
    created = app_client.post(
        "/v1/team/invites",
        headers=_auth(team_rows["key_a"]),
        json={"email": "joiner@example.com", "role": "Admin"},
    )
    assert created.status_code == 201, created.text
    token = created.json()["token"]

    preview = app_client.get(f"/v1/public/team-invites/{token}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["tenant_name"] == "Team A"
    assert preview.json()["email"] == "joiner@example.com"
    assert preview.json()["role"] == "Admin"

    accepted = app_client.post(
        f"/v1/public/team-invites/{token}/accept",
        json={"name": "Joiner Person", "avatar_color": "#10b981"},
    )
    assert accepted.status_code == 200, accepted.text
    member = accepted.json()
    assert member["email"] == "joiner@example.com"
    assert member["role"] == "Admin"
    assert member["name"] == "Joiner Person"

    repeated = app_client.post(
        f"/v1/public/team-invites/{token}/accept",
        json={"name": "Duplicate Person"},
    )
    assert repeated.status_code == 409, repeated.text
    assert repeated.json()["detail"]["code"] == "invite_used"

    with session_scope() as db:
        assert (
            db.query(TeamMember)
            .filter(TeamMember.email == "joiner@example.com")
            .count()
            == 1
        )
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.TEAM_JOINED)
            .count()
            == 1
        )


def test_expired_invite_is_rejected(team_rows, app_client):
    created = app_client.post(
        "/v1/team/invites",
        headers=_auth(team_rows["key_a"]),
        json={"email": "late@example.com", "role": "Support"},
    )
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    invite_id = created.json()["invite"]["id"]
    with session_scope() as db:
        invite = db.get(TeamInvite, invite_id)
        invite.expires_at = _now() - timedelta(seconds=1)

    preview = app_client.get(f"/v1/public/team-invites/{token}")
    assert preview.status_code == 410, preview.text
    assert preview.json()["detail"]["code"] == "invite_expired"


def test_invite_role_is_validated(team_rows, app_client):
    response = app_client.post(
        "/v1/team/invites",
        headers=_auth(team_rows["key_a"]),
        json={"email": "invalid@example.com", "role": "Superuser"},
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("role", ["Owner", "Admin", "Support"])
def test_all_v01_team_roles_can_be_invited(team_rows, app_client, role):
    response = app_client.post(
        "/v1/team/invites",
        headers=_auth(team_rows["key_a"]),
        json={"email": f"{role.lower()}@example.com", "role": role},
    )
    assert response.status_code == 201, response.text
    assert response.json()["invite"]["role"] == role
