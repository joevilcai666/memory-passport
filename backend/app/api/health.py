"""GET /v1/health — honest three-way liveness probe.

Returns ``{"mp": "ok", "hms": "ok", "db": "ok"}`` when every component is up.
Any failure downgrades the corresponding field to ``"error"`` and the HTTP
status to 503, so the response always tells the truth about dependencies.

This route is on the public allowlist (no auth) so the docker-compose
healthcheck and the acceptance smoke test can hit it without a key.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_engine
from app.hms import HmsClient

router = APIRouter(tags=["health"])


@router.get("/v1/health")
async def health() -> JSONResponse:
    mp = "ok"

    # DB: a trivial SELECT 1. Failures (connection, auth) -> "error".
    db = "ok"
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db = "error"

    # HMS: ping the upstream /health endpoint.
    hms = "ok"
    try:
        settings = get_settings()
        client = HmsClient(base_url=settings.hms_api_url, api_key=settings.hms_api_key)
        result = await client.health()
        if result.get("status") != "healthy":
            hms = "error"
    except Exception:  # noqa: BLE001
        hms = "error"

    payload = {"mp": mp, "hms": hms, "db": db}
    all_ok = all(v == "ok" for v in payload.values())
    code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=payload)
