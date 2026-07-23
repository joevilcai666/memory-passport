"""Browser CORS contract for the local Next.js evaluator."""

from __future__ import annotations

from app.config import Settings


def _preflight(client, origin: str):
    return client.options(
        "/v1/memories",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_local_browser_preflight_allows_authenticated_request(app_client) -> None:
    response = _preflight(app_client, "http://127.0.0.1:3000")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_unlisted_origin_receives_no_cors_permission(app_client) -> None:
    response = _preflight(app_client, "https://untrusted.example")

    assert "access-control-allow-origin" not in response.headers


def test_configured_origins_are_trimmed_deduplicated_and_ordered() -> None:
    settings = Settings(
        cors_allowed_origins=(
            " http://127.0.0.1:3000,https://console.example,"
            "http://127.0.0.1:3000, "
        )
    )

    assert settings.cors_origin_list == [
        "http://127.0.0.1:3000",
        "https://console.example",
    ]
