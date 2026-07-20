"""Acceptance tests for the Luna v1 -> v2 migration wedge."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    DeviceStatus,
    MemoryScope,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
    MigrationStatus,
)
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.migration import Migration
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def _memory(memory_id: str, *, layer: str, confidence: float, status=MemoryStatus.ACTIVE):
    now = _now()
    return MemoryRecord(
        id=memory_id,
        tenant_id="ten_migration",
        app_id="app_migration",
        passport_id="pp_migration",
        user_id="usr_migration",
        relationship_id="rel_source",
        agent_id="agt_migration",
        device_id="dev_v1",
        type=MemoryType.RELATIONSHIP,
        content=f"content {memory_id}",
        scope=MemoryScope.RELATIONSHIP_ONLY,
        sensitivity=MemorySensitivity.S1,
        status=status,
        confidence=confidence,
        portability={
            "layer": layer,
            "cross_device": layer == "portable",
            "cross_role": True,
            "cross_model": True,
            "cross_brand_app": False,
        },
        source={
            "event_id": f"evt_{memory_id}",
            "source_type": "chat",
            "timestamp": now.isoformat(),
            "quote": memory_id,
        },
        valid_from=now,
        expires_at=None,
        version=1,
        supersedes=None,
        last_used_at=None,
        usage_count=0,
        model_provenance={"created_by_model": "test", "retrieval_history": []},
    )


@pytest.fixture()
def migration_seed(sqlite_db):
    key = "mp_sandbox_migration_migration_migration"
    with session_scope() as db:
        db.add(Tenant(id="ten_migration", name="Migration", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            App(
                id="app_migration",
                tenant_id="ten_migration",
                name="Migration",
                product_type="hybrid",
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
                    id="key_migration",
                    app_id="app_migration",
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=_now(),
                    last_used_at=_now(),
                ),
                User(
                    id="usr_migration",
                    tenant_id="ten_migration",
                    external_user_id="ext_migration",
                    passport_id="pp_migration",
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=_now(),
                    display_name="Mia",
                    avatar_color="#123456",
                ),
                Agent(
                    id="agt_migration",
                    app_id="app_migration",
                    name="Luna",
                    type="robot",
                    persona_version="v1",
                    memory_policy_id=None,
                    allowed_memory_types=["relationship"],
                    created_at=_now(),
                    emoji="L",
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                Device(
                    id="dev_v1",
                    tenant_id="ten_migration",
                    model="Luna",
                    generation="v1",
                    serial_number_hash="v1hash",
                    status=DeviceStatus.BOUND,
                    bound_user_id="usr_migration",
                    last_seen_at=_now(),
                ),
                Device(
                    id="dev_v2",
                    tenant_id="ten_migration",
                    model="Luna",
                    generation="v2",
                    serial_number_hash="v2hash",
                    status=DeviceStatus.REGISTERED,
                    bound_user_id=None,
                    last_seen_at=None,
                ),
            ]
        )
        db.flush()
        db.add(
            Relationship(
                id="rel_source",
                tenant_id="ten_migration",
                user_id="usr_migration",
                agent_id="agt_migration",
                device_id="dev_v1",
                relationship_type="robot",
                memory_enabled=True,
                created_at=_now(),
            )
        )
        db.flush()
        for memory in (
            _memory("mem_013", layer="portable", confidence=0.95),
            _memory("mem_low", layer="portable", confidence=0.69),
            _memory("mem_024", layer="device_local", confidence=0.99),
            _memory(
                "mem_archived",
                layer="portable",
                confidence=0.99,
                status=MemoryStatus.ARCHIVED,
            ),
        ):
            db.add(memory)
            db.flush()
            db.add(
                MemoryRecordHmsUnit(
                    mp_memory_id=memory.id,
                    tenant_id="ten_migration",
                    hms_unit_id=f"hms_{memory.id}",
                    hms_bank_id="usr_migration",
                    hms_document_id=f"evt_{memory.id}",
                    created_at=_now(),
                )
            )

        db.add(Tenant(id="ten_migration_other", name="Other", plan="Sandbox", created_at=_now()))
    return {"key": key}


def _preview(app_client, key):
    return app_client.post(
        "/v1/migrations/preview",
        headers=_headers(key),
        json={
            "user_id": "usr_migration",
            "source_relationship_id": "rel_source",
            "target_relationship_id": "rel_target",
            "source_device_id": "dev_v1",
            "target_device_id": "dev_v2",
        },
    )


def test_preview_exact_buckets_and_is_idempotent(migration_seed, app_client):
    response = _preview(app_client, migration_seed["key"])
    assert response.status_code == 201, response.text
    preview = response.json()
    assert preview["recommended"]["memory_ids"] == ["mem_013"]
    assert preview["needs_review"]["memory_ids"] == ["mem_low"]
    assert preview["not_moved"]["memory_ids"] == ["mem_024"]
    assert preview["counts"] == {"recommended": 1, "needs_review": 1, "not_moved": 1}
    again = _preview(app_client, migration_seed["key"])
    assert again.status_code == 200
    assert again.json()["migration_id"] == preview["migration_id"]


def test_execute_moves_selected_but_never_changes_hms_bank(migration_seed, app_client):
    migration_id = _preview(app_client, migration_seed["key"]).json()["migration_id"]
    response = app_client.post(
        "/v1/migrations/execute",
        headers=_headers(migration_seed["key"]),
        json={
            "migration_id": migration_id,
            "selected_memory_ids": ["mem_013", "mem_low"],
            "old_device_access": "keep",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    with session_scope() as db:
        assert db.get(MemoryRecord, "mem_013").device_id == "dev_v2"
        assert db.get(MemoryRecord, "mem_low").device_id == "dev_v2"
        assert db.get(MemoryRecordHmsUnit, "mem_013").hms_bank_id == "usr_migration"
        assert db.get(Device, "dev_v1").status == DeviceStatus.BOUND
        actions = [row.action for row in db.query(AuditLog).order_by(AuditLog.timestamp)]
        assert actions == [AuditAction.MIGRATION_STARTED, AuditAction.MIGRATION_COMPLETED]


def test_partial_warning_and_total_failure_is_retryable(migration_seed, app_client):
    migration_id = _preview(app_client, migration_seed["key"]).json()["migration_id"]
    failed = app_client.post(
        "/v1/migrations/execute",
        headers=_headers(migration_seed["key"]),
        json={
            "migration_id": migration_id,
            "selected_memory_ids": ["missing"],
            "old_device_access": "keep",
        },
    )
    assert failed.json()["status"] == "failed"
    assert failed.json()["failed_memory_ids"] == ["missing"]

    retried = app_client.post(
        "/v1/migrations/execute",
        headers=_headers(migration_seed["key"]),
        json={
            "migration_id": migration_id,
            "selected_memory_ids": ["mem_013", "missing"],
            "old_device_access": "keep",
        },
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "completed_with_warnings"
    assert retried.json()["failed_memory_ids"] == ["missing"]


def test_remove_old_access_get_and_rollback_round_trip(migration_seed, app_client):
    migration_id = _preview(app_client, migration_seed["key"]).json()["migration_id"]
    executed = app_client.post(
        "/v1/migrations/execute",
        headers=_headers(migration_seed["key"]),
        json={
            "migration_id": migration_id,
            "selected_memory_ids": ["mem_013"],
            "old_device_access": "remove",
        },
    )
    assert executed.status_code == 200
    full = app_client.get(
        f"/v1/migrations/{migration_id}", headers=_headers(migration_seed["key"])
    ).json()
    assert full["selected_memory_ids"] == ["mem_013"]
    assert full["completed_at"] is not None
    with session_scope() as db:
        assert db.get(Device, "dev_v1").status == DeviceStatus.UNBOUND
        assert db.get(Device, "dev_v1").bound_user_id is None

    rolled_back = app_client.post(
        f"/v1/migrations/{migration_id}/rollback",
        headers=_headers(migration_seed["key"]),
    )
    assert rolled_back.status_code == 200, rolled_back.text
    assert rolled_back.json()["status"] == "rolled_back"
    assert rolled_back.json()["rolled_back_at"] is not None
    with session_scope() as db:
        assert db.get(MemoryRecord, "mem_013").device_id == "dev_v1"
        source = db.get(Device, "dev_v1")
        assert source.status == DeviceStatus.BOUND
        assert source.bound_user_id == "usr_migration"
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.MIGRATION_ROLLED_BACK)
            .count()
            == 1
        )


def test_migration_lookup_is_tenant_scoped(migration_seed, app_client):
    migration_id = _preview(app_client, migration_seed["key"]).json()["migration_id"]
    with session_scope() as db:
        row = db.get(Migration, migration_id)
        row.tenant_id = "ten_migration_other"
    response = app_client.get(
        f"/v1/migrations/{migration_id}", headers=_headers(migration_seed["key"])
    )
    assert response.status_code == 404


def test_rollback_before_completion_conflicts(migration_seed, app_client):
    migration_id = _preview(app_client, migration_seed["key"]).json()["migration_id"]
    response = app_client.post(
        f"/v1/migrations/{migration_id}/rollback",
        headers=_headers(migration_seed["key"]),
    )
    assert response.status_code == 409
    with session_scope() as db:
        assert db.get(Migration, migration_id).status == MigrationStatus.PREVIEW
