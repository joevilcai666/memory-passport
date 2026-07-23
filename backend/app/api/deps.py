"""FastAPI dependencies shared across routes."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import TenantContext
from app.db.session import get_sessionmaker
from app.models.enums import TeamRole


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


def require_role(
    *allowed: TeamRole,
) -> Callable[[TenantContext], TenantContext]:
    """Build a dependency that allows only the given operator roles.

    A caller whose effective role (null → Owner for sandbox/customer keys) is
    not in ``allowed`` gets a 403 ``insufficient_role``. Use on sensitive
    operator-only mutations (e.g. policy changes, sensitive reveal)::

        @router.post(..., dependencies=[Depends(require_role(TeamRole.OWNER, TeamRole.ADMIN))])
    """

    def _check(tenant: TenantContext = TenantDep) -> TenantContext:
        if tenant.effective_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "insufficient_role",
                    "message": (
                        f"role '{tenant.effective_role.value}' is not permitted"
                        " for this action"
                    ),
                    "required": [r.value for r in allowed],
                },
            )
        return tenant

    return _check


# Owner/Admin gate — the common "operator mutation" permission.
OperatorOrAdminDep = Depends(require_role(TeamRole.OWNER, TeamRole.ADMIN))

