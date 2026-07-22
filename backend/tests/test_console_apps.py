"""Live console app and API-key management contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture()
def console_tenants(sqlite_db):
    luna_key = "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd"
    other_key = "mp_sandbox_other_console_key"
    now = _now()
    with session_scope() as db:
        db.add_all(
            [
                Tenant(id="ten_luna", name="Luna", plan="Sandbox", created_at=now),
                Tenant(id="ten_other", name="Other", plan="Sandbox", created_at=now),
            ]
        )
        db.flush()
        db.add_all(
            [
                App(
                    id="app_luna",
                    tenant_id="ten_luna",
                    name="Luna",
                    product_type="hybrid",
                    environment="sandbox",
                    data_region="us-east-1",
                    show_powered_by=True,
                    status="active",
                    created_at=now,
                ),
                App(
                    id="app_other",
                    tenant_id="ten_other",
                    name="Other",
                    product_type="software",
                    environment="sandbox",
                    data_region="eu-west-1",
                    show_powered_by=False,
                    status="active",
                    created_at=now,
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                ApiKey(
                    id="key_luna",
                    app_id="app_luna",
                    label="Sandbox Default",
                    environment="sandbox",
                    key=luna_key,
                    created_at=now,
                    last_used_at=now,
                ),
                ApiKey(
                    id="key_other",
                    app_id="app_other",
                    label="Other Default",
                    environment="sandbox",
                    key=other_key,
                    created_at=now,
                    last_used_at=now,
                ),
            ]
        )
    return {"luna_key": luna_key, "other_key": other_key}


def test_app_list_and_detail_are_tenant_scoped_and_keys_are_masked(
    console_tenants, app_client
) -> None:
    listed = app_client.get("/v1/apps", headers=_headers(console_tenants["luna_key"]))
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["items"]] == ["app_luna"]
    key = listed.json()["items"][0]["api_keys"][0]
    assert "key" not in key
    assert key["masked_key"].startswith("mp_sandbox_")
    assert key["masked_key"].endswith(console_tenants["luna_key"][-4:])
    assert console_tenants["luna_key"] not in listed.text

    detail = app_client.get(
        "/v1/apps/app_luna", headers=_headers(console_tenants["luna_key"])
    )
    assert detail.status_code == 200
    assert detail.json()["name"] == "Luna"

    hidden = app_client.get(
        "/v1/apps/app_other", headers=_headers(console_tenants["luna_key"])
    )
    assert hidden.status_code == 404


def test_create_key_returns_secret_once_and_persists_masked_key(
    console_tenants, app_client
) -> None:
    created = app_client.post(
        "/v1/apps/app_luna/api-keys",
        headers=_headers(console_tenants["luna_key"]),
        json={"label": "Production Deploy", "environment": "production"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["key"].startswith("mp_live_")

    listed = app_client.get(
        "/v1/apps/app_luna", headers=_headers(console_tenants["luna_key"])
    ).json()
    stored = next(item for item in listed["api_keys"] if item["id"] == body["id"])
    assert "key" not in stored
    assert stored["masked_key"].endswith(body["key"][-4:])
    assert body["key"] not in str(listed)

    with session_scope() as db:
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.API_KEY_CREATED)
            .count()
            == 1
        )


def test_rotate_key_invalidates_old_secret_and_authorizes_replacement(
    console_tenants, app_client
) -> None:
    created = app_client.post(
        "/v1/apps/app_luna/api-keys",
        headers=_headers(console_tenants["luna_key"]),
        json={"label": "Rotating", "environment": "sandbox"},
    ).json()

    rotated = app_client.post(
        f"/v1/apps/app_luna/api-keys/{created['id']}/rotate",
        headers=_headers(console_tenants["luna_key"]),
    )
    assert rotated.status_code == 201, rotated.text
    replacement = rotated.json()
    assert replacement["id"] != created["id"]
    assert replacement["key"] != created["key"]

    assert app_client.get("/v1/apps", headers=_headers(created["key"])).status_code == 401
    assert app_client.get("/v1/apps", headers=_headers(replacement["key"])).status_code == 200

    with session_scope() as db:
        assert db.query(ApiKey).filter(ApiKey.id == created["id"]).one_or_none() is None
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.API_KEY_ROTATED)
            .count()
            == 1
        )


def test_key_mutations_hide_cross_tenant_resources(console_tenants, app_client) -> None:
    create = app_client.post(
        "/v1/apps/app_other/api-keys",
        headers=_headers(console_tenants["luna_key"]),
        json={"label": "Nope", "environment": "sandbox"},
    )
    rotate = app_client.post(
        "/v1/apps/app_other/api-keys/key_other/rotate",
        headers=_headers(console_tenants["luna_key"]),
    )

    assert create.status_code == 404
    assert rotate.status_code == 404
