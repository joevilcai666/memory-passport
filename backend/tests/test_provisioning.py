"""Integration tests for the Slice 2 provisioning endpoints.

Covers every acceptance criterion in issue #2:

* Happy path for each of the 7 endpoints (apps, agents, users, relationships,
  devices register/bind/unbind) — entity returned with generated id + timestamps.
* User idempotency — same (app_id, external_user_id) returns the same user and
  does NOT call HMS a second time.
* Device state machine — bind only from registered; unbind only from bound;
  illegal transitions return 409 with ``illegal_state_transition``.
* Pairing-code authorization — bind without/with wrong code returns 403.
* Tenant isolation — a tenant A key cannot create entities referencing tenant B
  rows (returns 404, not 403, so existence isn't leaked).
* AuditLog — every successful creation appends a row with the expected action.

All sqlite + respx-mocked HMS (no docker/Postgres needed).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import respx

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.identity import User
from app.models.tenant import ApiKey, App, Tenant
from app.services.provisioning import reset_pairing_codes_for_tests


def auth_headers(key: str) -> dict[str, str]:
    """Build a Bearer auth header for a given API key."""
    return {"Authorization": f"Bearer {key}"}


def _now() -> datetime:
    return datetime.now(tz=UTC)


@pytest.fixture(autouse=True)
def _clear_pairing_codes():
    """Each test starts with a clean pairing-code map (the codes are in-process)."""
    reset_pairing_codes_for_tests()


@pytest.fixture()
def two_tenants(sqlite_db):
    """Seed two tenants (A=luna, B=other) each with an app + sandbox key.

    Returns a dict with the ids + keys so tests can authenticate as either.
    """
    with session_scope() as db:
        # Tenant A — Luna (the seeded convention).
        db.add(Tenant(id="ten_luna", name="Luna Inc.", plan="Sandbox", created_at=_now()))
        db.add(
            App(
                id="app_luna",
                tenant_id="ten_luna",
                name="Luna",
                product_type="hybrid",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=True,
                status="active",
                created_at=_now(),
            )
        )
        db.add(
            ApiKey(
                id="key_sb_1",
                app_id="app_luna",
                label="Sandbox — Default",
                environment="sandbox",
                key="mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd",
                created_at=_now(),
                last_used_at=_now(),
            )
        )

        # Tenant B — a second customer.
        db.add(Tenant(id="ten_other", name="Other Co.", plan="Sandbox", created_at=_now()))
        db.add(
            App(
                id="app_other",
                tenant_id="ten_other",
                name="Other",
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
                id="key_other_1",
                app_id="app_other",
                label="Sandbox — Default",
                environment="sandbox",
                key="mp_sandbox_other_other_other_other_other",
                created_at=_now(),
                last_used_at=_now(),
            )
        )

    return {
        "a_key": "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd",
        "a_tenant": "ten_luna",
        "a_app": "app_luna",
        "a_key_id": "key_sb_1",
        "b_key": "mp_sandbox_other_other_other_other_other",
        "b_tenant": "ten_other",
        "b_app": "app_other",
        "b_key_id": "key_other_1",
    }


@pytest.fixture()
def hms_mock():
    """Mock HMS PUT /v1/default/banks/{id} — returns 200 for any bank_id."""
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        route = mock.put(url__regex=r"/v1/default/banks/[^/]+").respond(
            200, json={"status": "ok"}
        )
        yield mock, route


# ---------------------------------------------------------------------------
# POST /v1/apps
# ---------------------------------------------------------------------------


def test_create_app_returns_app_and_api_key(two_tenants, app_client):
    """POST /v1/apps -> 201 + App + auto-generated ApiKey (mp_<env>_<secret>)."""
    resp = app_client.post(
        "/v1/apps",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "name": "Luna v2",
            "product_type": "software",
            "environment": "production",
            "data_region": "eu-west-1",
            "show_powered_by": False,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    app = body["app"]
    key = body["api_key"]

    assert app["id"].startswith("app_")
    assert app["tenant_id"] == two_tenants["a_tenant"]
    assert app["name"] == "Luna v2"
    assert app["product_type"] == "software"
    assert app["environment"] == "production"
    assert app["data_region"] == "eu-west-1"
    assert app["show_powered_by"] is False
    assert app["status"] == "active"
    assert app["created_at"]

    assert key["id"].startswith("key_")
    assert key["environment"] == "production"
    # mp_live_<secret> — production keys use the "live" segment.
    assert key["key"].startswith("mp_live_")
    assert key["created_at"]


def test_create_app_writes_audit_log(two_tenants, app_client):
    """A successful app creation appends an AuditLog row (action=app.created)."""
    app_client.post(
        "/v1/apps",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "name": "Audited App",
            "product_type": "hardware",
            "environment": "sandbox",
            "data_region": "us-east-1",
        },
    )
    with session_scope() as db:
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == two_tenants["a_tenant"],
                AuditLog.action == AuditAction.APP_CREATED,
            )
            .all()
        )
    assert len(rows) == 1
    assert rows[0].actor == f"api:{two_tenants['a_key_id']}"
    assert rows[0].target.startswith("app_")


# ---------------------------------------------------------------------------
# POST /v1/agents
# ---------------------------------------------------------------------------


def test_create_agent_happy_path(two_tenants, app_client):
    resp = app_client.post(
        "/v1/agents",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "name": "Nova",
            "type": "companion",
            "persona_version": "nova.v1",
            "allowed_memory_types": ["profile", "preference"],
            "emoji": "✨",
        },
    )
    assert resp.status_code == 201, resp.text
    agent = resp.json()
    assert agent["id"].startswith("agt_")
    assert agent["app_id"] == two_tenants["a_app"]
    assert agent["name"] == "Nova"
    assert agent["type"] == "companion"
    assert agent["persona_version"] == "nova.v1"
    assert agent["allowed_memory_types"] == ["profile", "preference"]
    assert agent["emoji"] == "✨"
    assert agent["created_at"]


def test_create_agent_cross_tenant_app_returns_404(two_tenants, app_client):
    """Tenant A's key referencing tenant B's app_id -> 404 (no existence leak)."""
    resp = app_client.post(
        "/v1/agents",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["b_app"],  # B's app
            "name": "Infiltrator",
            "type": "assistant",
            "persona_version": "v1",
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# POST /v1/users
# ---------------------------------------------------------------------------


def test_create_user_provisions_hms_bank_once(two_tenants, app_client, hms_mock):
    """First call creates the user + provisions HMS exactly once."""
    _mock, route = hms_mock
    resp = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_001",
            "region": "US",
            "display_name": "Test User",
        },
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["id"].startswith("usr_")
    assert user["passport_id"].startswith("pp_")
    assert user["external_user_id"] == "ext_001"
    assert user["memory_enabled"] is True
    assert user["created_at"]
    # HMS called exactly once, bank_id == user.id.
    assert route.call_count == 1
    called_url = str(route.calls.last.request.url)
    assert called_url.endswith(f"/v1/default/banks/{user['id']}")


def test_create_user_is_idempotent(two_tenants, app_client, hms_mock):
    """Same (app_id, external_user_id) returns the same user; HMS NOT called twice."""
    _mock, route = hms_mock
    body = {
        "app_id": two_tenants["a_app"],
        "external_user_id": "ext_dup",
        "region": "US",
        "display_name": "Dup User",
    }
    first = app_client.post("/v1/users", headers=auth_headers(two_tenants["a_key"]), json=body)
    second = app_client.post("/v1/users", headers=auth_headers(two_tenants["a_key"]), json=body)

    assert first.status_code == 201
    assert second.status_code == 201
    # Same user (same id + passport_id) returned both times.
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["passport_id"] == second.json()["passport_id"]
    # HMS bank provisioned exactly once across both calls.
    assert route.call_count == 1


def test_create_user_writes_audit_and_persists(two_tenants, app_client, hms_mock):
    app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_audit",
            "region": "US",
            "display_name": "Audit User",
        },
    )
    with session_scope() as db:
        user = db.query(User).filter(User.external_user_id == "ext_audit").one()
        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == two_tenants["a_tenant"],
                AuditLog.action == AuditAction.USER_CREATED,
                AuditLog.target == user.id,
            )
            .one()
        )
    assert audit.actor == f"api:{two_tenants['a_key_id']}"


def test_create_user_hms_failure_returns_502_and_rolls_back(two_tenants, app_client):
    """HMS provisioning failure -> 502, no User row survives."""
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.put(url__regex=r"/v1/default/banks/[^/]+").respond(500)
        resp = app_client.post(
            "/v1/users",
            headers=auth_headers(two_tenants["a_key"]),
            json={
                "app_id": two_tenants["a_app"],
                "external_user_id": "ext_fail",
                "region": "US",
                "display_name": "Fail User",
            },
        )
    assert resp.status_code == 502, resp.text
    assert resp.json()["detail"]["code"] == "hms_provisioning_failed"
    with session_scope() as db:
        assert (
            db.query(User).filter(User.external_user_id == "ext_fail").one_or_none()
            is None
        )


# ---------------------------------------------------------------------------
# POST /v1/relationships
# ---------------------------------------------------------------------------


def test_create_relationship_happy_path(two_tenants, app_client, hms_mock):
    # Create a user + agent first (relationship links them).
    user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_rel",
            "region": "US",
            "display_name": "Rel User",
        },
    ).json()
    agent = app_client.post(
        "/v1/agents",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "name": "Rel Agent",
            "type": "companion",
            "persona_version": "v1",
        },
    ).json()

    resp = app_client.post(
        "/v1/relationships",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "user_id": user["id"],
            "agent_id": agent["id"],
            "relationship_type": "companion",
            "memory_enabled": True,
        },
    )
    assert resp.status_code == 201, resp.text
    rel = resp.json()
    assert rel["id"].startswith("rel_")
    assert rel["user_id"] == user["id"]
    assert rel["agent_id"] == agent["id"]
    assert rel["relationship_type"] == "companion"
    assert rel["memory_enabled"] is True
    assert rel["created_at"]


def test_create_relationship_cross_tenant_user_404(two_tenants, app_client, hms_mock):
    """Tenant A referencing tenant B's user_id -> 404."""
    # Create the user under tenant B first.
    b_user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["b_key"]),
        json={
            "app_id": two_tenants["b_app"],
            "external_user_id": "ext_b",
            "region": "US",
            "display_name": "B User",
        },
    ).json()
    # Create an agent under tenant A to satisfy the agent leg.
    a_agent = app_client.post(
        "/v1/agents",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "name": "A Agent",
            "type": "companion",
            "persona_version": "v1",
        },
    ).json()
    # Now tenant A tries to reference tenant B's user -> 404.
    resp = app_client.post(
        "/v1/relationships",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "user_id": b_user["id"],
            "agent_id": a_agent["id"],
            "relationship_type": "companion",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# POST /v1/devices/register
# ---------------------------------------------------------------------------


def test_register_device_returns_registered_status_and_pairing_code(two_tenants, app_client):
    resp = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "model": "Luna Robot",
            "generation": "v2",
            "serial_number_hash": "deadbeef",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    device = body["device"]
    code = body["pairing_code"]
    assert device["id"].startswith("dev_")
    assert device["status"] == "registered"
    assert device["bound_user_id"] is None
    assert device["model"] == "Luna Robot"
    assert device["generation"] == "v2"
    assert device["serial_number_hash"] == "deadbeef"
    assert isinstance(code, str)
    assert len(code) == 8


# ---------------------------------------------------------------------------
# POST /v1/devices/bind
# ---------------------------------------------------------------------------


def test_bind_device_happy_path(two_tenants, app_client, hms_mock):
    # register a device.
    dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["a_key"]),
        json={"model": "R1", "generation": "v1", "serial_number_hash": "abc"},
    ).json()
    device_id = dev["device"]["id"]
    code = dev["pairing_code"]
    # create a user to bind to.
    user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_bind",
            "region": "US",
            "display_name": "Bind User",
        },
    ).json()

    resp = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "device_id": device_id,
            "user_id": user["id"],
            "pairing_code": code,
        },
    )
    assert resp.status_code == 200, resp.text
    device = resp.json()
    assert device["status"] == "bound"
    assert device["bound_user_id"] == user["id"]
    assert device["last_seen_at"]

    # Audit row for device.bound was written.
    with session_scope() as db:
        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == two_tenants["a_tenant"],
                AuditLog.action == AuditAction.DEVICE_BOUND,
                AuditLog.target == device_id,
            )
            .one()
        )
    assert audit.actor == f"api:{two_tenants['a_key_id']}"


