"""Tests for GET /v1/health — the honest three-way liveness probe."""

from __future__ import annotations

import httpx
import respx


def test_health_all_ok(app_client):
    """mp/hms/db all ok when DB responds and HMS /health is healthy."""
    with respx.mock(base_url="http://hms-api.test") as mock:
        mock.get("/health").respond(200, json={"status": "healthy", "database": "connected"})
        resp = app_client.get("/v1/health")

    assert resp.status_code == 200
    assert resp.json() == {
        "mp": "ok",
        "hms": "ok",
        "db": "ok",
        "memory_engine": "demo",
    }


def test_health_hms_downgrades_to_error(app_client):
    """When HMS /health is unhealthy, the hms field is "error" and status is 503."""
    with respx.mock(base_url="http://hms-api.test") as mock:
        mock.get("/health").respond(200, json={"status": "unhealthy"})
        resp = app_client.get("/v1/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["mp"] == "ok"
    assert body["db"] == "ok"
    assert body["hms"] == "error"
    assert body["memory_engine"] == "demo"


def test_health_hms_unreachable(app_client):
    """A transport error against HMS surfaces as hms=error (not a crash)."""
    with respx.mock(base_url="http://hms-api.test") as mock:
        mock.get("/health").mock(side_effect=httpx.ConnectError("connection refused"))
        resp = app_client.get("/v1/health")

    assert resp.status_code == 503
    assert resp.json()["hms"] == "error"


def test_health_is_public(app_client):
    """No Authorization header is required for /v1/health."""
    with respx.mock(base_url="http://hms-api.test") as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        resp = app_client.get("/v1/health")

    assert resp.status_code == 200
