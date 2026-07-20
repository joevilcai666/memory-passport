"""FastAPI dependencies shared across routes."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import TenantContext
from app.db.session import get_sessionmaker


def get_tenant(request: Request) -> TenantContext:
    """Return the TenantContext resolved by the auth middleware.

    Protected routes take this dependency to scope every query by tenant.
    A missing context means the middleware was bypassed (shouldn't happen for
    registered routes), which we treat as unauthenticated.
    """
    context = getattr(request.state, "tenant", None)
    if context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthenticated")
    return context


def get_db() -> Iterator[Session]:
    """Request-scoped Session — opens one per request, closes on exit.

    Equivalent to ``app.db.session.get_session`` but defined here so the route
    signature can use the module-level ``DbDep`` singleton (ruff B008 forbids
    calling ``Depends()`` in argument defaults).
    """
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


# Convenience module-level singletons so route signatures read cleanly without
# triggering ruff B008 (``Depends()`` in argument defaults).
TenantDep = Depends(get_tenant)
DbDep = Depends(get_db)

