"""Add per-tenant HMS credentials (api key + schema) to tenants.

Multi-tenant HMS mapping (issue #12): MP stores a distinct HMS API key and a
distinct HMS schema name per tenant, and forwards the key as the Bearer token
when calling HMS. The custom ``MPTenantExtension`` (in the vendored HMS fork)
maps that key to the schema and auto-provisions it on first ingest.

The seeded Luna tenant is backfilled with the legacy shared HMS key
(``HMS_API_TENANT_API_KEY``) and the existing ``tenant_luna`` schema, so the
production data already living under ``tenant_luna`` keeps working unchanged.

Revision ID: 0009_tenant_hms_credentials
Revises: 0008_export_token_plaintext
Create Date: 2026-07-21 00:00:08
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_tenant_hms_credentials"
down_revision: str | None = "0008_export_token_plaintext"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # New audit action for the HMS-credentials provisioning event (issue #12).
    op.execute(
        "ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'tenant.hms_provisioned'"
    )

    # Add the columns nullable first so we can populate existing rows before
    # tightening to NOT NULL (tenants is tiny — one row in V0.1 — but the
    # pattern generalises and keeps the migration safe on a populated DB).
    op.add_column(
        "tenants",
        sa.Column("hms_api_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("hms_schema", sa.String(length=64), nullable=True),
    )

    # Backfill: every existing tenant gets the legacy shared HMS key (so the
    # MP↔HMS calls keep working exactly as before) and the seeded Luna tenant
    # keeps its existing ``tenant_luna`` schema. Any other tenant gets a
    # ``tenant_<id>`` schema name (the convention going forward). The key is
    # read from the env so the migration honours a deployment that already
    # rotated the placeholder; the default matches docker-compose.yml.
    legacy_key = os.getenv("HMS_API_TENANT_API_KEY", "hms_tenant_luna_change_me")
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE tenants SET "
            "  hms_api_key = :key, "
            "  hms_schema = CASE WHEN id = 'ten_luna' THEN 'tenant_luna' "
            "                    ELSE 'tenant_' || id END"
        ),
        {"key": legacy_key},
    )

    # Tighten to NOT NULL + unique on the key.
    op.alter_column("tenants", "hms_api_key", nullable=False)
    op.alter_column("tenants", "hms_schema", nullable=False)
    op.create_unique_constraint("uq_tenants_hms_api_key", "tenants", ["hms_api_key"])


def downgrade() -> None:
    op.drop_constraint("uq_tenants_hms_api_key", "tenants", type_="unique")
    op.drop_column("tenants", "hms_schema")
    op.drop_column("tenants", "hms_api_key")
