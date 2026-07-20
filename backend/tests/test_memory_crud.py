"""Acceptance tests for Slice 5 memory CRUD and its state machine."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
import respx

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    DeviceStatus,
    MemoryScope,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
    UsageOperation,
)
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.tenant import ApiKey, App, Tenant
from app.models.usage import UsageEvent


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def _record(
    memory_id: str,
    *,
    tenant_id: str = "ten_crud",
    app_id: str = "app_crud",
    user_id: str = "usr_crud",
    relationship_id: str = "rel_crud",
    agent_id: str = "agt_crud",
    device_id: str | None = "dev_crud",
    memory_type: MemoryType = MemoryType.PREFERENCE,
    scope: MemoryScope = MemoryScope.RELATIONSHIP_ONLY,
    status: MemoryStatus = MemoryStatus.ACTIVE,
    content: str = "Mia likes tea",
) -> MemoryRecord:
    now = _now()
    return MemoryRecord(
        id=memory_id,
        tenant_id=tenant_id,
        app_id=app_id,
        passport_id=f"pp_{user_id}",
        user_id=user_id,
        relationship_id=relationship_id,
        agent_id=agent_id,
        device_id=device_id,
        type=memory_type,
        content=content,
        scope=scope,
        sensitivity=MemorySensitivity.S1,
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
            "event_id": f"evt_{memory_id}",
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
        model_provenance={"created_by_model": "test-model", "retrieval_history": []},
    )


def _mapping(memory_id: str, *, tenant_id: str = "ten_crud", user_id: str = "usr_crud"):
    return MemoryRecordHmsUnit(
        mp_memory_id=memory_id,
        tenant_id=tenant_id,
        hms_unit_id=f"hms_{memory_id}",
        hms_bank_id=user_id,
        hms_document_id=f"evt_{memory_id}",
        created_at=_now(),
    )


@pytest.fixture()
def crud_seed(sqlite_db):
    key = "mp_sandbox_crud_crud_crud_crud_crud"
    with session_scope() as db:
        db.add(Tenant(id="ten_crud", name="CRUD Co", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            App(
                id="app_crud",
                tenant_id="ten_crud",
                name="CRUD",
                product_type="software",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=False,
                status="active",
                created_at=_now(),
            )
        )
        db.flush()
        db.add_all(
            [
                ApiKey(
                    id="key_crud",
                    app_id="app_crud",
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=_now(),
                    last_used_at=_now(),
                ),
                User(
                    id="usr_crud",
                    tenant_id="ten_crud",
                    external_user_id="ext_crud",
                    passport_id="pp_usr_crud",
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=_now(),
                    display_name="CRUD Tester",
                    avatar_color="#123456",
                ),
                Agent(
                    id="agt_crud",
                    app_id="app_crud",
                    name="CRUD Agent",
                    type="assistant",
                    persona_version="v1",
                    memory_policy_id=None,
                    allowed_memory_types=["preference"],
                    created_at=_now(),
                    emoji="C",
                ),
                Device(
                    id="dev_crud",
                    tenant_id="ten_crud",
                    model="test",
                    generation="1",
                    serial_number_hash="hash-crud",
                    status=DeviceStatus.BOUND,
                    bound_user_id="usr_crud",
                    last_seen_at=_now(),
                ),
            ]
        )
        db.flush()
        db.add(
            Relationship(
                id="rel_crud",
                tenant_id="ten_crud",
                user_id="usr_crud",
                agent_id="agt_crud",
                device_id="dev_crud",
                relationship_type="assistant",
                memory_enabled=True,
                created_at=_now(),
            )
        )
        db.flush()
        for record in (
            _record("mem_active"),
            _record("mem_second", content="Mia likes coffee"),
            _record("mem_deleted", status=MemoryStatus.DELETED),
        ):
            db.add(record)
            db.flush()
            db.add(_mapping(record.id))

        db.add(Tenant(id="ten_other", name="Other", plan="Sandbox", created_at=_now()))
        db.flush()
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
        db.flush()
        db.add_all(
            [
                User(
                    id="usr_other",
                    tenant_id="ten_other",
                    external_user_id="ext_other",
                    passport_id="pp_usr_other",
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=_now(),
                    display_name="Other",
                    avatar_color="#000000",
                ),
                Agent(
                    id="agt_other",
                    app_id="app_other",
                    name="Other",
                    type="assistant",
                    persona_version="v1",
                    memory_policy_id=None,
                    allowed_memory_types=[],
                    created_at=_now(),
                    emoji="O",
                ),
            ]
        )
        db.flush()
        db.add(
            Relationship(
                id="rel_other",
                tenant_id="ten_other",
                user_id="usr_other",
                agent_id="agt_other",
                device_id=None,
                relationship_type="assistant",
                memory_enabled=True,
                created_at=_now(),
            )
        )
        db.flush()
        db.add(
            _record(
                "mem_other",
                tenant_id="ten_other",
                app_id="app_other",
                user_id="usr_other",
                relationship_id="rel_other",
                agent_id="agt_other",
                device_id=None,
            )
        )
    return {"key": key}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("user_id=usr_crud", 2),
        ("type=preference", 2),
        ("status=active", 2),
        ("scope=relationship_only", 2),
        ("relationship_id=rel_crud", 2),
        ("agent_id=agt_crud", 2),
        ("device_id=dev_crud", 2),
    ],
)
def test_list_filters_and_excludes_deleted(crud_seed, app_client, query, expected):
    response = app_client.get(
        f"/v1/memories?{query}&page=1&page_size=10",
        headers=_headers(crud_seed["key"]),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == expected
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert {item["id"] for item in payload["items"]} == {"mem_active", "mem_second"}
    assert payload["items"][0]["tenant_id"] == "ten_crud"


def test_list_pagination_and_include_deleted(crud_seed, app_client):
    page = app_client.get(
        "/v1/memories?page=2&page_size=1&include_deleted=true",
        headers=_headers(crud_seed["key"]),
    ).json()
    assert page["total"] == 3
    assert page["pages"] == 3
    assert len(page["items"]) == 1


def _mock_edit_hms(*, unit_id: str = "hms_edited", content: str = "Mia prefers green tea"):
    captured: dict[str, str] = {}

    def retain(request):
        captured["document_id"] = json.loads(request.content)["items"][0]["document_id"]
        return respx.MockResponse(200, json={"success": True, "items_count": 1})

    def listing(_request):
        return respx.MockResponse(
            200,
            json={
                "items": [
                    {
                        "id": unit_id,
                        "text": content,
                        "document_id": captured["document_id"],
                        "tags": ["rel:rel_crud", "scope:relationship_only"],
                    }
                ],
                "total": 1,
                "limit": 100,
                "offset": 0,
            },
        )

    mock = respx.mock(base_url="http://hms-api.test", assert_all_called=False)
    mock.post(url__regex=r"/v1/default/banks/usr_crud/memories$").mock(side_effect=retain)
    mock.get(url__regex=r"/v1/default/banks/usr_crud/memories/list.*").mock(
        side_effect=listing
    )
    mock.delete(url__regex=r"/v1/default/banks/usr_crud/documents/.*").respond(
        200, json={"deleted": True}
    )
    return mock


def test_content_edit_creates_version_archives_old_and_audits(crud_seed, app_client):
    with _mock_edit_hms():
        response = app_client.patch(
            "/v1/memories/mem_active",
            headers=_headers(crud_seed["key"]),
            json={"content": "Mia prefers green tea"},
        )
    assert response.status_code == 200, response.text
    edited = response.json()
    assert edited["id"] != "mem_active"
    assert edited["content"] == "Mia prefers green tea"
    assert edited["status"] == "active"
    assert edited["version"] == 2
    assert edited["supersedes"] == "mem_active"

    with session_scope() as db:
        assert db.get(MemoryRecord, "mem_active").status == MemoryStatus.ARCHIVED
        assert db.get(MemoryRecordHmsUnit, "mem_active") is None
        mapping = db.get(MemoryRecordHmsUnit, edited["id"])
        assert mapping.hms_unit_id == "hms_edited"
        audit = db.query(AuditLog).filter(AuditLog.target == edited["id"]).one()
        assert audit.action == AuditAction.MEMORY_EDITED
        assert db.query(UsageEvent).one().operation == UsageOperation.UPDATE


def test_two_edits_preserve_the_complete_supersedes_chain(crud_seed, app_client):
    headers = _headers(crud_seed["key"])
    with _mock_edit_hms(content="version two"):
        version_two = app_client.patch(
            "/v1/memories/mem_active", headers=headers, json={"content": "version two"}
        ).json()
    with _mock_edit_hms(unit_id="hms_edited_twice", content="version three"):
        response = app_client.patch(
            f"/v1/memories/{version_two['id']}",
            headers=headers,
            json={"content": "version three"},
        )
    assert response.status_code == 200, response.text
    version_three = response.json()
    assert version_three["version"] == 3
    assert version_three["supersedes"] == version_two["id"]
    with session_scope() as db:
        assert db.get(MemoryRecord, version_two["id"]).supersedes == "mem_active"
        assert db.get(MemoryRecord, version_two["id"]).status == MemoryStatus.ARCHIVED


@pytest.mark.parametrize(
    ("initial", "target"),
    [
        (MemoryStatus.CANDIDATE, MemoryStatus.ACTIVE),
        (MemoryStatus.CANDIDATE, MemoryStatus.NEEDS_REVIEW),
        (MemoryStatus.ACTIVE, MemoryStatus.ARCHIVED),
        (MemoryStatus.ACTIVE, MemoryStatus.NEEDS_REVIEW),
        (MemoryStatus.ACTIVE, MemoryStatus.DELETED),
        (MemoryStatus.ACTIVE, MemoryStatus.EXPIRED),
        (MemoryStatus.ACTIVE, MemoryStatus.FLAGGED_WRONG),
    ],
)
def test_every_legal_status_transition(crud_seed, app_client, initial, target):
    with session_scope() as db:
        record = db.get(MemoryRecord, "mem_active")
        record.status = initial

    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.patch(url__regex=r"/v1/default/banks/usr_crud/documents/.*").respond(
            200, json={"updated": True}
        )
        mock.delete(url__regex=r"/v1/default/banks/usr_crud/documents/.*").respond(
            200, json={"deleted": True}
        )
        response = app_client.patch(
            "/v1/memories/mem_active",
            headers=_headers(crud_seed["key"]),
            json={"status": target.value},
        )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == target.value


_LEGAL_TRANSITIONS = {
    (MemoryStatus.CANDIDATE, MemoryStatus.ACTIVE),
    (MemoryStatus.CANDIDATE, MemoryStatus.NEEDS_REVIEW),
    (MemoryStatus.ACTIVE, MemoryStatus.ARCHIVED),
    (MemoryStatus.ACTIVE, MemoryStatus.NEEDS_REVIEW),
    (MemoryStatus.ACTIVE, MemoryStatus.DELETED),
    (MemoryStatus.ACTIVE, MemoryStatus.EXPIRED),
    (MemoryStatus.ACTIVE, MemoryStatus.FLAGGED_WRONG),
}


@pytest.mark.parametrize(
    ("initial", "target"),
    [
        (initial, target)
        for initial in MemoryStatus
        for target in MemoryStatus
        if initial != target and (initial, target) not in _LEGAL_TRANSITIONS
    ],
)
def test_illegal_status_transition_names_both_states(crud_seed, app_client, initial, target):
    with session_scope() as db:
        db.get(MemoryRecord, "mem_active").status = initial
    response = app_client.patch(
        "/v1/memories/mem_active",
        headers=_headers(crud_seed["key"]),
        json={"status": target.value},
    )
    assert response.status_code == 409
    assert initial.value in response.text
    assert target.value in response.text


def test_delete_is_tombstone_removes_mapping_and_is_not_retrieved(crud_seed, app_client):
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.delete("/v1/default/banks/usr_crud/documents/evt_mem_active").respond(
            200, json={"deleted": True}
        )
        response = app_client.delete(
            "/v1/memories/mem_active", headers=_headers(crud_seed["key"])
        )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "deleted"
    with session_scope() as db:
        assert db.get(MemoryRecord, "mem_active") is not None
        assert db.get(MemoryRecordHmsUnit, "mem_active") is None
        audit = db.query(AuditLog).filter(AuditLog.target == "mem_active").one()
        assert audit.action == AuditAction.MEMORY_DELETED
        assert db.query(UsageEvent).one().operation == UsageOperation.DELETE


def test_cross_tenant_mutations_are_not_found(crud_seed, app_client):
    response = app_client.patch(
        "/v1/memories/mem_other",
        headers=_headers(crud_seed["key"]),
        json={"status": "archived"},
    )
    assert response.status_code == 404
    assert app_client.delete(
        "/v1/memories/mem_other", headers=_headers(crud_seed["key"])
    ).status_code == 404


def test_hms_failure_rolls_back_content_edit(crud_seed, app_client):
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.post(url__regex=r"/v1/default/banks/usr_crud/memories$").respond(503)
        response = app_client.patch(
            "/v1/memories/mem_active",
            headers=_headers(crud_seed["key"]),
            json={"content": "must not persist"},
        )
    assert response.status_code == 502
    with session_scope() as db:
        record = db.get(MemoryRecord, "mem_active")
        assert record.status == MemoryStatus.ACTIVE
        assert db.query(MemoryRecord).filter(MemoryRecord.supersedes == "mem_active").count() == 0


def test_patch_requires_exactly_one_change(crud_seed, app_client):
    headers = _headers(crud_seed["key"])
    assert app_client.patch("/v1/memories/mem_active", headers=headers, json={}).status_code == 422
    assert app_client.patch(
        "/v1/memories/mem_active",
        headers=headers,
        json={"content": "new", "status": "archived"},
    ).status_code == 422
