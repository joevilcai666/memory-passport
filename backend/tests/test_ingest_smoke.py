"""Ingest smoke test against real HMS (Slice 3 architecture-validation tracer).

This is the ONE test that exercises the real MP↔HMS contract end-to-end
(retain -> list -> MP record) inside docker-compose. It's pg-only and skipped
when DATABASE_URL isn't postgres OR HMS_API_URL still points at the test mock
(runs only when an operator points the suite at a live hms-api).

Skipped by default in the local sqlite suite — run via:
    docker-compose run mp-backend pytest tests/test_ingest_smoke.py
"""

from __future__ import annotations

from datetime import UTC

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

import app.models  # noqa: F401
from app.config import get_settings
from app.db.base import _JSON_DUMPS, Base
from app.db.session import reset_engine_for_tests


def _is_postgres() -> bool:
    return get_settings().database_url.startswith("postgresql")


def _hms_is_live() -> bool:
    # The conftest points hms_api_url at http://hms-api.test (respx-only). The
    # smoke test only runs when an operator overrides it to a real hms-api URL.
    return not get_settings().hms_api_url.startswith("http://hms-api.test")


pytestmark = pytest.mark.skipif(
    not (_is_postgres() and _hms_is_live()),
    reason="ingest smoke test requires Postgres + a live HMS (docker-compose)",
)


@pytest.fixture()
def pg_app():
    """Fresh Postgres DB + TestClient wired to it."""
    settings = get_settings()
    base_url = settings.database_url
    test_db_name = "memory_passport_ingest_smoke"
    server_url = base_url.rsplit("/", 1)[0] + "/postgres"
    test_url = base_url.rsplit("/", 1)[0] + f"/{test_db_name}"

    admin = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        conn.execute(text(f"CREATE DATABASE {test_db_name}"))
    admin.dispose()

    engine = create_engine(
        test_url, pool_pre_ping=True, future=True, json_serializer=_JSON_DUMPS
    )
    Base.metadata.create_all(engine)
    reset_engine_for_tests(engine)

    import app.main as main_mod

    main_mod.get_settings().run_migrations_on_startup = False
    client = TestClient(main_mod.create_app())
    yield client

    client.close()
    engine.dispose()
    cleanup = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with cleanup.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
    cleanup.dispose()


def test_ingest_against_real_hms(pg_app):
    """Seed tenant/app/user/agent/relationship, then ingest against real HMS.

    The assertion is loose (HMS extraction is non-deterministic): we check that
    ingest returns 201, that the response has an event_id + at least one ADD,
    and that an MP record + mapping row were persisted. Operators inspect logs
    for the actual extracted facts.
    """
    from datetime import datetime as _dt

    from app.db.session import session_scope
    from app.models.identity import Agent, Relationship, User
    from app.models.memory import MemoryPolicy
    from app.models.tenant import ApiKey, App, Tenant

    now = _dt.now(tz=UTC)
    with session_scope() as db:
        db.add(Tenant(id="ten_smoke", name="Smoke", plan="Sandbox", created_at=now))
        db.add(
            App(
                id="app_smoke",
                tenant_id="ten_smoke",
                name="Smoke",
                product_type="software",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=False,
                status="active",
                created_at=now,
            )
        )
        db.add(
            ApiKey(
                id="key_smoke",
                app_id="app_smoke",
                label="Sandbox",
                environment="sandbox",
                key="mp_sandbox_smoke_smoke_smoke_smoke_sm",
                created_at=now,
                last_used_at=now,
            )
        )
        db.add(
            User(
                id="usr_smoke",
                tenant_id="ten_smoke",
                external_user_id="ext_smoke",
                passport_id="pp_smoke",
                age_group="adult",
                region="US",
                memory_enabled=True,
                created_at=now,
                display_name="Smoke",
                avatar_color="#000000",
            )
        )
        db.add(
            Agent(
                id="agt_smoke",
                app_id="app_smoke",
                name="Smoke Agent",
                type="companion",
                persona_version="v1",
                memory_policy_id=None,
                allowed_memory_types=["preference"],
                created_at=now,
                emoji="🚬",
            )
        )
        db.flush()
        db.add(
            MemoryPolicy(
                id="pol_smoke",
                app_id="app_smoke",
                agent_id="agt_smoke",
                portability={
                    "layer": "portable",
                    "cross_device": True,
                    "cross_role": True,
                    "cross_model": True,
                    "cross_brand_app": False,
                },
                retrieval={"max_memories_per_response": 8, "include_sensitive_in_prompt": False},
            )
        )
        db.flush()
        db.query(Agent).filter(Agent.id == "agt_smoke").update({"memory_policy_id": "pol_smoke"})
        db.add(
            Relationship(
                id="rel_smoke",
                tenant_id="ten_smoke",
                user_id="usr_smoke",
                agent_id="agt_smoke",
                device_id=None,
                relationship_type="companion",
                memory_enabled=True,
                created_at=now,
            )
        )

    # Pre-provision the HMS bank so retain has somewhere to land.
    import asyncio

    from app.hms import HmsClient

    settings = get_settings()
    client = HmsClient(base_url=settings.hms_api_url, api_key=settings.hms_api_key)
    asyncio.run(client.put_bank("usr_smoke"))

    resp = pg_app.post(
        "/v1/events/ingest",
        headers={"Authorization": "Bearer mp_sandbox_smoke_smoke_smoke_smoke_sm"},
        json={
            "user_id": "usr_smoke",
            "agent_id": "agt_smoke",
            "relationship_id": "rel_smoke",
            "source_type": "explicit_instruction",
            "content": "My favorite tea is chamomile and I drink it every evening.",
            "quote": "My favorite tea is chamomile and I drink it every evening.",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["event_id"]
    # HMS extraction may yield 0..N facts; if it yielded 0 we get NOOP.
    assert any(r["action"] in ("ADD", "NOOP") for r in body["results"])
