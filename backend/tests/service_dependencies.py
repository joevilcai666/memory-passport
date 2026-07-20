"""Bounded probes used to skip service-backed tests on an unprepared host."""

from __future__ import annotations

import httpx
from sqlalchemy import create_engine, text

from app.config import get_settings


def postgres_available() -> bool:
    settings = get_settings()
    if not settings.database_url.startswith("postgresql"):
        return False
    server_url = settings.database_url.rsplit("/", 1)[0] + "/postgres"
    engine = create_engine(
        server_url,
        connect_args={"connect_timeout": 1},
        pool_pre_ping=True,
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - absence is a skip condition
        return False
    finally:
        engine.dispose()


def hms_available() -> bool:
    settings = get_settings()
    if settings.hms_api_url.startswith("http://hms-api.test"):
        return False
    try:
        response = httpx.get(
            f"{settings.hms_api_url.rstrip('/')}/health",
            timeout=1.0,
            trust_env=False,
        )
        return response.status_code == 200 and response.json().get("status") == "healthy"
    except Exception:  # noqa: BLE001 - absence is a skip condition
        return False
