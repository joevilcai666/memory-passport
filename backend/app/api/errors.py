"""Shared HTTP error helpers for the MP API.

Centralising the error body shape keeps the contract uniform across routers:

    {"detail": <human message>, "code": <machine code>, ...extra}

FastAPI's default ``HTTPException(detail=...)`` puts the message in ``detail``;
for richer bodies (e.g. the device state-machine error that also carries
``current`` and ``action``) we pass a dict as ``detail``.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


def not_found(entity: str, ident: str | None = None) -> HTTPException:
    """404 — entity doesn't exist *in this tenant* (cross-tenant isolation).

    Cross-tenant references intentionally return 404 (not 403) so the API
    doesn't leak the existence of another tenant's rows.
    """
    suffix = f" {ident}" if ident else ""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "not_found", "message": f"{entity} not found{suffix}"},
    )


def forbidden(code: str, message: str, **extra: Any) -> HTTPException:
    """403 — the caller is authenticated but not allowed to do this."""
    body: dict[str, Any] = {"code": code, "message": message}
    body.update(extra)
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=body)


def conflict_illegal_state(current: str, action: str) -> HTTPException:
    """409 — device state-machine violation (e.g. binding a bound device).

    Body carries the current state + attempted action so the client can branch
    on the failure mode without re-fetching.
    """
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "illegal_state_transition",
            "message": f"cannot {action} a device in state '{current}'",
            "current": current,
            "action": action,
        },
    )


def memory_disabled(user_id: str) -> HTTPException:
    """409 — the user has explicitly disabled memory operations."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "memory_disabled",
            "message": f"memory is disabled for user {user_id}",
        },
    )
