"""Acceptance tests for async export and the delete-user cascade."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import pytest
import respx

from app.config import get_settings
from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    MemoryScope,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
    PassportStatus,
)
from app.models.export import ExportJob
from app.models.identity import Agent, Relationship, User
from app.models.memory import MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def _memory(memory_id: str):
    now = _now()
    return MemoryRecord(
        id=memory_id,
        tenant_id="ten_data",
        app_id="app_data",
        passport_id="pp_data",
        user_id="usr_data",
        relationship_id="rel_data",
        agent_id="agt_data",
        device_id=None,
        type=MemoryType.PREFERENCE,
        content=f"model-neutral content {memory_id}",
        scope=MemoryScope.RELATIONSHIP_ONLY,
        sensitivity=MemorySensitivity.S1,
        status=MemoryStatus.ACTIVE,
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
            "quote": memory_id,
        },
        valid_from=now,
        expires_at=None,
        version=1,
        supersedes=None,
        last_used_at=None,
        usage_count=0,
        model_provenance={"created_by_model": "model-a", "retrieval_history": []},
    )


@pytest.fixture()
def data_ops_seed(sqlite_db, tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "export_dir", str(tmp_path / "exports"), raising=False)
    monkeypatch.setattr(settings, "export_token_ttl_seconds", 900, raising=False)
    key = "mp_sandbox_data_ops_data_ops_data_ops"
    with session_scope() as db:
        db.add(Tenant(id="ten_data", name="Data", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            App(
                id="app_data",
                tenant_id="ten_data",
                name="Data",
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
                    id="key_data",
                    app_id="app_data",
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=_now(),
                    last_used_at=_now(),
                ),
                User(
                    id="usr_data",
                    tenant_id="ten_data",
                    external_user_id="ext_data",
                    passport_id="pp_data",
                    passport_status=PassportStatus.ACTIVE,
                    passport_deleted_at=None,
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=_now(),
                    display_name="Data Tester",
                    avatar_color="#123456",
                ),
                Agent(
                    id="agt_data",
                    app_id="app_data",
                    name="Data Agent",
                    type="assistant",
                    persona_version="v1",
                    memory_policy_id=None,
                    allowed_memory_types=["preference"],
                    created_at=_now(),
                    emoji="D",
                ),
            ]
        )
        db.flush()
        db.add(
            Relationship(
                id="rel_data",
                tenant_id="ten_data",
                user_id="usr_data",
                agent_id="agt_data",
                device_id=None,
                relationship_type="assistant",
                memory_enabled=True,
                created_at=_now(),
            )
        )
        db.flush()
        for memory in (_memory("mem_data_1"), _memory("mem_data_2")):
            db.add(memory)
            db.flush()
            db.add(
                MemoryRecordHmsUnit(
                    mp_memory_id=memory.id,
                    tenant_id="ten_data",
                    hms_unit_id=f"hms_{memory.id}",
                    hms_bank_id="usr_data",
                    hms_document_id=f"evt_{memory.id}",
                    created_at=_now(),
                )
            )

        db.add(Tenant(id="ten_data_other", name="Other", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            User(
                id="usr_data_other",
                tenant_id="ten_data_other",
                external_user_id="ext_other",
                passport_id="pp_other",
                passport_status=PassportStatus.ACTIVE,
                passport_deleted_at=None,
                age_group="adult",
                region="US",
                memory_enabled=True,
                created_at=_now(),
                display_name="Other",
                avatar_color="#000000",
            )
        )
    return {"key": key}


def test_export_round_trip_is_model_neutral_and_audited(data_ops_seed, app_client):
    headers = _headers(data_ops_seed["key"])
    response = app_client.post("/v1/exports", headers=headers, json={"user_id": "usr_data"})
    assert response.status_code == 202, response.text
    export_id = response.json()["export_id"]
    status = app_client.get(f"/v1/exports/{export_id}", headers=headers)
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "completed"
    assert payload["download_url"]
    download = app_client.get(payload["download_url"], headers=headers)
    assert download.status_code == 200, download.text
    bundle = download.json()
    assert bundle["format"] == "memory-passport/v1"
    assert bundle["user"] == {"id": "usr_data", "passport_id": "pp_data"}
    assert len(bundle["memories"]) == 2
    serialized = json.dumps(bundle).lower()
    assert "embedding" not in serialized
    assert "api_key" not in serialized
    assert "provider" not in serialized
    with session_scope() as db:
        job = db.get(ExportJob, export_id)
        assert job.download_token_hash
        assert "token=" not in (job.artifact_path or "")
        assert db.query(AuditLog).filter(
            AuditLog.action == AuditAction.MEMORY_EXPORTED
        ).count() == 1


def test_download_rejects_wrong_and_expired_tokens(data_ops_seed, app_client):
    headers = _headers(data_ops_seed["key"])
    export_id = app_client.post(
        "/v1/exports", headers=headers, json={"user_id": "usr_data"}
    ).json()["export_id"]
    status = app_client.get(f"/v1/exports/{export_id}", headers=headers).json()
    parts = urlsplit(status["download_url"])
    query = parse_qs(parts.query)
    query["token"] = ["wrong-token"]
    wrong_url = urlunsplit((*parts[:3], urlencode(query, doseq=True), parts.fragment))
    assert app_client.get(wrong_url, headers=headers).status_code == 403
    with session_scope() as db:
        db.get(ExportJob, export_id).download_token_expires_at = _now() - timedelta(seconds=1)
    assert app_client.get(status["download_url"], headers=headers).status_code == 410


def test_export_failure_is_persisted_without_internal_details(
    data_ops_seed, app_client, monkeypatch
):
    def fail_write(*_args, **_kwargs):
        raise OSError("/secret/internal/path is unavailable")

    monkeypatch.setattr("app.services.data_ops._write_export_bundle", fail_write)
    headers = _headers(data_ops_seed["key"])
    export_id = app_client.post(
        "/v1/exports", headers=headers, json={"user_id": "usr_data"}
    ).json()["export_id"]
    status = app_client.get(f"/v1/exports/{export_id}", headers=headers).json()
    assert status["status"] == "failed"
    assert status["error"] == "export failed"
    assert "secret" not in json.dumps(status).lower()


def test_export_token_persists_across_store_reload(data_ops_seed, app_client):
    """The download token must survive a store reload (not process memory).

    Regression for issue #13: the plaintext token used to live in an in-process
    dict, so a second worker or a restart silently lost the download_url. The
    token is now persisted on the ExportJob row, so opening a brand-new session
    (the process-reload proxy) still resolves it.
    """
    headers = _headers(data_ops_seed["key"])
    export_id = app_client.post(
        "/v1/exports", headers=headers, json={"user_id": "usr_data"}
    ).json()["export_id"]

    # The persisted row — not a module-level cache — holds the plaintext token.
    with session_scope() as db:
        job = db.get(ExportJob, export_id)
        assert job.download_token is not None
        assert job.download_token_hash  # verification hash still present

    # download_url is built from the persisted row, so a status poll from a
    # "fresh" session still returns it and the download succeeds.
    status = app_client.get(f"/v1/exports/{export_id}", headers=headers).json()
    assert status["download_url"], "download_url missing after store reload"
    download = app_client.get(status["download_url"], headers=headers)
    assert download.status_code == 200, download.text


def test_export_token_is_one_shot_and_cleared_after_download(
    data_ops_seed, app_client
):
    """A successful download consumes the token: it can't be replayed and the
    status endpoint no longer returns a download_url. See issue #13."""
    headers = _headers(data_ops_seed["key"])
    export_id = app_client.post(
        "/v1/exports", headers=headers, json={"user_id": "usr_data"}
    ).json()["export_id"]
    status = app_client.get(f"/v1/exports/{export_id}", headers=headers).json()
    download_url = status["download_url"]
    assert download_url

    first = app_client.get(download_url, headers=headers)
    assert first.status_code == 200, first.text

    # The plaintext is cleared on the row — one-shot semantics.
    with session_scope() as db:
        assert db.get(ExportJob, export_id).download_token is None

    # A replay of the exact URL now fails: status no longer exposes it and the
    # download itself rejects the (now-cleared) token.
    repeat_status = app_client.get(f"/v1/exports/{export_id}", headers=headers).json()
    assert repeat_status["download_url"] is None
    assert app_client.get(download_url, headers=headers).status_code == 403



