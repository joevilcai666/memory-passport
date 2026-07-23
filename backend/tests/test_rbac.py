"""Operator RBAC enforcement — issue #32.

Invite/accept/team persistence is covered by ``test_team.py``. This file proves
the *authorization* half: an API key linked to a Support role is refused policy
mutation (403 ``insufficient_role``), while Owner/Admin/null-role keys succeed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.session import session_scope
from app.models.enums import TeamRole
from app.models.identity import Agent
from app.models.team import TeamMember
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def _policy_body() -> dict:
    return {
        "app_id": "app_rbac",
        "agent_id": "agt_rbac",
        "auto_write_rules": [],
        "portability": {
            "layer": "portable",
            "cross_device": True,
            "cross_role": True,
            "cross_model": True,
            "cross_brand_app": False,
        },
        "retrieval": {"max_memories_per_response": 5},
    }


@pytest.fixture()
def rbac_seed(sqlite_db):
    """Seed one tenant/app/agent plus three API keys: Owner, Admin, Support.

    A fourth key has no linked role (null) — the sandbox/customer path that must
    keep working (treated as Owner).
    """
    keys = {
        "owner": "mp_sandbox_rbac_owner_______________",
        "admin": "mp_sandbox_rbac_admin_______________",
        "support": "mp_sandbox_rbac_support_____________",
        "norole": "mp_sandbox_rbac_norole______________",
    }
    with session_scope() as db:
        db.add(Tenant(id="ten_rbac", name="RBAC", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            App(
                id="app_rbac",
                tenant_id="ten_rbac",
                name="RBAC",
                product_type="software",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=False,
                status="active",
                created_at=_now(),
            )
        )
        db.flush()
        db.add(
            Agent(
                id="agt_rbac",
                app_id="app_rbac",
                name="RBAC Agent",
                type="assistant",
                persona_version="v1",
                memory_policy_id=None,
                allowed_memory_types=["relationship"],
                created_at=_now(),
                emoji="R",
            )
        )
        members = {
            "owner": ("tm_rbac_owner", TeamRole.OWNER, "Owner Op"),
            "admin": ("tm_rbac_admin", TeamRole.ADMIN, "Admin Op"),
            "support": ("tm_rbac_support", TeamRole.SUPPORT, "Support Op"),
        }
        for short, (member_id, role, name) in members.items():
            db.add(
                TeamMember(
                    id=member_id,
                    tenant_id="ten_rbac",
                    name=name,
                    email=f"{short}@rbac.test",
                    role=role,
                    avatar_color="#000000",
                    joined_at=_now(),
                    last_active=_now(),
                )
            )
            db.flush()
            db.add(
                ApiKey(
                    id=f"key_{short}",
                    app_id="app_rbac",
                    label=f"{short} key",
                    environment="sandbox",
                    key=keys[short],
                    created_at=_now(),
                    last_used_at=_now(),
                    team_member_id=member_id,
                    role=role,
                )
            )
        # Null-role key (sandbox / customer backend-to-backend) — no member link.
        db.add(
            ApiKey(
                id="key_norole",
                app_id="app_rbac",
                label="norole key",
                environment="sandbox",
                key=keys["norole"],
                created_at=_now(),
                last_used_at=_now(),
                team_member_id=None,
                role=None,
            )
        )
    return keys


def test_owner_can_change_policy(rbac_seed, app_client):
    response = app_client.post(
        "/v1/policies", headers=_headers(rbac_seed["owner"]), json=_policy_body()
    )
    assert response.status_code in (200, 201), response.text


def test_admin_can_change_policy(rbac_seed, app_client):
    response = app_client.post(
        "/v1/policies", headers=_headers(rbac_seed["admin"]), json=_policy_body()
    )
    assert response.status_code in (200, 201), response.text


def test_support_is_refused_policy_mutation(rbac_seed, app_client):
    """Support may read but cannot mutate policy (issue #32 acceptance)."""
    read = app_client.get(
        "/v1/policies?app_id=app_rbac&agent_id=agt_rbac",
        headers=_headers(rbac_seed["support"]),
    )
    # GET is unprotected by role; a missing policy is a benign 404 here.
    assert read.status_code == 404

    response = app_client.post(
        "/v1/policies", headers=_headers(rbac_seed["support"]), json=_policy_body()
    )
    assert response.status_code == 403, response.text
    body = response.json()["detail"]
    assert body["code"] == "insufficient_role"
    assert "Owner" in body["required"] and "Admin" in body["required"]


def test_null_role_key_is_treated_as_owner(rbac_seed, app_client):
    """Sandbox/customer keys (no linked role) keep full access (Owner default)."""
    response = app_client.post(
        "/v1/policies", headers=_headers(rbac_seed["norole"]), json=_policy_body()
    )
    assert response.status_code in (200, 201), response.text


def test_insufficient_role_writes_no_policy(rbac_seed, app_client):
    from app.models.memory import MemoryPolicy

    app_client.post(
        "/v1/policies", headers=_headers(rbac_seed["support"]), json=_policy_body()
    )
    with session_scope() as db:
        assert db.query(MemoryPolicy).count() == 0
