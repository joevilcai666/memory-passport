"""FastAPI dependencies shared across routes."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.auth import TenantContext


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


# Convenience re-export so routes can write ``Depends(CommonDeps.tenant)``.
TenantDep = Depends(get_tenant)