def test_bind_device_wrong_pairing_code_returns_403(two_tenants, app_client, hms_mock):
    dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["a_key"]),
        json={"model": "R1", "generation": "v1", "serial_number_hash": "abc"},
    ).json()
    user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_bind_bad",
            "region": "US",
            "display_name": "Bad Bind User",
        },
    ).json()

    resp = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "device_id": dev["device"]["id"],
            "user_id": user["id"],
            "pairing_code": "WRONG123",
        },
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"]["code"] == "invalid_pairing_code"


def test_bind_device_without_pairing_code_is_422(two_tenants, app_client):
    """Anonymous / code-less bind is rejected at the schema layer (422)."""
    resp = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={"device_id": "dev_whatever", "user_id": "usr_whatever"},  # no pairing_code
    )
    assert resp.status_code == 422


def test_bind_device_anonymous_missing_user_is_422(two_tenants, app_client):
    """A bind without user_id (anonymous) is rejected by the schema (PRD §9.1)."""
    resp = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={"device_id": "dev_x", "pairing_code": "CODE1234"},
    )
    assert resp.status_code == 422


def test_bind_already_bound_device_returns_409(two_tenants, app_client, hms_mock):
    """bind on a 'bound' device -> 409 illegal_state_transition."""
    dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["a_key"]),
        json={"model": "R1", "generation": "v1", "serial_number_hash": "abc"},
    ).json()
    user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_double_bind",
            "region": "US",
            "display_name": "Double Bind",
        },
    ).json()
    # First bind succeeds.
    first = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "device_id": dev["device"]["id"],
            "user_id": user["id"],
            "pairing_code": dev["pairing_code"],
        },
    )
    assert first.status_code == 200

    # Second bind (now bound, code consumed) -> 409 (state check happens before
    # the code check, so the body is illegal_state_transition).
    second = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "device_id": dev["device"]["id"],
            "user_id": user["id"],
            "pairing_code": "ANYCODE1",
        },
    )
    assert second.status_code == 409, second.text
    detail = second.json()["detail"]
    assert detail["code"] == "illegal_state_transition"
    assert detail["current"] == "bound"
    assert detail["action"] == "bind"


