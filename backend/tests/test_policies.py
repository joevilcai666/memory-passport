"""Acceptance tests for live, authoritative memory policies."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import respx

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import AuditAction, MemoryScope, MemorySensitivity, MemoryStatus, MemoryType
from app.models.identity import Agent, Relationship, User
from app.models.memory import AutoWriteRule, MemoryPolicy, MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture()
def policy_seed(sqlite_db):
    key = "mp_sandbox_policy_policy_policy_policy"
    with session_scope() as db:
        db.add(Tenant(id="ten_policy", name="Policy", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            App(
                id="app_policy",
                tenant_id="ten_policy",
                name="Policy",
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
                    id="key_policy",
                    app_id="app_policy",
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=_now(),
                    last_used_at=_now(),
                ),
                User(
                    id="usr_policy",
                    tenant_id="ten_policy",
                    external_user_id="ext_policy",
                    passport_id="pp_policy",
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=_now(),
                    display_name="Policy Tester",
                    avatar_color="#123456",
                ),
                Agent(
                    id="agt_policy",
                    app_id="app_policy",
                    name="Policy Agent",
                    type="assistant",
                    persona_version="v1",
                    memory_policy_id=None,
                    allowed_memory_types=["relationship", "boundary"],
                    created_at=_now(),
                    emoji="P",
                ),
            ]
        )
        db.flush()
        db.add(
            Relationship(
                id="rel_policy",
                tenant_id="ten_policy",
                user_id="usr_policy",
                agent_id="agt_policy",
                device_id=None,
                relationship_type="assistant",
                memory_enabled=True,
                created_at=_now(),
            )
        )

        db.add(Tenant(id="ten_other_policy", name="Other", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            App(
                id="app_other_policy",
                tenant_id="ten_other_policy",
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
        db.add(
            Agent(
                id="agt_other_policy",
                app_id="app_other_policy",
                name="Other",
                type="assistant",
                persona_version="v1",
                memory_policy_id=None,
                allowed_memory_types=[],
                created_at=_now(),
                emoji="O",
            )
        )
    return {"key": key}


def _body(**overrides):
    body = {
        "app_id": "app_policy",
        "agent_id": "agt_policy",
        "auto_write_rules": [
            {
                "memory_type": "relationship",
                "action": "auto_write",
                "sensitivity": "S1",
                "ttl_days": None,
            }
        ],
        "portability": {
            "layer": "portable",
            "cross_device": True,
            "cross_role": True,
            "cross_model": True,
            "cross_brand_app": False,
        },
        "retrieval": {"max_memories_per_response": 8},
    }
    body.update(overrides)
    return body


def test_create_then_update_same_pair_persists_every_field(policy_seed, app_client):
    headers = _headers(policy_seed["key"])
    created = app_client.post("/v1/policies", headers=headers, json=_body())
    assert created.status_code == 201, created.text
    first = created.json()
    assert first["retrieval"]["include_sensitive_in_prompt"] is False
    assert first["auto_write_rules"][0]["memory_type"] == "relationship"

    changed = _body(
        auto_write_rules=[
            {
                "memory_type": "boundary",
                "action": "block",
                "sensitivity": "S3",
                "ttl_days": 30,
            }
        ],
        portability={
            "layer": "device_local",
            "cross_device": False,
            "cross_role": False,
            "cross_model": False,
            "cross_brand_app": False,
        },
        retrieval={"max_memories_per_response": 2, "include_sensitive_in_prompt": True},
    )
    updated = app_client.post("/v1/policies", headers=headers, json=changed)
    assert updated.status_code == 200, updated.text
    second = updated.json()
    assert second["id"] == first["id"]
    assert second["portability"]["cross_device"] is False
    assert second["portability"]["cross_role"] is False
    assert second["portability"]["cross_model"] is False
    assert second["retrieval"] == {
        "max_memories_per_response": 2,
        "include_sensitive_in_prompt": True,
    }
    assert second["auto_write_rules"][0]["action"] == "block"
    with session_scope() as db:
        assert db.query(MemoryPolicy).count() == 1
        assert db.query(AutoWriteRule).count() == 1
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.POLICY_CHANGED)
            .count()
            == 2
        )


def test_get_policy_returns_persisted_state_without_writing(policy_seed, app_client):
    headers = _headers(policy_seed["key"])
    created = app_client.post("/v1/policies", headers=headers, json=_body())
    assert created.status_code == 201

    with session_scope() as db:
        audit_count = db.query(AuditLog).count()

    response = app_client.get(
        "/v1/policies?app_id=app_policy&agent_id=agt_policy", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json() == created.json()

    with session_scope() as db:
        assert db.query(AuditLog).count() == audit_count


def test_get_missing_policy_returns_404_without_write(policy_seed, app_client):
    response = app_client.get(
        "/v1/policies?app_id=app_policy&agent_id=agt_policy",
        headers=_headers(policy_seed["key"]),
    )
    assert response.status_code == 404
    with session_scope() as db:
        assert db.query(MemoryPolicy).count() == 0
        assert db.query(AuditLog).count() == 0


def test_cross_brand_is_rejected_without_any_write(policy_seed, app_client):
    body = _body()
    body["portability"]["cross_brand_app"] = True
    response = app_client.post(
        "/v1/policies", headers=_headers(policy_seed["key"]), json=body
    )
    assert response.status_code == 422
    assert "deferred to P2" in response.text
    with session_scope() as db:
        assert db.query(MemoryPolicy).count() == 0
        assert db.query(AuditLog).count() == 0


def test_policy_pair_must_belong_to_calling_tenant(policy_seed, app_client):
    response = app_client.post(
        "/v1/policies",
        headers=_headers(policy_seed["key"]),
        json=_body(app_id="app_other_policy", agent_id="agt_other_policy"),
    )
    assert response.status_code == 404


def test_live_block_rule_prevents_ingest_without_hms_call(policy_seed, app_client):
    body = _body(
        auto_write_rules=[
            {
                "memory_type": "relationship",
                "action": "block",
                "sensitivity": "S1",
                "ttl_days": None,
            }
        ]
    )
    headers = _headers(policy_seed["key"])
    assert app_client.post("/v1/policies", headers=headers, json=body).status_code == 201
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        retain = mock.post(url__regex=r"/v1/default/banks/[^/]+/memories$").respond(500)
        response = app_client.post(
            "/v1/events/ingest",
            headers=headers,
            json={
                "user_id": "usr_policy",
                "agent_id": "agt_policy",
                "relationship_id": "rel_policy",
                "source_type": "chat",
                "content": "do not retain this",
            },
        )
    assert response.status_code == 201, response.text
    assert response.json()["results"][0]["action"] == "BLOCKED"
    assert retain.call_count == 0
    with session_scope() as db:
        assert db.query(MemoryRecord).count() == 0


def _add_sensitive_memories():
    now = _now()
    with session_scope() as db:
        for index in (1, 2):
            memory_id = f"mem_policy_{index}"
            db.add(
                MemoryRecord(
                    id=memory_id,
                    tenant_id="ten_policy",
                    app_id="app_policy",
                    passport_id="pp_policy",
                    user_id="usr_policy",
                    relationship_id="rel_policy",
                    agent_id="agt_policy",
                    device_id=None,
                    type=MemoryType.RELATIONSHIP,
                    content=f"sensitive content {index}",
                    scope=MemoryScope.RELATIONSHIP_ONLY,
                    sensitivity=MemorySensitivity.S2,
                    status=MemoryStatus.ACTIVE,
                    confidence=0.9,
                    portability=_body()["portability"],
                    source={
                        "event_id": f"evt_policy_{index}",
                        "source_type": "chat",
                        "timestamp": now.isoformat(),
                        "quote": f"sensitive content {index}",
                    },
                    valid_from=now,
                    expires_at=None,
                    version=1,
                    supersedes=None,
                    last_used_at=None,
                    usage_count=0,
                    model_provenance={"created_by_model": "test", "retrieval_history": []},
                )
            )
            db.flush()
            db.add(
                MemoryRecordHmsUnit(
                    mp_memory_id=memory_id,
                    tenant_id="ten_policy",
                    hms_unit_id=f"hms_policy_{index}",
                    hms_bank_id="usr_policy",
                    hms_document_id=f"evt_policy_{index}",
                    created_at=now,
                )
            )


def _recall(app_client, headers):
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.post(url__regex=r"/v1/default/banks/usr_policy/memories/recall$").respond(
            200,
            json={
                "results": [
                    {"id": "hms_policy_1", "text": "sensitive content 1"},
                    {"id": "hms_policy_2", "text": "sensitive content 2"},
                ]
            },
        )
        return app_client.post(
            "/v1/memories/retrieve",
            headers=headers,
            json={
                "user_id": "usr_policy",
                "agent_id": "agt_policy",
                "relationship_id": "rel_policy",
                "query": "sensitive",
                "model": "test",
            },
        )


def test_retrieve_reads_live_cap_and_masking_toggle(policy_seed, app_client):
    headers = _headers(policy_seed["key"])
    _add_sensitive_memories()
    masked_policy = _body(
        retrieval={"max_memories_per_response": 1, "include_sensitive_in_prompt": False}
    )
    assert app_client.post("/v1/policies", headers=headers, json=masked_policy).status_code == 201
    masked = _recall(app_client, headers)
    assert masked.status_code == 200
    assert [item["content"] for item in masked.json()["results"]] == ["[redacted]"]

    visible_policy = _body(
        retrieval={"max_memories_per_response": 2, "include_sensitive_in_prompt": True}
    )
    assert app_client.post("/v1/policies", headers=headers, json=visible_policy).status_code == 200
    visible = _recall(app_client, headers)
    assert visible.status_code == 200
    assert [item["content"] for item in visible.json()["results"]] == [
        "sensitive content 1",
        "sensitive content 2",
    ]
