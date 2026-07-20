"""Memory Passport FastAPI application factory.

Slice 1 wiring:
* lifespan: run Alembic migrations on startup (toggleable), so a fresh
  ``docker-compose up`` is immediately usable.
* middleware: tenant API-key auth (resolves ``Authorization: Bearer`` →
  ``TenantContext`` on ``request.state``).
* routes: ``GET /v1/health`` (the only endpoint in this slice) + docs.

Later slices mount the business routers under ``/v1``.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1 import router as v1_router
from app.auth import auth_middleware
from app.config import get_settings

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    """Apply Alembic migrations to head, unless disabled for tests."""
    settings = get_settings()
    if not settings.run_migrations_on_startup:
        return
    try:
        from alembic.config import Config

        from alembic import command

        # alembic.ini lives next to the app package (the image WORKDIR is /app).
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied to head")
    except Exception:  # noqa: BLE001
        # Don't crash the app on migration failure — the health endpoint will
        # report db=error and the operator can inspect logs. Re-raise in DEBUG.
        logger.exception("Alembic migration on startup failed")
        if settings.log_level.lower() == "debug":
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run migrations. Nothing to clean up on shutdown."""
    _run_migrations()
    yield


def create_app() -> FastAPI:
    """Build the FastAPI app — one place to wire middleware + routers."""
    settings = get_settings()

    app = FastAPI(
        title="Memory Passport",
        description="B2B2C portable memory infrastructure for AI companions and robots.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Auth runs first so even /v1/* routes resolve a tenant before the handler.
    # /v1/health + /docs are allowlisted inside the middleware.
    app.middleware("http")(auth_middleware)

    app.include_router(health_router)
    app.include_router(v1_router)

    # Convenience root redirect to docs — useful when poking the dev server.
    if settings.log_level.lower() in ("debug", "info"):
        logger.info("Memory Passport backend ready on %s:%s", settings.host, settings.port)

    return app


app = create_app()
