"""AuditLog helper — every provisioning action appends one row.

The audit trail is the B-side accountability record (PRD §10). Each successful
provisioning operation writes a single row whose ``action`` is one of the
``*.created`` / ``device.*`` enum values, scoped to the caller's tenant, with
``actor`` identifying the API key that drove the action.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.services.ids import new_audit_id


def write_audit(
    db: Session,
    *,
    tenant_id: str,
    actor: str,
    action: AuditAction,
    target: str,
    detail: str,
) -> AuditLog:
    """Append an AuditLog row and flush so the caller's commit persists it.

    ``actor`` is ``api:<key_id>`` for API-driven provisioning (see
    ``app.api.deps``). The function does not commit — the owning request session
    does — but it does flush so ``target`` FK lookups in the same transaction
    see the row if needed.
    """
    row = AuditLog(
        id=new_audit_id(),
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        target=target,
        detail=detail,
        timestamp=datetime.now(tz=UTC),
    )
    db.add(row)
    db.flush()
    return row


def api_actor(api_key_id: str) -> str:
    """Stable actor string for API-driven actions."""
    return f"api:{api_key_id}"
