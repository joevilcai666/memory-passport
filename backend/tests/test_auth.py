"""Tests for the API-key auth middleware.

Every non-public route must carry ``Authorization: Bearer mp_<env>_<secret>``
that resolves to a seeded ApiKey. Missing/unknown keys return 401.
"""

from __future__ import annotations

import respx


def test_missing_authorization_returns_401(app_client, seeded_auth_rows):
    """No Authorization header on a protected route → 401."""
    resp = app_client.get("/v1/users/anything-not-yet-implemented")
    assert resp.status_code == 401
    assert resp.json() == {"detail": "unauthenticated"}


def test_bad_scheme_returns_401(app_client, seeded_auth_rows):
    """A non-Bearer scheme is treated as unauthenticated."""
    resp = app_client.get(
        "/v1/users/anything-not-yet-implemented",
        headers={"Authorization": "Basic xyz"},
    )
    assert resp.status_code == 401


def test_unknown_key_returns_401(app_client, seeded_auth_rows):
    """A syntactically-valid but unknown token → 401."""
    resp = app_client.get(
        "/v1/users/anything-not-yet-implemented",
        headers={"Authorization": "Bearer mp_sandbox_does_not_exist"},
    )
    assert resp.status_code == 401


def test_valid_sandbox_key_passes_auth(app_client, seeded_auth_rows, sandbox_key):
    """The seeded sandbox key authenticates — past the middleware (404, not 401)."""
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        resp = app_client.get(
            "/v1/users/anything-not-yet-implemented",
            headers={"Authorization": f"Bearer {sandbox_key}"},
        )

    # 404 means the request cleared auth but no such route exists yet (Slice 1
    # ships only /v1/health). The important assertion: it's NOT 401.
    assert resp.status_code != 401


def test_bare_token_also_authenticates(app_client, seeded_auth_rows, sandbox_key):
    """A bare token (no 'Bearer' scheme) is accepted for SDK compatibility."""
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        resp = app_client.get(
            "/v1/users/anything-not-yet-implemented",
            headers={"Authorization": sandbox_key},
        )

    assert resp.status_code != 401


def test_health_allowed_without_auth(app_client):
    """The public allowlist covers /v1/health even with no rows seeded."""
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        resp = app_client.get("/v1/health")

    assert resp.status_code == 200
