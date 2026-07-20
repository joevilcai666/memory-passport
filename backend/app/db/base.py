"""SQLAlchemy declarative base + naming convention + portable column types.

Production runs on Postgres (JSONB, ARRAY, native enums). Tests need to also
run on sqlite so the suite is usable without a live Postgres — the
:func:`jsonb` / :func:`text_array` helpers build ``with_variant`` columns that
fall back to ``JSON`` / ``Text`` on sqlite.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, MetaData, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

# Constrained names so Alembic autogenerate produces deterministic output and
# `downgrade base` returns to a clean state regardless of run order.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every MP model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _json_default(obj):
    """JSON encoder for types the stdlib default can't handle.

    JSONB columns in MP store nested dicts that include ISO timestamps (e.g.
    ``memory_records.source.timestamp``); the seed data builds those as Python
    ``datetime`` objects. Serialise them to ISO 8601 here so the round-trip is
    faithful to ``src/lib/types.ts`` (where they're ``string``).
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


# A reusable encoder that handles datetime/Decimal — passed to psycopg/SQLA as
# the JSON serialiser for every JSONB column.
_JSON_DUMPS = lambda obj: json.dumps(obj, default=_json_default)  # noqa: E731


# Postgres-only imports are deferred so importing this module doesn't require
# psycopg at collection time (sqlite tests don't load the pg dialect).
try:
    from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:  # pragma: no cover — psycopg is a hard dep in practice
    PG_ARRAY = None  # type: ignore[assignment]
    JSONB = None  # type: ignore[assignment]


def jsonb() -> TypeDecorator:
    """A JSONB column on Postgres, plain JSON elsewhere (sqlite tests).

    Nested datetimes are serialised to ISO strings via the engine-level
    ``json_serializer`` set in :func:`app.db.session.get_engine` (this SA
    version doesn't accept json_serializer on the type itself).
    """
    if JSONB is not None:
        return JSONB().with_variant(JSON(), "sqlite")
    return JSON()


def text_array() -> TypeDecorator:
    """A Postgres ``ARRAY(Text)`` column; falls back to JSON on sqlite.

    Stored as a list of strings in Python either way, so model code is uniform.
    """
    if PG_ARRAY is not None:
        return PG_ARRAY(String).with_variant(JSON(), "sqlite")
    return JSON()


__all__ = ["Base", "jsonb", "text_array"]

