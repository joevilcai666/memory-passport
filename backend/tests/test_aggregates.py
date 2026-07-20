"""Acceptance tests for read-only audit and usage aggregates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    MemoryScope,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
    UsageOperation,
)
from app.models.identity import Agent, Relationship, User
from app.models.memory import MemoryRecord
from app.models.tenant import ApiKey, App, Tenant
from app.models.usage import UsageEvent

NOW = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _memory(memory_id: str, status=MemoryStatus.ACTIVE):
    return MemoryRecord(
        id=memory_id,
        tenant_id="ten_agg",
        app_id="app_agg",
        passport_id="pp_agg",
        user_id="usr_agg",
        relationship_id="rel_agg",
        agent_id="agt_agg",
        device_id=None,
        type=MemoryType.PREFERENCE,
        content=memory_id,
        scope=MemoryScope.RELATIONSHIP_ONLY,
        sensitivity=MemorySensitivity.S1,
        status=status,
        confidence=0.9,
        portability={"layer": "portable", "cross_brand_app": False},
        source={
            "event_id": f"evt_{memory_id}",
            "source_type": "chat",
            "timestamp": NOW.isoformat(),
            "quote": memory_id,
        },
        valid_from=NOW,
        expires_at=None,
        version=1,
        supersedes=None,
        last_used_at=None,
        usage_count=0,
        model_provenance={"created_by_model": "test", "retrieval_history": []},
    )


@pytest.fixture()
def aggregate_seed(sqlite_db):
    key = "mp_sandbox_aggregate_aggregate_aggregate"
    with session_scope() as db:
        db.add(Tenant(id="ten_agg", name="Aggregate", plan="Sandbox", created_at=NOW))
        db.flush()
        db.add(
            App(
                id="app_agg",
                tenant_id="ten_agg",
                name="Aggregate",
                product_type="software",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=False,
                status="active",
                created_at=NOW,
            )
        )
        db.flush()
        db.add_all(
            [
                ApiKey(
                    id="key_agg",
                    app_id="app_agg",
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=NOW,
                    last_used_at=NOW,
                ),
                User(
                    id="usr_agg",
                    tenant_id="ten_agg",
                    external_user_id="ext_agg",
                    passport_id="pp_agg",
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=NOW,
                    display_name="Aggregate",
                    avatar_color="#123456",
                ),
                Agent(
                    id="agt_agg",
                    app_id="app_agg",
                    name="Aggregate",
                    type="assistant",
                    persona_version="v1",
                    memory_policy_id=None,
                    allowed_memory_types=[],
                    created_at=NOW,
                    emoji="A",
                ),
            ]
        )
        db.flush()
        db.add(
            Relationship(
                id="rel_agg",
                tenant_id="ten_agg",
                user_id="usr_agg",
                agent_id="agt_agg",
                device_id=None,
                relationship_type="assistant",
                memory_enabled=True,
                created_at=NOW,
            )
        )
        db.flush()
        db.add_all([_memory("mem_active"), _memory("mem_deleted", MemoryStatus.DELETED)])
        for index, (action, target, age) in enumerate(
            [
                (AuditAction.MEMORY_CREATED, "mem_active", 4),
                (AuditAction.DEVICE_BOUND, "dev_1", 3),
                (AuditAction.MIGRATION_STARTED, "mig_1", 2),
                (AuditAction.MEMORY_DELETED, "mem_deleted", 1),
            ],
            start=1,
        ):
            db.add(
                AuditLog(
                    id=f"al_agg_{index}",
                    tenant_id="ten_agg",
                    actor="api:key_agg" if index != 4 else "user:usr_agg",
                    action=action,
                    target=target,
                    detail=f"detail {index}",
                    timestamp=NOW - timedelta(days=age),
                )
            )
        for index, operation in enumerate(UsageOperation, start=1):
            db.add(
                UsageEvent(
                    id=f"use_agg_{index}",
                    tenant_id="ten_agg",
                    user_id="usr_agg",
                    operation=operation,
                    timestamp=NOW - timedelta(hours=index),
                )
            )
        db.add(
            UsageEvent(
                id="use_old",
                tenant_id="ten_agg",
                user_id="usr_agg",
                operation=UsageOperation.INGEST,
                timestamp=NOW - timedelta(days=40),
            )
        )

        db.add(Tenant(id="ten_agg_other", name="Other", plan="Sandbox", created_at=NOW))
        db.flush()
        db.add(
            AuditLog(
                id="al_other",
                tenant_id="ten_agg_other",
                actor="other",
                action=AuditAction.MEMORY_CREATED,
                target="secret",
                detail="must not leak",
                timestamp=NOW,
            )
        )
        db.add(
            UsageEvent(
                id="use_other",
                tenant_id="ten_agg_other",
                user_id="usr_other",
                operation=UsageOperation.INGEST,
                timestamp=NOW,
            )
        )
    return {"key": key}


def _counts():
    with session_scope() as db:
        return db.query(AuditLog).count(), db.query(UsageEvent).count()


def test_audit_filters_paginates_newest_first_and_is_tenant_scoped(
    aggregate_seed, app_client
):
    headers = _headers(aggregate_seed["key"])
    response = app_client.get(
        "/v1/audit_logs?page=1&page_size=2", headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    assert [item["id"] for item in body["items"]] == ["al_agg_4", "al_agg_3"]
    assert set(body["items"][0]) == {
        "id",
        "tenant_id",
        "actor",
        "action",
        "target",
        "detail",
        "timestamp",
    }
    filtered = app_client.get(
        "/v1/audit_logs?actor=api:key_agg&action=device.bound&target=dev_1",
        headers=headers,
    ).json()
    assert [item["id"] for item in filtered["items"]] == ["al_agg_2"]
    assert "al_other" not in str(body)


def test_audit_honors_inclusive_iso_bounds(aggregate_seed, app_client):
    since = _iso(NOW - timedelta(days=3))
    until = _iso(NOW - timedelta(days=1))
    body = app_client.get(
        f"/v1/audit_logs?since={since}&until={until}",
        headers=_headers(aggregate_seed["key"]),
    ).json()
    assert [item["id"] for item in body["items"]] == [
        "al_agg_4",
        "al_agg_3",
        "al_agg_2",
    ]


def test_usage_returns_five_dimensions_and_honors_window(aggregate_seed, app_client):
    since = _iso(NOW - timedelta(days=30))
    until = _iso(NOW)
    response = app_client.get(
        f"/v1/usage?since={since}&until={until}",
        headers=_headers(aggregate_seed["key"]),
    )
    assert response.status_code == 200, response.text
    usage = response.json()
    assert set(usage) == {
        "since",
        "until",
        "memory_mau",
        "memory_ops",
        "storage",
        "device_activations",
        "migration_count",
    }
    assert usage["memory_mau"] == 1
    assert usage["memory_ops"] == {"ingest": 1, "retrieve": 1, "update": 1, "delete": 1}
    assert usage["storage"] == 1
    assert usage["device_activations"] == 1
    assert usage["migration_count"] == 1


def test_aggregate_reads_have_no_side_effects_and_reject_reversed_window(
    aggregate_seed, app_client
):
    before = _counts()
    headers = _headers(aggregate_seed["key"])
    assert app_client.get("/v1/audit_logs", headers=headers).status_code == 200
    assert app_client.get("/v1/usage", headers=headers).status_code == 200
    assert _counts() == before
    response = app_client.get(
        f"/v1/usage?since={_iso(NOW)}&until={_iso(NOW - timedelta(days=1))}",
        headers=headers,
    )
    assert response.status_code == 422
