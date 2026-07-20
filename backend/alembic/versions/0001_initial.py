"""Initial MP schema — mirrors src/lib/types.ts 1:1.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-20 00:00:00

Every Postgres enum type is declared explicitly so `downgrade base` drops them
cleanly. Tables are created in dependency order; downgrade reverses it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_enum(name: str, values: tuple[str, ...]) -> None:
    """Create a Postgres enum type idempotently.

    Using raw SQL via ``op.execute`` is more robust than ``sa.Enum().create()``
    in Alembic online mode: the latter can emit ``CREATE TYPE x AS ENUM ()``
    (empty) when checkfirst interacts badly with NullPool, and isn't properly
    idempotent across partial runs. DO blocks make this safe to re-run.
    """
    vals = ", ".join(f"'{v}'" for v in values)
    op.execute(f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({vals}); EXCEPTION WHEN duplicate_object THEN NULL; END $$")


def upgrade() -> None:
    # ---- Enum types ------------------------------------------------------
    # Declared up-front so table creation can reference them by name. Idempotent
    # via DO/EXCEPTION so re-runs (partial upgrades) don't fail.
    _create_enum("product_type", ("software", "hardware", "hybrid"))
    _create_enum("environment", ("sandbox", "production"))
    _create_enum("tenant_plan", ("Sandbox", "Growth", "Enterprise"))
    _create_enum("app_status", ("active", "paused"))
    _create_enum("data_region", ("us-east-1", "eu-west-1", "ap-southeast-1"))
    _create_enum("age_group", ("adult", "minor", "unknown"))
    _create_enum("agent_type", ("character", "companion", "pet", "robot", "assistant"))
    _create_enum("relationship_type", ("companion", "pet", "robot", "assistant"))
    _create_enum("device_status", ("registered", "bound", "unbound", "wiped"))
    _create_enum("memory_type", ("profile", "preference", "boundary", "relationship", "event", "task"))
    _create_enum(
        "memory_scope",
        ("user_global", "relationship_only", "agent_only", "device_only", "private", "blocked"),
    )
    _create_enum("memory_sensitivity", ("S0", "S1", "S2", "S3"))
    _create_enum(
        "memory_status",
        ("candidate", "active", "archived", "needs_review", "deleted", "expired", "flagged_wrong"),
    )
    _create_enum("portability_layer", ("portable", "device_local"))
    _create_enum("autowrite_action", ("auto_write", "confirm", "block"))
    _create_enum(
        "migration_status",
        (
            "draft",
            "preview",
            "confirmed",
            "running",
            "completed",
            "completed_with_warnings",
            "failed",
        ),
    )
    _create_enum("old_device_access", ("keep", "remove"))
    _create_enum(
        "audit_action",
        (
            "memory.created",
            "memory.deleted",
            "memory.edited",
            "memory.viewed",
            "policy.changed",
            "device.bound",
            "device.unbound",
            "migration.completed",
            "migration.started",
            "memory.exported",
        ),
    )
    _create_enum("team_role", ("Owner", "Admin", "Support"))
    _create_enum(
        "source_type",
        ("chat", "voice", "setup", "explicit_instruction", "robot_event", "app_event"),
    )
    _create_enum("alert_severity", ("warning", "error", "info"))

    # ---- Tables (dependency order) ---------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan", PG_ENUM(name="tenant_plan", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "apps",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("product_type", PG_ENUM(name="product_type", create_type=False), nullable=False),
        sa.Column("environment", PG_ENUM(name="environment", create_type=False), nullable=False),
        sa.Column("data_region", PG_ENUM(name="data_region", create_type=False), nullable=False),
        sa.Column("show_powered_by", sa.Boolean(), nullable=False),
        sa.Column("status", PG_ENUM(name="app_status", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_apps_tenant_id", "apps", ["tenant_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("passport_id", sa.String(64), nullable=False),
        sa.Column("age_group", PG_ENUM(name="age_group", create_type=False), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("memory_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("avatar_color", sa.String(32), nullable=False),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_passport_id", "users", ["passport_id"])

    op.create_table(
        "devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("generation", sa.String(32), nullable=False),
        sa.Column("serial_number_hash", sa.String(128), nullable=False),
        sa.Column("status", PG_ENUM(name="device_status", create_type=False), nullable=False),
        sa.Column("bound_user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_devices_tenant_id", "devices", ["tenant_id"])
    op.create_index("ix_devices_bound_user_id", "devices", ["bound_user_id"])

    # NOTE: memory_policies.agent_id -> agents.id forms a circular FK with
    # agents.memory_policy_id -> memory_policies.id. Create the table first
    # WITHOUT the agent_id FK, then add the constraint after `agents` exists.
    op.create_table(
        "memory_policies",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("app_id", sa.String(64), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("portability", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retrieval", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_memory_policies_app_id", "memory_policies", ["app_id"])
    op.create_index("ix_memory_policies_agent_id", "memory_policies", ["agent_id"])

    op.create_table(
        "agents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("app_id", sa.String(64), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", PG_ENUM(name="agent_type", create_type=False), nullable=False),
        sa.Column("persona_version", sa.String(64), nullable=False),
        sa.Column(
            "memory_policy_id",
            sa.String(64),
            sa.ForeignKey("memory_policies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("allowed_memory_types", sa.dialects.postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("emoji", sa.String(16), nullable=False),
    )
    op.create_index("ix_agents_app_id", "agents", ["app_id"])
    op.create_index("ix_agents_memory_policy_id", "agents", ["memory_policy_id"])

    # Now that both tables exist, close the circular FK on memory_policies.agent_id.
    op.create_foreign_key(
        "fk_memory_policies_agent_id_agents",
        "memory_policies",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "auto_write_rules",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "policy_id",
            sa.String(64),
            sa.ForeignKey("memory_policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("memory_type", PG_ENUM(name="memory_type", create_type=False), nullable=False),
        sa.Column("action", PG_ENUM(name="autowrite_action", create_type=False), nullable=False),
        sa.Column("sensitivity", PG_ENUM(name="memory_sensitivity", create_type=False), nullable=False),
        sa.Column("ttl_days", sa.Integer(), nullable=True),
    )
    op.create_index("ix_auto_write_rules_policy_id", "auto_write_rules", ["policy_id"])

    op.create_table(
        "relationships",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("relationship_type", PG_ENUM(name="relationship_type", create_type=False), nullable=False),
        sa.Column("memory_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_relationships_tenant_id", "relationships", ["tenant_id"])
    op.create_index("ix_relationships_user_id", "relationships", ["user_id"])
    op.create_index("ix_relationships_agent_id", "relationships", ["agent_id"])
    op.create_index("ix_relationships_device_id", "relationships", ["device_id"])

    op.create_table(
        "memory_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("app_id", sa.String(64), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("passport_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "relationship_id", sa.String(64), sa.ForeignKey("relationships.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", PG_ENUM(name="memory_type", create_type=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("scope", PG_ENUM(name="memory_scope", create_type=False), nullable=False),
        sa.Column("sensitivity", PG_ENUM(name="memory_sensitivity", create_type=False), nullable=False),
        sa.Column("status", PG_ENUM(name="memory_status", create_type=False), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("portability", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("supersedes", sa.String(64), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("model_provenance", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_memory_records_tenant_id", "memory_records", ["tenant_id"])
    op.create_index("ix_memory_records_app_id", "memory_records", ["app_id"])
    op.create_index("ix_memory_records_passport_id", "memory_records", ["passport_id"])
    op.create_index("ix_memory_records_user_id", "memory_records", ["user_id"])
    op.create_index("ix_memory_records_relationship_id", "memory_records", ["relationship_id"])
    op.create_index("ix_memory_records_agent_id", "memory_records", ["agent_id"])
    op.create_index("ix_memory_records_device_id", "memory_records", ["device_id"])
    op.create_index("ix_memory_records_user_type", "memory_records", ["user_id", "type"])
    op.create_index("ix_memory_records_status", "memory_records", ["status"])

    op.create_table(
        "migrations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "source_relationship_id",
            sa.String(64),
            sa.ForeignKey("relationships.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_relationship_id", sa.String(64), nullable=False),
        sa.Column(
            "source_device_id", sa.String(64), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "target_device_id", sa.String(64), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", PG_ENUM(name="migration_status", create_type=False), nullable=False),
        sa.Column("selected_memory_ids", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("skipped_memory_ids", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("old_device_access", PG_ENUM(name="old_device_access", create_type=False), nullable=False),
        sa.Column("audit_log_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_migrations_tenant_id", "migrations", ["tenant_id"])
    op.create_index("ix_migrations_user_id", "migrations", ["user_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("action", PG_ENUM(name="audit_action", create_type=False), nullable=False),
        sa.Column("target", sa.String(128), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_tenant_action", "audit_logs", ["tenant_id", "action"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("app_id", sa.String(64), sa.ForeignKey("apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("environment", PG_ENUM(name="environment", create_type=False), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("key", name="uq_api_keys_key"),
    )
    op.create_index("ix_api_keys_app_id", "api_keys", ["app_id"])
    op.create_index("ix_api_keys_key", "api_keys", ["key"])


def downgrade() -> None:
    # Drop tables in reverse dependency order.
    op.drop_table("api_keys")
    op.drop_table("audit_logs")
    op.drop_table("migrations")
    op.drop_table("memory_records")
    op.drop_table("relationships")
    op.drop_table("auto_write_rules")
    # Drop the deferred circular FK first, then the two tables it links.
    op.drop_constraint("fk_memory_policies_agent_id_agents", "memory_policies", type_="foreignkey")
    op.drop_table("agents")
    op.drop_table("memory_policies")
    op.drop_table("devices")
    op.drop_table("users")
    op.drop_table("apps")
    op.drop_table("tenants")

    # Drop enum types. checkfirst=True keeps this idempotent.
    for enum_name in (
        "alert_severity",
        "source_type",
        "team_role",
        "audit_action",
        "old_device_access",
        "migration_status",
        "autowrite_action",
        "portability_layer",
        "memory_status",
        "memory_sensitivity",
        "memory_scope",
        "memory_type",
        "device_status",
        "relationship_type",
        "agent_type",
        "age_group",
        "data_region",
        "app_status",
        "tenant_plan",
        "environment",
        "product_type",
    ):
        # DROP TYPE IF EXISTS is idempotent; safer than sa.Enum().drop() across
        # partial downgrade runs.
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
