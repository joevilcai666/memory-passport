"""Shared schema primitives.

* ``BaseModel`` — every schema inherits from this; configured to read from ORM
  attributes (``from_attributes=True``) so a route can ``return orm_row`` and
  FastAPI serialises it via the response_model.
* Timestamps are emitted as ISO-8601 strings (``types.ts`` types them as
  ``string``), matching how the seed data round-trips datetimes through JSONB.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict

# Every MP id is a string (``types.ts``: ``export type ID = string``). Kept as a
# plain ``str`` here — the Annotated alias documents intent at the call site.
ID = Annotated[str, "MP entity id"]


class _OrmModel(BaseModel):
    """Base for response models that map directly from ORM rows."""

    model_config = ConfigDict(from_attributes=True)


def to_iso(value: datetime | None) -> str | None:
    """Serialise a datetime to ISO-8601, or None.

    ``types.ts`` types every timestamp as ``string``; JSON doesn't carry tz, so
    we emit an ISO string (with offset when the datetime is tz-aware).
    """
    if value is None:
        return None
    return value.isoformat()
