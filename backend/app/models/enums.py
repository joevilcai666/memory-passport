"""Domain enums — 1:1 with ``src/lib/types.ts``.

Each enum is declared twice:

* A Python ``enum.Enum`` for application code.
* A matching SQLAlchemy ``Enum`` type (``PG_<Name>``) for Postgres enum columns.

Postgres enum *types* are first-class objects in the schema (not just CHECK
constraints), so Alembic can create/drop them deterministically. The Python
enum is the source of values for both the PG type and any JSON/JSONB columns
that store enum-typed values as strings.
"""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum

# Python enums -----------------------------------------------------------------


class ProductType(str, enum.Enum):
    SOFTWARE = "software"
    HARDWARE = "hardware"
    HYBRID = "hybrid"


class Environment(str, enum.Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class TenantPlan(str, enum.Enum):
    SANDBOX = "Sandbox"
    GROWTH = "Growth"
    ENTERPRISE = "Enterprise"


class AppStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"


class DataRegion(str, enum.Enum):
    US_EAST_1 = "us-east-1"
    EU_WEST_1 = "eu-west-1"
    AP_SOUTHEAST_1 = "ap-southeast-1"


class AgeGroup(str, enum.Enum):
    ADULT = "adult"
    MINOR = "minor"
    UNKNOWN = "unknown"


class AgentType(str, enum.Enum):
    CHARACTER = "character"
    COMPANION = "companion"
    PET = "pet"
    ROBOT = "robot"
    ASSISTANT = "assistant"


class RelationshipType(str, enum.Enum):
    COMPANION = "companion"
    PET = "pet"
    ROBOT = "robot"
    ASSISTANT = "assistant"


class DeviceStatus(str, enum.Enum):
    REGISTERED = "registered"
    BOUND = "bound"
    UNBOUND = "unbound"
    WIPED = "wiped"


class MemoryType(str, enum.Enum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    BOUNDARY = "boundary"
    RELATIONSHIP = "relationship"
    EVENT = "event"
    TASK = "task"


class MemoryScope(str, enum.Enum):
    USER_GLOBAL = "user_global"
    RELATIONSHIP_ONLY = "relationship_only"
    AGENT_ONLY = "agent_only"
    DEVICE_ONLY = "device_only"
    PRIVATE = "private"
    BLOCKED = "blocked"


class MemorySensitivity(str, enum.Enum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class MemoryStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    ARCHIVED = "archived"
    NEEDS_REVIEW = "needs_review"
    DELETED = "deleted"
    EXPIRED = "expired"
    FLAGGED_WRONG = "flagged_wrong"


class PortabilityLayer(str, enum.Enum):
    PORTABLE = "portable"
    DEVICE_LOCAL = "device_local"


class AutoWriteAction(str, enum.Enum):
    AUTO_WRITE = "auto_write"
    CONFIRM = "confirm"
    BLOCK = "block"


class MigrationStatus(str, enum.Enum):
    DRAFT = "draft"
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class OldDeviceAccess(str, enum.Enum):
    KEEP = "keep"
    REMOVE = "remove"


class UsageOperation(str, enum.Enum):
    INGEST = "ingest"
    RETRIEVE = "retrieve"
    UPDATE = "update"
    DELETE = "delete"


class PassportStatus(str, enum.Enum):
    ACTIVE = "active"
    DELETED = "deleted"


class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditAction(str, enum.Enum):
    MEMORY_CREATED = "memory.created"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_EDITED = "memory.edited"
    MEMORY_VIEWED = "memory.viewed"
    POLICY_CHANGED = "policy.changed"
    DEVICE_BOUND = "device.bound"
    DEVICE_UNBOUND = "device.unbound"
    MIGRATION_COMPLETED = "migration.completed"
    MIGRATION_STARTED = "migration.started"
    MIGRATION_ROLLED_BACK = "migration.rolled_back"
    MEMORY_EXPORTED = "memory.exported"
    # Slice 2 — provisioning actions (one row per successful entity creation).
    APP_CREATED = "app.created"
    AGENT_CREATED = "agent.created"
    USER_CREATED = "user.created"
    RELATIONSHIP_CREATED = "relationship.created"
    DEVICE_REGISTERED = "device.registered"
    # Slice 3/4/7 — pipeline actions.
    MEMORY_BLOCKED = "memory.blocked"  # S3 event blocked end-to-end (no HMS call)
    RETRIEVAL_PERFORMED = "retrieval.performed"
    DEVICE_WIPED = "device.wiped"
    USER_DELETED = "user.deleted"
    TENANT_HMS_PROVISIONED = "tenant.hms_provisioned"  # issue #12 multi-tenant
    API_KEY_CREATED = "api_key.created"
    API_KEY_ROTATED = "api_key.rotated"
    USER_CONSENT_CHANGED = "user.consent_changed"
    RETRIEVAL_FEEDBACK_RECORDED = "retrieval.feedback_recorded"
    TEAM_INVITED = "team.invited"
    TEAM_JOINED = "team.joined"


class TeamRole(str, enum.Enum):
    OWNER = "Owner"
    ADMIN = "Admin"
    SUPPORT = "Support"


class SourceType(str, enum.Enum):
    CHAT = "chat"
    VOICE = "voice"
    SETUP = "setup"
    EXPLICIT_INSTRUCTION = "explicit_instruction"
    ROBOT_EVENT = "robot_event"
    APP_EVENT = "app_event"


class AlertSeverity(str, enum.Enum):
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


# SQLAlchemy enum types --------------------------------------------------------
# name= is the Postgres enum type name created by Alembic. values_primitives
# keeps str-Enum values usable as plain strings in JSON/JSONB.


def _pg_enum(python_enum: type[enum.Enum], name: str) -> SAEnum:
    """Build a Postgres-native enum column type for a Python enum."""
    return SAEnum(python_enum, name=name, values_callable=lambda e: [m.value for m in e])


PG_PRODUCT_TYPE = _pg_enum(ProductType, "product_type")
PG_ENVIRONMENT = _pg_enum(Environment, "environment")
PG_TENANT_PLAN = _pg_enum(TenantPlan, "tenant_plan")
PG_APP_STATUS = _pg_enum(AppStatus, "app_status")
PG_DATA_REGION = _pg_enum(DataRegion, "data_region")
PG_AGE_GROUP = _pg_enum(AgeGroup, "age_group")
PG_AGENT_TYPE = _pg_enum(AgentType, "agent_type")
PG_RELATIONSHIP_TYPE = _pg_enum(RelationshipType, "relationship_type")
PG_DEVICE_STATUS = _pg_enum(DeviceStatus, "device_status")
PG_MEMORY_TYPE = _pg_enum(MemoryType, "memory_type")
PG_MEMORY_SCOPE = _pg_enum(MemoryScope, "memory_scope")
PG_MEMORY_SENSITIVITY = _pg_enum(MemorySensitivity, "memory_sensitivity")
PG_MEMORY_STATUS = _pg_enum(MemoryStatus, "memory_status")
PG_PORTABILITY_LAYER = _pg_enum(PortabilityLayer, "portability_layer")
PG_AUTOWRITE_ACTION = _pg_enum(AutoWriteAction, "autowrite_action")
PG_MIGRATION_STATUS = _pg_enum(MigrationStatus, "migration_status")
PG_OLD_DEVICE_ACCESS = _pg_enum(OldDeviceAccess, "old_device_access")
PG_USAGE_OPERATION = _pg_enum(UsageOperation, "usage_operation")
PG_PASSPORT_STATUS = _pg_enum(PassportStatus, "passport_status")
PG_EXPORT_STATUS = _pg_enum(ExportStatus, "export_status")
PG_AUDIT_ACTION = _pg_enum(AuditAction, "audit_action")
PG_TEAM_ROLE = _pg_enum(TeamRole, "team_role")
PG_SOURCE_TYPE = _pg_enum(SourceType, "source_type")
PG_ALERT_SEVERITY = _pg_enum(AlertSeverity, "alert_severity")
