"""Pytest fixtures — in-memory sqlite for fast, isolated unit tests.

Production is Postgres; this suite deliberately uses sqlite for the health/auth
tests so they run anywhere (including CI without a DB). The model layer is
multi-dialect (JSONB→JSON, ARRAY→JSON on sqlite; see app/db/base.py).

The seed-count test exercises the real Postgres schema via Alembic when run
inside ``docker-compose run mp-backend pytest`` — it's marked ``@pytest.mark.pg``
and skips automatically when the DATABASE_URL isn't a postgres URL.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers every model on Base.metadata
from app.config import get_settings
from app.db import base as db_base  # noqa: F401 — ensures variant helpers load
from app.db.base import Base
from app.db.session import reset_engine_for_tests
from app.models.tenant import ApiKey, App, Tenant


@pytest.fixture(autouse=True)
def _disable_startup_migrations(monkeypatch) -> None:
    """Never run Alembic during tests — the DB fixture creates the schema."""
    monkeypatch.setattr(get_settings(), "run_migrations_on_startup", False, raising=False)
    # Also patch the cached singleton the app captured at import time.
    import app.main as main_mod

    monkeypatch.setattr(main_mod.get_settings(), "run_migrations_on_startup", False, raising=False)


@pytest.fixture(autouse=True)
def _hms_settings(monkeypatch) -> None:
    """Point HMS at a stable respx-mockable URL for every test.

    Without this the default ``http://localhost:18080`` would be used and respx
    (which mocks ``http://hms-api.test``) wouldn't intercept the call.
    """
    import app.main as main_mod

    settings = main_mod.get_settings()
    monkeypatch.setattr(settings, "hms_api_url", "http://hms-api.test", raising=False)
    monkeypatch.setattr(settings, "hms_api_key", "test-key", raising=False)


@pytest.fixture()
def sqlite_db() -> Iterator[None]:
    """Create a fresh in-memory sqlite DB with all tables, then tear it down."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    reset_engine_for_tests(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def app_client(sqlite_db) -> Iterator[TestClient]:
    """A TestClient against a freshly-seeded-in-memory sqlite app instance."""
    # Re-import to get a fresh app bound to the test engine.
    from app.main import create_app

    client = TestClient(create_app())
    yield client


def _now() -> datetime:
    return datetime.now(tz=UTC)


@pytest.fixture()
def sandbox_key() -> str:
    """The seeded sandbox key — matches src/lib/mock-data.ts."""
    return "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd"


@pytest.fixture()
def seeded_auth_rows(sqlite_db):
    """Insert a minimal tenant/app/api-key row the auth middleware can resolve."""
    from app.db.session import session_scope

    with session_scope() as db:
        db.add(
            Tenant(
                id="ten_luna",
                name="Luna Inc.",
                plan="Sandbox",
                created_at=_now(),
            )
        )
        db.add(
            App(
                id="app_luna",
                tenant_id="ten_luna",
                name="Luna",
                product_type="hybrid",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=True,
                status="active",
                created_at=_now(),
            )
        )
        db.add(
            ApiKey(
                id="key_sb_1",
                app_id="app_luna",
                label="Sandbox — Default",
                environment="sandbox",
                key="mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd",
                created_at=_now(),
                last_used_at=_now(),
            )
        )
