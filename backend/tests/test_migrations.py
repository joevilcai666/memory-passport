"""Alembic migration tests — acceptance criterion: upgrade then downgrade clean.

Exercises the actual 0001_initial revision against a throwaway Postgres DB so
we verify every enum/table/index/constraint is created AND dropped without
error (the "Alembic downgrade returns to a clean state" criterion).
"""

from __future__ import annotations

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.config import get_settings
from tests.service_dependencies import postgres_available

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not postgres_available(),
        reason="migration tests require a reachable Postgres service",
    ),
]


@pytest.fixture()
def empty_pg_url():
    """Spin up + tear down a throwaway Postgres database."""
    settings = get_settings()
    base_url = settings.database_url
    db_name = "memory_passport_migtest"
    server_url = base_url.rsplit("/", 1)[0] + "/postgres"
    test_url = base_url.rsplit("/", 1)[0] + f"/{db_name}"

    admin = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        conn.execute(text(f"CREATE DATABASE {db_name}"))
    admin.dispose()

    yield test_url

    cleanup = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with cleanup.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
    cleanup.dispose()


def _alembic_config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_head_creates_all_tables(empty_pg_url):
    """`alembic upgrade head` materialises every table in types.ts."""
    command.upgrade(_alembic_config(empty_pg_url), "head")

    engine = create_engine(empty_pg_url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    engine.dispose()

    expected = {
        "tenants", "apps", "api_keys", "users", "agents", "devices",
        "relationships", "memory_records", "memory_policies", "auto_write_rules",
        "migrations", "audit_logs",
        "team_members", "team_invites",
    }
    assert expected <= tables, f"missing tables: {expected - tables}"


def test_downgrade_base_is_clean(empty_pg_url):
    """`alembic downgrade base` removes every MP table + enum (clean slate)."""
    command.upgrade(_alembic_config(empty_pg_url), "head")
    command.downgrade(_alembic_config(empty_pg_url), "base")

    engine = create_engine(empty_pg_url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    # Only alembic_version should remain.
    remaining_mp = tables - {"alembic_version"}
    assert remaining_mp == set(), f"tables not dropped: {remaining_mp}"

    # And every MP enum type is gone too.
    with engine.connect() as conn:
        enum_rows = conn.execute(
            text("SELECT typname FROM pg_type WHERE typtype='e'").execution_options(
                autocommit=False
            )
        ).fetchall()
    mp_enums = {
        r[0]
        for r in enum_rows
        if r[0]
        in {
            "product_type", "environment", "tenant_plan", "app_status", "data_region",
            "age_group", "agent_type", "relationship_type", "device_status", "memory_type",
            "memory_scope", "memory_sensitivity", "memory_status", "portability_layer",
            "autowrite_action", "migration_status", "old_device_access", "audit_action",
            "team_role", "source_type", "alert_severity",
        }
    }
    engine.dispose()
    assert mp_enums == set(), f"enums not dropped: {mp_enums}"
