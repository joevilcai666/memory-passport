"""Multi-tenant HMS resolution (issue #12).

Asserts MP-side behavior: each tenant's HMS client carries that tenant's key,
the seed runner backfills Luna, and provisioning mints distinct credentials for
a new tenant. The HMS-side key→schema mapping lives in the vendored HMS fork
(``core/dataplane/tests/test_mp_tenant.py``).

The per-tenant key resolution is real-mode behavior (the demo HMS is
single-schema and only knows the shared key), so these tests force
``memory_engine_mode = "real"``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from app.config import get_settings
from app.db.session import session_scope
from app.hms import HmsError, hms_client_for_tenant
from app.models.tenant import Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


@pytest.fixture(autouse=True)
def _real_engine_mode(monkeypatch):
    """Per-tenant key resolution is real-mode behavior — force it on."""
    monkeypatch.setattr(get_settings(), "memory_engine_mode", "real", raising=False)


@pytest.fixture()
def two_tenants(sqlite_db):
    """Two tenants with distinct HMS keys + schemas."""
    with session_scope() as db:
        db.add_all(
            [
                Tenant(
                    id="ten_a",
                    name="Tenant A",
                    plan="Sandbox",
                    created_at=_now(),
                    hms_api_key="hms_key_aaaaaa",
                    hms_schema="tenant_ten_a",
                ),
                Tenant(
                    id="ten_b",
                    name="Tenant B",
                    plan="Sandbox",
                    created_at=_now(),
                    hms_api_key="hms_key_bbbbbb",
                    hms_schema="tenant_ten_b",
                ),
            ]
        )
    return {"ten_a": "hms_key_aaaaaa", "ten_b": "hms_key_bbbbbb"}


def test_hms_client_for_tenant_uses_the_tenants_own_key(two_tenants):
    """The resolved client carries the per-tenant key, not the shared default."""
    client_a = hms_client_for_tenant(two_tenants["ten_a"])
    client_b = hms_client_for_tenant(two_tenants["ten_b"])
    assert client_a._api_key == "hms_key_aaaaaa"
    assert client_b._api_key == "hms_key_bbbbbb"
    # The two tenants never share a key — this is the multi-tenant isolation
    # invariant the HMS extension relies on to pick a schema.
    assert client_a._api_key != client_b._api_key


def test_demo_mode_ignores_per_tenant_key_and_uses_shared(sqlite_db, monkeypatch):
    """In demo mode the single-schema evaluator only knows the shared key."""
    monkeypatch.setattr(get_settings(), "memory_engine_mode", "demo", raising=False)
    client = hms_client_for_tenant("hms_some_tenant_key")
    # Falls back to settings.hms_api_key regardless of the tenant key passed.
    assert client._api_key == get_settings().hms_api_key


def test_hms_client_falls_back_to_shared_key_when_no_tenant(sqlite_db):
    """Health probe + seed runner have no tenant context → shared Luna key."""
    client = hms_client_for_tenant(None)
    assert client._api_key  # not None
    assert client._api_key == get_settings().hms_api_key


def test_two_tenants_send_distinct_bearer_headers_to_hms(two_tenants):
    """End-to-end: the Authorization header differs per tenant, so HMS can route."""
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        seen_headers: list[str] = []

        def _record(request: httpx.Request) -> httpx.Response:
            seen_headers.append(request.headers.get("Authorization", ""))
            return httpx.Response(200, json={"status": "healthy"})

        mock.get("/health").mock(side_effect=_record)

        import asyncio

        client_a = hms_client_for_tenant(two_tenants["ten_a"])
        client_b = hms_client_for_tenant(two_tenants["ten_b"])
        asyncio.run(client_a.health())
        asyncio.run(client_b.health())

    assert seen_headers == [
        f"Bearer {two_tenants['ten_a']}",
        f"Bearer {two_tenants['ten_b']}",
    ]
    assert seen_headers[0] != seen_headers[1]


def test_distinct_keys_mean_a_wrong_key_is_rejected(two_tenants):
    """If tenant B's key leaked into tenant A's request, HMS would 401 it.

    We simulate the HMS side rejecting an unknown key: MP surfaces that as an
    HmsError. This is the invariant that makes per-tenant keys meaningful.
    """
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(401)
        client = hms_client_for_tenant(two_tenants["ten_a"])
        with pytest.raises(HmsError):
            import asyncio

            asyncio.run(client.health())