# ---------------------------------------------------------------------------
# POST /v1/devices/unbind
# ---------------------------------------------------------------------------


def test_unbind_device_happy_path(two_tenants, app_client, hms_mock):
    dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["a_key"]),
        json={"model": "R1", "generation": "v1", "serial_number_hash": "abc"},
    ).json()
    user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_unbind",
            "region": "US",
            "display_name": "Unbind User",
        },
    ).json()
    app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "device_id": dev["device"]["id"],
            "user_id": user["id"],
            "pairing_code": dev["pairing_code"],
        },
    )

    resp = app_client.post(
        "/v1/devices/unbind",
        headers=auth_headers(two_tenants["a_key"]),
        json={"device_id": dev["device"]["id"]},
    )
    assert resp.status_code == 200, resp.text
    device = resp.json()
    assert device["status"] == "unbound"
    assert device["bound_user_id"] is None

    with session_scope() as db:
        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == two_tenants["a_tenant"],
                AuditLog.action == AuditAction.DEVICE_UNBOUND,
                AuditLog.target == dev["device"]["id"],
            )
            .one()
        )
    assert audit.actor == f"api:{two_tenants['a_key_id']}"


def test_unbind_registered_device_returns_409(two_tenants, app_client):
    """unbind on a 'registered' (never-bound) device -> 409."""
    dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["a_key"]),
        json={"model": "R1", "generation": "v1", "serial_number_hash": "abc"},
    ).json()
    resp = app_client.post(
        "/v1/devices/unbind",
        headers=auth_headers(two_tenants["a_key"]),
        json={"device_id": dev["device"]["id"]},
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "illegal_state_transition"
    assert detail["current"] == "registered"
    assert detail["action"] == "unbind"


def test_unbind_already_unbound_returns_409(two_tenants, app_client, hms_mock):
    """unbind on an 'unbound' device -> 409."""
    dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["a_key"]),
        json={"model": "R1", "generation": "v1", "serial_number_hash": "abc"},
    ).json()
    user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_unbind2",
            "region": "US",
            "display_name": "Unbind2",
        },
    ).json()
    bind = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "device_id": dev["device"]["id"],
            "user_id": user["id"],
            "pairing_code": dev["pairing_code"],
        },
    )
    assert bind.status_code == 200
    # First unbind succeeds.
    app_client.post(
        "/v1/devices/unbind",
        headers=auth_headers(two_tenants["a_key"]),
        json={"device_id": dev["device"]["id"]},
    )
    # Second unbind -> 409.
    second = app_client.post(
        "/v1/devices/unbind",
        headers=auth_headers(two_tenants["a_key"]),
        json={"device_id": dev["device"]["id"]},
    )
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["current"] == "unbound"
    assert detail["action"] == "unbind"