def test_delete_user_cascades_and_retrieve_short_circuits_hms(data_ops_seed, app_client):
    headers = _headers(data_ops_seed["key"])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        delete_bank = mock.delete("/v1/default/banks/usr_data").respond(
            200, json={"deleted": True}
        )
        recall = mock.post(url__regex=r"/v1/default/banks/usr_data/memories/recall$").respond(
            500
        )
        deleted = app_client.post(
            "/v1/delete_user", headers=headers, json={"user_id": "usr_data"}
        )
        recalled = app_client.post(
            "/v1/memories/retrieve",
            headers=headers,
            json={
                "user_id": "usr_data",
                "agent_id": "agt_data",
                "relationship_id": "rel_data",
                "query": "anything",
                "model": "test",
            },
        )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["tombstoned_memories"] == 2
    assert delete_bank.call_count == 1
    assert recall.call_count == 0
    assert recalled.status_code == 200
    assert recalled.json()["results"] == []
    listed = app_client.get(
        "/v1/memories?user_id=usr_data&include_deleted=true", headers=headers
    ).json()
    assert {row["status"] for row in listed["items"]} == {"deleted"}
    with session_scope() as db:
        user = db.get(User, "usr_data")
        assert user.passport_status == PassportStatus.DELETED
        assert user.passport_deleted_at is not None
        assert db.query(MemoryRecordHmsUnit).count() == 0
        assert db.query(AuditLog).filter(
            AuditLog.action == AuditAction.USER_DELETED
        ).count() == 1


def test_data_operations_explicitly_forbid_cross_tenant_users(data_ops_seed, app_client):
    headers = _headers(data_ops_seed["key"])
    assert app_client.post(
        "/v1/exports", headers=headers, json={"user_id": "usr_data_other"}
    ).status_code == 403
    assert app_client.post(
        "/v1/delete_user", headers=headers, json={"user_id": "usr_data_other"}
    ).status_code == 403
