"""Scope-filter matrix + sensitivity masking (PRD §9.1).

Pure functions — no DB access — so the retrieve pipeline and the Slice 7
post-wipe tests can exercise them directly. The matrix decides, given a memory
record's ``scope`` and the caller's context, whether the caller may read it.

Scope rules (PRD §9.1):
  blocked          -> never returned.
  private          -> only to the originating agent/user (identified by agent_id
                      matching the record's agent_id).
  device_only      -> only when the caller is the bound device AND that device
                      is currently ``bound`` (a wiped/unbound device loses
                      access). This is the Slice 7 coordination point.
  agent_only       -> only to that record's agent.
  relationship_only-> only within the user×agent relationship.
  user_global      -> to any of the user's relationships (broadest).

Sensitivity masking:
  When ``policy.retrieval.include_sensitive_in_prompt == false``, S2/S3
  ``content`` is projected as the redaction token in the returned projection.
  The DB row is NEVER modified — only the response projection is masked.
"""

from __future__ import annotations

from typing import Any

from app.models.enums import MemoryScope, MemorySensitivity
from app.models.memory import MemoryRecord

# The token substituted into the masked projection. DB content stays intact.
MASK_TOKEN = "[redacted]"


def is_readable(
    record: MemoryRecord,
    *,
    caller_agent_id: str,
    caller_relationship_id: str,
    caller_device_id: str | None,
    caller_device_status: str | None,
) -> bool:
    """True iff the caller's context permits reading ``record``.

    ``caller_device_status`` is the Device.status.value of the device the
    caller identified as (``None`` if the caller is not a device). The retrieve
    pipeline passes ``"bound"`` for a live device and ``"wiped"``/``"unbound"``
    for a device that's lost access.
    """
    scope = record.scope

    if scope == MemoryScope.BLOCKED:
        return False

    if scope == MemoryScope.PRIVATE:
        # Only the originating agent may read a private memory.
        return record.agent_id == caller_agent_id

    if scope == MemoryScope.DEVICE_ONLY:
        # Caller must be the bound device, AND that device must still be bound.
        # A wiped device (Slice 7) loses device_only access entirely.
        if caller_device_id is None:
            return False
        if record.device_id != caller_device_id:
            return False
        return caller_device_status == "bound"

    if scope == MemoryScope.AGENT_ONLY:
        return record.agent_id == caller_agent_id

    if scope == MemoryScope.RELATIONSHIP_ONLY:
        return record.relationship_id == caller_relationship_id

    if scope == MemoryScope.USER_GLOBAL:
        return True

    # Unknown scope — fail closed.
    return False


def mask_if_needed(record: MemoryRecord, *, include_sensitive: bool) -> str:
    """Return the content to project for ``record``, masking S2/S3 when needed.

    The DB ``content`` column is never modified; this only affects the value
    placed into the response projection. When ``include_sensitive`` is True
    (policy.retrieval.include_sensitive_in_prompt), the full content is returned.
    """
    if include_sensitive:
        return record.content
    if record.sensitivity in (MemorySensitivity.S2, MemorySensitivity.S3):
        return MASK_TOKEN
    return record.content


def project_record(
    record: MemoryRecord,
    *,
    include_sensitive: bool,
) -> dict[str, Any]:
    """Build the JSON projection of one memory record for the retrieve response.

    Applies sensitivity masking to ``content``; carries the rich domain fields
    (scope, sensitivity, portability, source.quote, model_provenance) HMS
    doesn't know about. This is the shape the debug-trace endpoint also stores.
    """
    return {
        "id": record.id,
        "type": _val(record.type),
        "content": mask_if_needed(record, include_sensitive=include_sensitive),
        "scope": _val(record.scope),
        "sensitivity": _val(record.sensitivity),
        "status": _val(record.status),
        "confidence": record.confidence,
        "source": record.source,
        "portability": record.portability,
        "model_provenance": record.model_provenance,
        "usage_count": record.usage_count,
        "last_used_at": (
            record.last_used_at.isoformat() if record.last_used_at is not None else None
        ),
    }


def _val(value: Any) -> Any:
    """Unwrap a Python enum to its string value (the TS-facing shape)."""
    return value.value if hasattr(value, "value") else value