# ---------------------------------------------------------------------------
# Tenant isolation (device dimension)
# ---------------------------------------------------------------------------


def test_bind_cross_tenant_device_returns_404(two_tenants, app_client, hms_mock):
    """Tenant A's key cannot bind tenant B's device -> 404."""
    # Tenant B registers a device.
    b_dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["b_key"]),
        json={"model": "BR", "generation": "v1", "serial_number_hash": "bbb"},
    ).json()
    # Tenant A creates its own user.
    a_user = app_client.post(
        "/v1/users",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "app_id": two_tenants["a_app"],
            "external_user_id": "ext_a",
            "region": "US",
            "display_name": "A User",
        },
    ).json()
    # Tenant A tries to bind B's device -> 404.
    resp = app_client.post(
        "/v1/devices/bind",
        headers=auth_headers(two_tenants["a_key"]),
        json={
            "device_id": b_dev["device"]["id"],
            "user_id": a_user["id"],
            "pairing_code": b_dev["pairing_code"],
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "not_found"


def test_unbind_cross_tenant_device_returns_404(two_tenants, app_client):
    """Tenant A's key cannot unbind tenant B's device -> 404."""
    b_dev = app_client.post(
        "/v1/devices/register",
        headers=auth_headers(two_tenants["b_key"]),
        json={"model": "BR", "generation": "v1", "serial_number_hash": "bbb"},
    ).json()
    resp = app_client.post(
        "/v1/devices/unbind",
        headers=auth_headers(two_tenants["a_key"]),
        json={"device_id": b_dev["device"]["id"]},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth regression
# ---------------------------------------------------------------------------


def test_provisioning_endpoints_require_auth(app_client, two_tenants):
    """No Authorization header on a protected provisioning route -> 401."""
    for path in ("/v1/apps", "/v1/agents", "/v1/users", "/v1/relationships",
                 "/v1/devices/register", "/v1/devices/bind", "/v1/devices/unbind"):
        resp = app_client.post(path, json={})
        assert resp.status_code == 401, f"{path} did not return 401: {resp.status_code}"
        assert resp.json() == {"detail": "unauthenticated"}
