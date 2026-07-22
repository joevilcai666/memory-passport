"""Consent persistence and enforcement tests.

The user-level memory switch is authoritative: state changes are persisted and
audited, while disabled users cannot ingest or retrieve memory and must be
rejected before Memory Passport contacts HMS.
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


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture()
def consent_rows(sqlite_db):
    key_a = "mp_sandbox_consent_consent_consent_a"
    key_b = "mp_sandbox_consent_consent_consent_b"

    with session_scope() as db:
        for tenant_id, app_id, key_id, key in (
            ("ten_consent_a", "app_consent_a", "key_consent_a", key_a),
            ("ten_consent_b", "app_consent_b", "key_consent_b", key_b),
        ):
            db.add(
                Tenant(
                    id=tenant_id,
                    name=tenant_id,
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
                    id=key_id,
                    app_id=app_id,
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=_now(),
                    last_used_at=_now(),
                )
            )

        db.add_all(
            [
                User(
                    id="usr_consent_a",
                    tenant_id="ten_consent_a",
                    external_user_id="external_a",
                    passport_id="pp_consent_a",
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=_now(),
                    display_name="Consent A",
                    avatar_color="#6366f1",
                ),
                User(
                    id="usr_consent_b",
                    tenant_id="ten_consent_b",
                    external_user_id="external_b",
                    passport_id="pp_consent_b",
                    age_group="adult",
                    region="US",
                    memory_enabled=True,
                    created_at=_now(),
                    display_name="Consent B",
                    avatar_color="#6366f1",
                ),
            ]
        )

    return {"key_a": key_a, "key_b": key_b}


def test_consent_patch_persists_explicit_values_and_is_idempotent(
    consent_rows, app_client
):
    headers = _auth(consent_rows["key_a"])

    disabled = app_client.patch(
        "/v1/users/usr_consent_a/consent",
        headers=headers,
        json={"memory_enabled": False},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["memory_enabled"] is False

    with session_scope() as db:
        user = db.get(User, "usr_consent_a")
        assert user is not None and user.memory_enabled is False
        audits = (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.USER_CONSENT_CHANGED)
            .all()
        )
        assert len(audits) == 1
        assert audits[0].tenant_id == "ten_consent_a"
        assert audits[0].actor == "api:key_consent_a"
        assert audits[0].target == "usr_consent_a"

    repeated = app_client.patch(
        "/v1/users/usr_consent_a/consent",
        headers=headers,
        json={"memory_enabled": False},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["memory_enabled"] is False
    with session_scope() as db:
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.USER_CONSENT_CHANGED)
            .count()
            == 1
        )

    enabled = app_client.patch(
        "/v1/users/usr_consent_a/consent",
        headers=headers,
        json={"memory_enabled": True},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["memory_enabled"] is True
    with session_scope() as db:
        assert db.get(User, "usr_consent_a").memory_enabled is True
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.USER_CONSENT_CHANGED)
            .count()
            == 2
        )


def test_consent_patch_hides_cross_tenant_user(consent_rows, app_client):
    response = app_client.patch(
        "/v1/users/usr_consent_b/consent",
        headers=_auth(consent_rows["key_a"]),
        json={"memory_enabled": False},
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"]["code"] == "not_found"


def test_disabled_user_cannot_ingest_and_hms_is_not_called(consent_rows, app_client):
    headers = _auth(consent_rows["key_a"])
    patch = app_client.patch(
        "/v1/users/usr_consent_a/consent",
        headers=headers,
        json={"memory_enabled": False},
    )
    assert patch.status_code == 200, patch.text

    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        retain = mock.post(url__regex=r"/v1/default/banks/[^/]+/memories$").respond(
            200, json={"success": True}
        )
        response = app_client.post(
            "/v1/events/ingest",
            headers=headers,
            json={
                "user_id": "usr_consent_a",
                "agent_id": "agt_should_not_be_loaded",
                "relationship_id": "rel_should_not_be_loaded",
                "source_type": "chat",
                "content": "This must not be retained.",
            },
        )

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "memory_disabled"
    assert retain.call_count == 0


def test_disabled_user_cannot_retrieve_and_hms_is_not_called(
    consent_rows, app_client
):
    headers = _auth(consent_rows["key_a"])
    patch = app_client.patch(
        "/v1/users/usr_consent_a/consent",
        headers=headers,
        json={"memory_enabled": False},
    )
    assert patch.status_code == 200, patch.text

    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        recall = mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").respond(
            200, json={"results": []}
        )
        response = app_client.post(
            "/v1/memories/retrieve",
            headers=headers,
            json={
                "user_id": "usr_consent_a",
                "agent_id": "agt_should_not_be_loaded",
                "relationship_id": "rel_should_not_be_loaded",
                "query": "Anything",
                "model": "test-model",
            },
        )

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "memory_disabled"
    assert recall.call_count == 0
