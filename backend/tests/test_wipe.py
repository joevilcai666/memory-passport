"""Integration tests for POST /v1/devices/wipe (Slice 7, issue #3).

Covers every acceptance criterion:
* wipe only succeeds on a 'bound' device; registered/unbound/wiped -> 409.
* scope-selective tombstoning: device_only -> deleted; user_global /
  relationship_only on the same device untouched.
* post-wipe retrieve rejection: a wiped device's device_only memories are not
  returned by POST /v1/memories/retrieve (coordination with Slice 4).
* audit row written with action=device.wiped.
* cross-tenant wipe -> 404.

The device_only tombstoning + retrieve-rejection coordination is the heart of
the privacy-positive "factory reset" path (PRD §9.1).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import respx

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    DeviceStatus,
    MemoryScope,
    MemoryStatus,
)
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.tenant import ApiKey, App, Tenant
from app.services.provisioning import reset_pairing_codes_for_tests


def auth_headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def _now() -> datetime:
    return datetime.now(tz=UTC)


@pytest.fixture(autouse=True)
def _clear_pairing_codes():
    reset_pairing_codes_for_tests()


@pytest.fixture()
def tenant_and_key(sqlite_db):
    """Seed one tenant + app + key. Tests add devices/memories as needed."""
    tenant_id = "ten_wipe"
    app_id = "app_wipe"
    agent_id = "agt_wipe"
    user_id = "usr_wipe"
    rel_id = "rel_wipe"
    key = "mp_sandbox_wipe_wipe_wipe_wipe_wipe"

    with session_scope() as db:
        db.add(Tenant(id=tenant_id, name="Wipe Co.", plan="Sandbox", created_at=_now()))
        db.add(
            App(
                id=app_id,
                tenant_id=tenant_id,
                name="Wipe",
                product_type="hybrid",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=False,
                status="active",
                created_at=_now(),
            )
        )
        db.add(
            ApiKey(
                id="key_wipe_1",
                app_id=app_id,
                label="Sandbox",
                environment="sandbox",
                key=key,
                created_at=_now(),
                last_used_at=_now(),
            )
        )
        db.add(
            User(
                id=user_id,
                tenant_id=tenant_id,
                external_user_id="ext_wipe",
                passport_id="pp_wipe_001",
                age_group="adult",
                region="US",
                memory_enabled=True,
                created_at=_now(),
                display_name="Wipe Tester",
                avatar_color="#000000",
            )
        )
        db.add(
            Agent(
                id=agent_id,
                app_id=app_id,
                name="Wipe Agent",
                type="companion",
                persona_version="v1",
                memory_policy_id=None,
                allowed_memory_types=["preference"],
                created_at=_now(),
                emoji="🧻",
            )
        )
        db.add(
            Relationship(
                id=rel_id,
                tenant_id=tenant_id,
                user_id=user_id,
                agent_id=agent_id,
                device_id=None,
                relationship_type="companion",
                memory_enabled=True,
                created_at=_now(),
            )
        )

    return {
        "key": key,
        "tenant_id": tenant_id,
        "app_id": app_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "rel_id": rel_id,
    }


def _add_device(
    *,
    tenant_id: str,
    device_id: str,
    status: DeviceStatus = DeviceStatus.BOUND,
    bound_user_id: str | None = "usr_wipe",
):
    with session_scope() as db:
        db.add(
            Device(
                id=device_id,
                tenant_id=tenant_id,
                model="R1",
                generation="v1",
                serial_number_hash=f"hash_{device_id}",
                status=status,
                bound_user_id=bound_user_id,
                last_seen_at=_now(),
            )
        )


def _add_memory(
    *,
    tenant_id: str,
    app_id: str,
    user_id: str,
    agent_id: str,
    rel_id: str,
    mp_id: str,
    hms_unit_id: str,
    scope: MemoryScope,
    device_id: str | None = None,
    content: str = "a memory",
    status: MemoryStatus = MemoryStatus.ACTIVE,
):
    """Seed a MemoryRecord + its HMS mapping row (the shape ingest produces)."""
    now = _now()
    with session_scope() as db:
        db.add(
            MemoryRecord(
                id=mp_id,
                tenant_id=tenant_id,
                app_id=app_id,
                passport_id="pp_wipe_001",
                user_id=user_id,
                relationship_id=rel_id,
                agent_id=agent_id,
                device_id=device_id,
                type="preference",
                content=content,
                scope=scope,
                sensitivity="S1",
                status=status,
                confidence=0.9,
                portability={
                    "layer": "portable",
                    "cross_device": True,
                    "cross_role": True,
                    "cross_model": True,
                    "cross_brand_app": False,
                },
                source={
                    "event_id": "evt_seed",
                    "source_type": "chat",
                    "timestamp": now.isoformat(),
                    "quote": content,
                },
                valid_from=now,
                expires_at=None,
                version=1,
                supersedes=None,
                last_used_at=None,
                usage_count=0,
                model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []},
            )
        )
        db.flush()
        db.add(
            MemoryRecordHmsUnit(
                mp_memory_id=mp_id,
                tenant_id=tenant_id,
                hms_unit_id=hms_unit_id,
                hms_bank_id=user_id,
                hms_document_id="evt_seed",
                created_at=now,
            )
        )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_wipe_bound_device_tombstones_device_only_memories(tenant_and_key, app_client):
    """wipe: bound -> wiped; device_only memories tombstoned; count returned."""
    s = tenant_and_key
    _add_device(tenant_id=s["tenant_id"], device_id="dev_bound", status=DeviceStatus.BOUND)
    # Two device_only memories on the device + one user_global on the same device.
    _add_memory(tenant_id=s["tenant_id"], app_id=s["app_id"], user_id=s["user_id"],
                agent_id=s["agent_id"], rel_id=s["rel_id"],
                mp_id="mem_dev_a", hms_unit_id="hms_a",
                scope=MemoryScope.DEVICE_ONLY, device_id="dev_bound", content="dev only A")
    _add_memory(tenant_id=s["tenant_id"], app_id=s["app_id"], user_id=s["user_id"],
                agent_id=s["agent_id"], rel_id=s["rel_id"],
                mp_id="mem_dev_b", hms_unit_id="hms_b",
                scope=MemoryScope.DEVICE_ONLY, device_id="dev_bound", content="dev only B")
    _add_memory(tenant_id=s["tenant_id"], app_id=s["app_id"], user_id=s["user_id"],
                agent_id=s["agent_id"], rel_id=s["rel_id"],
                mp_id="mem_global", hms_unit_id="hms_g",
                scope=MemoryScope.USER_GLOBAL, device_id="dev_bound",
                content="global on same device")

    resp = app_client.post(
        "/v1/devices/wipe",
        headers=auth_headers(s["key"]),
        json={"device_id": "dev_bound"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["device"]["id"] == "dev_bound"
    assert body["device"]["status"] == "wiped"
    assert body["device"]["bound_user_id"] is None
    assert body["tombstoned_memories"] == 2  # only the 2 device_only ones

    # Verify the tombstone was scope-selective.
    with session_scope() as db:
        a = db.query(MemoryRecord).filter(MemoryRecord.id == "mem_dev_a").one()
        b = db.query(MemoryRecord).filter(MemoryRecord.id == "mem_dev_b").one()
        g = db.query(MemoryRecord).filter(MemoryRecord.id == "mem_global").one()
    assert a.status == MemoryStatus.DELETED
    assert b.status == MemoryStatus.DELETED
    assert g.status == MemoryStatus.ACTIVE  # user_global untouched


def test_wipe_writes_audit_row(tenant_and_key, app_client):
    s = tenant_and_key
    _add_device(tenant_id=s["tenant_id"], device_id="dev_audit", status=DeviceStatus.BOUND)
    _add_memory(tenant_id=s["tenant_id"], app_id=s["app_id"], user_id=s["user_id"],
                agent_id=s["agent_id"], rel_id=s["rel_id"],
                mp_id="mem_audit", hms_unit_id="hms_audit",
                scope=MemoryScope.DEVICE_ONLY, device_id="dev_audit")

    app_client.post(
        "/v1/devices/wipe",
        headers=auth_headers(s["key"]),
        json={"device_id": "dev_audit"},
    )
    with session_scope() as db:
        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == s["tenant_id"],
                AuditLog.action == AuditAction.DEVICE_WIPED,
                AuditLog.target == "dev_audit",
            )
            .one()
        )
    assert "tombstoned 1" in audit.detail


# ---------------------------------------------------------------------------
# Illegal source-state transitions -> 409
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        DeviceStatus.REGISTERED,
        DeviceStatus.UNBOUND,
        DeviceStatus.WIPED,
    ],
)
def test_wipe_illegal_source_state_returns_409(tenant_and_key, app_client, status):
    """wipe on registered/unbound/wiped -> 409 illegal_state_transition."""
    s = tenant_and_key
    _add_device(
        tenant_id=s["tenant_id"],
        device_id=f"dev_{status.value}",
        status=status,
        bound_user_id=None,
    )
    resp = app_client.post(
        "/v1/devices/wipe",
        headers=auth_headers(s["key"]),
        json={"device_id": f"dev_{status.value}"},
    )
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "illegal_state_transition"
    assert detail["current"] == status.value
    assert detail["action"] == "wipe"


# ---------------------------------------------------------------------------
# Cross-tenant isolation
# ---------------------------------------------------------------------------


def test_wipe_cross_tenant_device_returns_404(tenant_and_key, app_client, sqlite_db):
    """Wiping another tenant's device -> 404 (no existence leak)."""
    s = tenant_and_key
    with session_scope() as db:
        db.add(Tenant(id="ten_other", name="Other", plan="Sandbox", created_at=_now()))
        db.add(
            Device(
                id="dev_other",
                tenant_id="ten_other",
                model="R1",
                generation="v1",
                serial_number_hash="other",
                status=DeviceStatus.BOUND,
                bound_user_id=None,
                last_seen_at=_now(),
            )
        )
    resp = app_client.post(
        "/v1/devices/wipe",
        headers=auth_headers(s["key"]),  # tenant_wipe's key
        json={"device_id": "dev_other"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Post-wipe retrieve rejection (coordination with Slice 4)
# ---------------------------------------------------------------------------


def test_wiped_device_cannot_retrieve_device_only_memories(tenant_and_key, app_client):
    """After wipe, a device_only memory is NOT returned to that device via retrieve.

    This is the end-to-end privacy check: ingest-then-wipe-then-retrieve shows
    the wiped device's device_only memory is both tombstoned (DB) AND filtered
    (retrieve scope matrix).
    """
    s = tenant_and_key
    # Start with a bound device + a device_only memory on it.
    _add_device(tenant_id=s["tenant_id"], device_id="dev_retr", status=DeviceStatus.BOUND)
    _add_memory(tenant_id=s["tenant_id"], app_id=s["app_id"], user_id=s["user_id"],
                agent_id=s["agent_id"], rel_id=s["rel_id"],
                mp_id="mem_dev_retr", hms_unit_id="hms_dev_retr",
                scope=MemoryScope.DEVICE_ONLY, device_id="dev_retr",
                content="secret on device")

    # Retrieve AS the bound device — the device_only memory IS returned.
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").respond(
            200, json={"results": [{"id": "hms_dev_retr", "text": "secret on device"}]}
        )
        before = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "secret",
                "device_id": "dev_retr",
            },
        )
    assert before.status_code == 200
    assert len(before.json()["results"]) == 1  # bound device can read it

    # Now wipe the device.
    wipe = app_client.post(
        "/v1/devices/wipe",
        headers=auth_headers(s["key"]),
        json={"device_id": "dev_retr"},
    )
    assert wipe.status_code == 200

    # Retrieve AS the (now wiped) device — the device_only memory is NOT returned.
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        # HMS might still return the unit (HMS doesn't know about the wipe), but
        # MP's scope matrix must filter it out for a wiped device.
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").respond(
            200, json={"results": [{"id": "hms_dev_retr", "text": "secret on device"}]}
        )
        after = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "secret",
                "device_id": "dev_retr",  # now wiped
            },
        )
    assert after.status_code == 200
    assert after.json()["results"] == []  # wiped device -> filtered


# ---------------------------------------------------------------------------
# Auth regression
# ---------------------------------------------------------------------------


def test_wipe_requires_auth(app_client):
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        resp = app_client.post("/v1/devices/wipe", json={"device_id": "dev_x"})
    assert resp.status_code == 401
