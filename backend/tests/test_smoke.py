"""Smoke test — the Slice 1 acceptance flow: seed → GET /v1/health → assert ok.

Runs against Postgres (the seed needs pg_insert). Skipped on sqlite.
"""

from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

import app.models  # noqa: F401
from app.config import get_settings
from app.db.base import _JSON_DUMPS, Base
from app.db.session import reset_engine_for_tests
from tests.service_dependencies import postgres_available

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not postgres_available(),
        reason="smoke test requires a reachable Postgres service",
    ),
]


@pytest.fixture()
def pg_app():
    """Fresh Postgres DB + TestClient wired to it."""
    settings = get_settings()
    base_url = settings.database_url
    test_db_name = "memory_passport_smoke"
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


def test_seed_then_health_reports_all_ok(pg_app):
    """The acceptance smoke test: seed → /v1/health → mp/hms/db all ok."""
    from app.seed.run_seed import seed_mp

    counts = seed_mp()
    assert counts["memory_records"] == 42
    assert counts["users"] == 4

    with respx.mock(base_url="http://hms-api.test") as mock:
        # The app is configured to hit hms-api.test by test config; patch it.
        import app.main as main_mod

        main_mod.get_settings().hms_api_url = "http://hms-api.test"
        main_mod.get_settings().hms_api_key = "test-key"
        mock.get("/health").respond(200, json={"status": "healthy", "database": "connected"})
        resp = pg_app.get("/v1/health")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "mp": "ok",
        "hms": "ok",
        "db": "ok",
        "memory_engine": "demo",
    }
