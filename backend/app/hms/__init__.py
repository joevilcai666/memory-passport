"""HMS HTTP client — the thin wrapper MP uses to talk to the memory engine.

Slice 1 only needs:
* :meth:`HmsClient.health` — ping ``GET /health`` (used by ``/v1/health``).
* :meth:`HmsClient.put_bank` — provision an empty bank via
  ``PUT /v1/default/banks/{bank_id}`` (HMS auto-creates with defaults; no LLM
  call is made). Used by the seed script.

retain/recall land in later slices; stubs are deliberately omitted to keep the
slice honest (this is the prefactor, not the engine).
"""

from __future__ import annotations

from typing import Any

import httpx


class HmsError(RuntimeError):
    """Raised when an HMS call fails unexpectedly."""


class HmsClient:
    """Stateless async client for the HMS FastAPI service.

    Each method opens a short-lived ``httpx.AsyncClient`` so the client is safe
    to use from request handlers and the seed script alike. A persistent client
    with connection pooling is a P1 optimisation.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def health(self) -> dict[str, Any]:
        """GET /health on hms-api.

        Returns the HMS health dict (``{"status": "healthy", "database": ...}``
        on success). Raises :class:`HmsError` on transport/HTTP failure so the
        health endpoint can downgrade the ``hms`` field honestly.
        """
        try:
            async with self._client() as client:
                resp = await client.get(f"{self._base_url}/health", headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 — report any failure honestly
            raise HmsError(f"HMS health check failed: {exc}") from exc

    async def put_bank(self, bank_id: str) -> dict[str, Any]:
        """PUT /v1/default/banks/{bank_id} — idempotently create an empty bank.

        HMS auto-creates the bank with defaults on first touch
        (``get_bank_profile`` does ``INSERT ... ON CONFLICT DO NOTHING``), so an
        empty body ``{}`` is enough. No LLM/embedding call is made.
        """
        url = f"{self._base_url}/v1/default/banks/{bank_id}"
        try:
            async with self._client() as client:
                resp = await client.put(url, json={}, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HmsError(f"HMS put_bank({bank_id}) failed: {exc}") from exc

    async def list_banks(self) -> list[dict[str, Any]]:
        """GET /v1/default/banks — list every bank under the tenant schema.

        Used by tests to assert the 4 user-id banks exist post-seed.
        """
        url = f"{self._base_url}/v1/default/banks"
        try:
            async with self._client() as client:
                resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("banks", [])
        except Exception as exc:  # noqa: BLE001
            raise HmsError(f"HMS list_banks failed: {exc}") from exc

    def _client(self) -> httpx.AsyncClient:
        """Build a short-lived client.

        ``trust_env=False`` so the MP→hms-api call stays on the internal docker
        network and never picks up host HTTP_PROXY/ALL_PROXY env vars (which
        would otherwise leak into the container and break the internal call).
        """
        return httpx.AsyncClient(timeout=self._timeout, trust_env=False)
