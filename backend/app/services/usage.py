"""One structured usage writer shared by successful memory operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import UsageOperation
from app.models.usage import UsageEvent
from app.services.ids import new_usage_id


def write_usage(
    db: Session,
    tenant_id: str,
    user_id: str,
    operation: UsageOperation,
    timestamp: datetime | None = None,
) -> UsageEvent:
    event = UsageEvent(
        id=new_usage_id(),
        tenant_id=tenant_id,
        user_id=user_id,
        operation=operation,
        timestamp=timestamp or datetime.now(tz=UTC),
    )
    db.add(event)
    db.flush()
    return event


__all__ = ["write_usage"]
