"""Seed runner — ``python -m app.seed.run_seed``.

Upserts the Luna dataset into the MP database (idempotent), then provisions one
empty HMS bank per user (``bank_id == user_id``) via :meth:`HmsClient.put_bank`.

Idempotency: every row is upserted by primary key (``ON CONFLICT DO UPDATE``),
so re-running is safe and deterministic. HMS bank creation is likewise
idempotent (HMS does ``ON CONFLICT DO NOTHING`` internally).

Run inside docker-compose:
    docker-compose exec mp-backend python -m app.seed.run_seed
"""

from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.db.session import session_scope
from app.hms import HmsClient, HmsError
from app.models.audit import AuditLog
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import AutoWriteRule, MemoryPolicy, MemoryRecord
from app.models.migration import Migration
from app.models.tenant import ApiKey, App, Tenant
from app.seed import data as seed_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("seed")


def _upsert_all(db, model, rows: list[dict]) -> int:
    """Upsert a batch of rows by primary key (Postgres ON CONFLICT DO UPDATE).

    Each row is upserted individually so the SET clause can exclude the PK
    regardless of which model is passed. Returns the number of rows written.
    """
    if not rows:
        return 0
    pk_col = list(model.__table__.primary_key.columns)[0].name
    for row in rows:
        stmt = pg_insert(model).values(**row)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in model.__table__.columns
            if c.name != pk_col
        }
        db.execute(stmt.on_conflict_do_update(index_elements=[pk_col], set_=update_cols))
    return len(rows)


def seed_mp() -> dict[str, int]:
    """Seed the MP database. Returns the per-table counts written."""
    counts: dict[str, int] = {}
    with session_scope() as db:
        counts["tenants"] = _upsert_all(db, Tenant, [seed_data.tenant()])
        counts["apps"] = _upsert_all(db, App, [seed_data.app()])
        counts["api_keys"] = _upsert_all(db, ApiKey, seed_data.api_keys())
        counts["users"] = _upsert_all(db, User, seed_data.users())
        counts["devices"] = _upsert_all(db, Device, seed_data.devices())

        # Circular FK between agents.memory_policy_id and memory_policies.agent_id
        # (both NOT NULL). Break the cycle: insert agents with a NULL
        # memory_policy_id, then the policy, then re-upsert agents to set the FK.
        agents_rows = seed_data.agents()
        for row in agents_rows:
            saved_policy_id = row.get("memory_policy_id")
            row["memory_policy_id"] = None
            _upsert_all(db, Agent, [row])
            row["memory_policy_id"] = saved_policy_id

        pol = seed_data.memory_policy()
        counts["memory_policies"] = _upsert_all(db, MemoryPolicy, [pol["policy"]])
        counts["auto_write_rules"] = _upsert_all(db, AutoWriteRule, pol["rules"])

        # Re-upsert agents now that the policy exists (sets memory_policy_id).
        counts["agents"] = _upsert_all(db, Agent, agents_rows)

        counts["relationships"] = _upsert_all(db, Relationship, seed_data.relationships())
        counts["memory_records"] = _upsert_all(db, MemoryRecord, seed_data.memories())
        counts["migrations"] = _upsert_all(db, Migration, [seed_data.migration()])
        counts["audit_logs"] = _upsert_all(db, AuditLog, seed_data.audit_logs())

    return counts


async def seed_hms_banks() -> list[str]:
    """Provision one empty HMS bank per seeded user. Returns the bank_ids.

    ``bank_id == user_id`` per the acceptance criterion. HMS auto-creates the
    bank with defaults on first touch, so an empty PUT body is enough.
    """
    settings = get_settings()
    # Seed runs outside a request/tenant context; it provisions Luna's banks,
    # so use the shared Luna key (the seed data also writes it onto the Luna
    # tenant row so later request-scoped calls resolve the same key).
    client = HmsClient(base_url=settings.hms_api_url, api_key=settings.hms_api_key)
    bank_ids: list[str] = [u["id"] for u in seed_data.users()]

    provisioned: list[str] = []
    for bank_id in bank_ids:
        try:
            await client.put_bank(bank_id)
            provisioned.append(bank_id)
            logger.info("HMS bank provisioned: %s", bank_id)
        except HmsError as exc:
            # Don't abort the whole seed on one HMS failure — report and continue.
            logger.error("HMS bank provisioning failed for %s: %s", bank_id, exc)
    return provisioned


def _verify_counts(counts: dict[str, int]) -> bool:
    """Compare written counts against the expected acceptance counts."""
    ok = True
    for table, expected in seed_data.EXPECTED_COUNTS.items():
        actual = counts.get(table, 0)
        marker = "✓" if actual == expected else "✗"
        if actual != expected:
            ok = False
        print(f"  {marker} {table:20s} {actual:>3} (expected {expected})")
    return ok


async def main() -> int:
    print("==> seeding Memory Passport database…")
    counts = seed_mp()
    ok = _verify_counts(counts)

    print("\n==> provisioning HMS banks (one per user)…")
    provisioned = await seed_hms_banks()
    print(f"  HMS banks provisioned: {len(provisioned)}/{len(seed_data.users())}")

    if not ok:
        print("\n✗ MP counts mismatch — see above", file=sys.stderr)
        return 1
    if len(provisioned) != len(seed_data.users()):
        print("\n✗ some HMS banks failed to provision — see logs above", file=sys.stderr)
        return 2

    print("\n✓ seed complete")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
