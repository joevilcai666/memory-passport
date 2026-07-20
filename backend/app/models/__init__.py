"""ORM models package — every table in the MP schema.

Importing this package registers all models on :class:`app.db.base.Base`, which
Alembic's ``env.py`` introspects for autogenerate.
"""

from app.models.audit import AuditLog
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import AutoWriteRule, MemoryPolicy, MemoryRecord
from app.models.migration import Migration
from app.models.tenant import ApiKey, App, Tenant

__all__ = [
    "Agent",
    "ApiKey",
    "App",
    "AuditLog",
    "AutoWriteRule",
    "Device",
    "Migration",
    "MemoryPolicy",
    "MemoryRecord",
    "Relationship",
    "Tenant",
    "User",
]
