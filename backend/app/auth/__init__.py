"""Tenant auth — API-key middleware.

Every protected request must carry ``Authorization: Bearer mp_<env>_<secret>``.
The middleware resolves the bearer token to an :class:`ApiKey` row, loads the
parent :class:`App` + :class:`Tenant`, and attaches a :class:`TenantContext`
to ``request.state.tenant`` for downstream handlers/dependencies.

Health, docs, and OpenAPI routes are allowlisted so unauthenticated probes
and the acceptance smoke test (which hits ``/v1/health``) work without a key.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.models.tenant import ApiKey, App, Tenant


@dataclass
class TenantContext:
    """The resolved caller attached to ``request.state.tenant``."""

    api_key: ApiKey
    app: App
    tenant: Tenant


# Paths that never require auth: health, docs, openapi, redoc, favicon.
# Matching is prefix-based so /docs/oauth2-redirect and /openapi.json both pass.
PUBLIC_PATH_PREFIXES = (
    "/v1/health",
    "/v1/public/team-invites",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)


def _is_public(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") or path == p for p in PUBLIC_PATH_PREFIXES)


def _extract_bearer(authorization: str | None) -> str | None:
    """Pull the token out of ``Authorization: Bearer <token>``.

    Accepts the bare token too (HMS's convention), but the canonical form is
    the ``Bearer`` scheme — matches what the Quickstart page tells users to copy.
    """
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer":
        return token.strip() or None
    # Bare token (no scheme) — accept for SDK compatibility.
    return authorization.strip() or None


async def auth_middleware(request: Request, call_next):
    """Resolve the bearer token to a TenantContext; 401 on any failure."""
    if _is_public(request.url.path):
        return await call_next(request)

    token = _extract_bearer(request.headers.get("Authorization"))
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "unauthenticated"},
        )

    from app.db.session import session_scope

    try:
        with session_scope() as db:
            api_key = db.query(ApiKey).filter(ApiKey.key == token).one_or_none()
            if api_key is None:
                return _unauthorized()
            # Eager-load app + tenant so the context is self-contained after
            # the session closes (expire_on_commit=False keeps them usable).
            app = api_key.app
            tenant = app.tenant
            if app.status.value != "active":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "app_paused"},
                )
            context = TenantContext(api_key=api_key, app=app, tenant=tenant)
    except Exception:
        # DB errors are 500s, not 401s — don't leak auth state on infra failure.
        raise

    request.state.tenant = context
    return await call_next(request)


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "unauthenticated"},
    )
