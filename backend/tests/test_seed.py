"""Seed-count tests — the acceptance criterion on Luna dataset shape.

These run against Postgres (the seed uses ``pg_insert`` / ``ON CONFLICT``).
When the test DATABASE_URL isn't postgres (e.g. running locally on sqlite),
the tests are skipped — ``make test`` runs them inside docker-compose against
the real Postgres, which is where this acceptance check belongs.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

import app.models  # noqa: F401
from app.config import get_settings
from app.db.base import _JSON_DUMPS, Base
from app.db.session import reset_engine_for_tests
from app.models.identity import User
from app.models.team import TeamMember
from app.seed import data as seed_data
from tests.service_dependencies import postgres_available

pytestmark = pytest.mark.postgres

pg_only = pytest.mark.skipif(
    not postgres_available(),
    reason="seed-count tests require a reachable Postgres service",
)


@pytest.fixture()
def fresh_pg_db():
    """Create a throwaway Postgres DB for one test, drop it after."""
    settings = get_settings()
    base_url = settings.database_url
    test_db_name = "memory_passport_test"

    # Connect to the server (maintenance DB) with AUTOCOMMIT so CREATE/DROP
    # DATABASE work outside a transaction.
    server_url = base_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        conn.execute(text(f"CREATE DATABASE {test_db_name}"))
    admin_engine.dispose()

    # Point a fresh engine at the new DB and build the schema from metadata.
    test_url = base_url.rsplit("/", 1)[0] + f"/{test_db_name}"
    schema_engine = create_engine(
        test_url, pool_pre_ping=True, future=True, json_serializer=_JSON_DUMPS
    )
    Base.metadata.create_all(schema_engine)
    reset_engine_for_tests(schema_engine)

    yield

    schema_engine.dispose()
    cleanup = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with cleanup.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
    cleanup.dispose()


@pg_only
def test_seed_mp_counts_match_acceptance_criteria(fresh_pg_db):
    """Seed produces exactly the counts listed in the issue + EXPECTED_COUNTS."""
    from app.seed.run_seed import seed_mp

    counts = seed_mp()

    for table, expected in seed_data.EXPECTED_COUNTS.items():
        assert counts[table] == expected, f"{table}: {counts[table]} != {expected}"


@pg_only
def test_seed_luna_tenant_backfilled_with_legacy_hms_credentials(fresh_pg_db):
    """The Luna tenant keeps the shared HMS key + the tenant_luna schema (issue #12 back-compat)."""
    import os

    from app.db.session import session_scope
    from app.models.tenant import Tenant
    from app.seed.run_seed import seed_mp

    seed_mp()
    expected_key = os.getenv("HMS_API_TENANT_API_KEY", "hms_tenant_luna_change_me")
    with session_scope() as db:
        luna = db.get(Tenant, seed_data.TENANT_ID)
        assert luna is not None
        assert luna.hms_api_key == expected_key
        assert luna.hms_schema == "tenant_luna"


@pg_only
def test_seed_mp_is_idempotent(fresh_pg_db):
    """Re-running seed doesn't duplicate rows — counts stay constant."""
    from app.seed.run_seed import seed_mp

    first = seed_mp()
    second = seed_mp()
    assert first == second


@pg_only
def test_seed_users_are_the_four_expected(fresh_pg_db):
    """The 4 seeded users are mia + alex + sam + jordan."""
    from app.db.session import session_scope
    from app.seed.run_seed import seed_mp

    seed_mp()
    with session_scope() as db:
        ids = {u.id for u in db.query(User).all()}
    assert ids == {"usr_mia", "usr_alex", "usr_sam", "usr_jordan"}


@pg_only
def test_seed_team_members_match_console_contract(fresh_pg_db):
    """Seeded team is persisted with all three V0.1 roles."""
    from app.db.session import session_scope
    from app.seed.run_seed import seed_mp

    seed_mp()
    with session_scope() as db:
        members = db.query(TeamMember).order_by(TeamMember.id).all()

    assert [member.email for member in members] == [
        "mia@luna.inc",
        "dev@luna.inc",
        "sara@luna.inc",
    ]
    assert {member.role.value for member in members} == {"Owner", "Admin", "Support"}


@pg_only
def test_seed_memory_field_shapes_match_memory_record(fresh_pg_db):
    """Every memory row round-trips the full MemoryRecord shape."""
    from app.db.session import session_scope
    from app.models.memory import MemoryRecord
    from app.seed.run_seed import seed_mp

    seed_mp()
    with session_scope() as db:
        rows = db.query(MemoryRecord).all()
        assert len(rows) == 42
        for m in rows:
            # Required scalar fields.
            assert m.id and m.tenant_id and m.app_id and m.passport_id
            assert m.user_id and m.relationship_id and m.agent_id
            assert m.type and m.scope and m.sensitivity and m.status
            assert 0.0 <= m.confidence <= 1.0
            # JSONB composites have the expected keys.
            assert set(m.portability) == {
                "layer",
                "cross_device",
                "cross_role",
                "cross_model",
                "cross_brand_app",
            }
            assert {"event_id", "source_type", "timestamp", "quote"} <= set(m.source)
            assert "created_by_model" in m.model_provenance
            assert "retrieval_history" in m.model_provenance


@pg_only
def test_migration_seeded_in_preview_status(fresh_pg_db):
    """mig_001 is seeded with status=preview (the wedge is mid-preview)."""
    from app.db.session import session_scope
    from app.models.migration import Migration
    from app.seed.run_seed import seed_mp

    seed_mp()
    with session_scope() as db:
        mig = db.query(Migration).one()
    assert mig.id == "mig_001"
    assert mig.status.value == "preview"
    assert mig.source_device_id == "dev_luna_v1"
    assert mig.target_device_id == "dev_luna_v2"
