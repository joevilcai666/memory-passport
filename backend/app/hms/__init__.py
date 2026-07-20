"""HMS HTTP client — the thin wrapper MP uses to talk to the memory engine.

Methods (one per HMS endpoint MP needs):
* :meth:`health`       — ``GET /health`` (liveness probe).
* :meth:`put_bank`     — ``PUT /v1/default/banks/{bank_id}`` (idempotent create).
* :meth:`list_banks`   — ``GET /v1/default/banks`` (test introspection).
* :meth:`retain`       — ``POST /v1/default/banks/{bank_id}/memories`` (ingest).
* :meth:`recall`       — ``POST /v1/default/banks/{bank_id}/memories/recall`` (retrieve).
* :meth:`list_memories`— ``GET /v1/default/banks/{bank_id}/memories/list`` (verify).

HMS contract notes (verified at submodule pin ``a808ab393ca0``):
* ``retain`` runs an LLM internally (one item in → potentially N memory_units
  out) and does NOT return the created unit ids. The ingest pipeline reconciles
  via :meth:`list_memories` + a ``document_id`` correlation key.
* ``recall`` returns ranked results but **strips the relevance score** — MP
  ranks/caps client-side using ``policy.retrieval.max_memories_per_response``.
* ``metadata`` values must be strings; ``tags`` is free-form (no pre-creation).
* The literal ``default`` path segment is a fixed HMS namespace, not a tenant.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

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

    async def retain(
        self,
        bank_id: str,
        items: list[dict[str, Any]],
        *,
        async_: bool = False,
    ) -> dict[str, Any]:
        """POST /v1/default/banks/{bank_id}/memories — ingest one or more items.

        HMS runs the LLM extraction/embedding/dedup internally. Each item should
        carry a ``document_id`` correlation key (we set it to the MP event_id)
        so the caller can reconcile the created memory_units via
        :meth:`list_memories` — HMS's retain response carries no unit ids.

        ``async_`` controls HMS's own async mode (JSON key is literally
        ``async``). MP uses sync retains so the response is final by the time
        the handler returns.

        Returns the HMS ``RetainResponse`` (``success``, ``items_count``,
        ``usage``, …). Raises :class:`HmsError` on transport/HTTP failure.
        """
        url = f"{self._base_url}/v1/default/banks/{bank_id}/memories"
        body: dict[str, Any] = {"items": items, "async": async_}
        try:
            async with self._client() as client:
                resp = await client.post(url, json=body, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HmsError(f"HMS retain({bank_id}) failed: {exc}") from exc

    async def recall(
        self,
        bank_id: str,
        *,
        query: str,
        types: list[str] | None = None,
        budget: str = "mid",
        tags: list[str] | None = None,
        tags_match: str = "any",
        include_trace: bool = False,
    ) -> dict[str, Any]:
        """POST /v1/default/banks/{bank_id}/memories/recall — semantic search.

        Returns ``{"results": [RecallResult, ...], "trace"?: {...}}``. Each
        result has ``id``, ``text``, ``type``, ``entities``, ``context``,
        ``tags``, ``document_id`` — but NO relevance score (HMS strips it).
        Ranking is implicit in the result order.

        ``types`` filters HMS fact types (``world``/``experience``/``observation``).
        ``tags`` + ``tags_match`` filter by visibility-scope tags set at retain
        (``any`` includes untagged; ``any_strict`` requires at least one tag).
        """
        url = f"{self._base_url}/v1/default/banks/{bank_id}/memories/recall"
        body: dict[str, Any] = {
            "query": query,
            "budget": budget,
            "trace": include_trace,
            "tags_match": tags_match,
        }
        if types is not None:
            body["types"] = types
        if tags is not None:
            body["tags"] = tags
        try:
            async with self._client() as client:
                resp = await client.post(url, json=body, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HmsError(f"HMS recall({bank_id}) failed: {exc}") from exc

    async def list_memories(
        self,
        bank_id: str,
        *,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """GET /v1/default/banks/{bank_id}/memories/list — list memory_units.

        Used by the ingest pipeline to reconcile the units HMS created from a
        retain (HMS retain returns no ids). ``q`` is an ILIKE over text+context
        — for document_id-based correlation, list a wide window then filter
        client-side on ``document_id`` (the field is present on each item).

        Returns ``{"items": [...], "total", "limit", "offset"}``. Each item has
        ``id``, ``text``, ``context``, ``document_id``, ``fact_type``,
        ``mentioned_at``, ``tags``, …
        """
        url = f"{self._base_url}/v1/default/banks/{bank_id}/memories/list"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        try:
            async with self._client() as client:
                resp = await client.get(url, params=params, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HmsError(f"HMS list_memories({bank_id}) failed: {exc}") from exc

    async def update_document_tags(
        self,
        bank_id: str,
        document_id: str,
        tags: list[str],
    ) -> dict[str, Any]:
        """PATCH the tags on an HMS source document."""
        encoded_document_id = quote(document_id, safe="")
        url = (
            f"{self._base_url}/v1/default/banks/{bank_id}/documents/"
            f"{encoded_document_id}"
        )
        try:
            async with self._client() as client:
                resp = await client.patch(url, json={"tags": tags}, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HmsError(
                f"HMS update_document_tags({bank_id}, {document_id}) failed: {exc}"
            ) from exc

    async def delete_document(self, bank_id: str, document_id: str) -> dict[str, Any]:
        """DELETE an HMS document and its derived memory units."""
        encoded_document_id = quote(document_id, safe="")
        url = (
            f"{self._base_url}/v1/default/banks/{bank_id}/documents/"
            f"{encoded_document_id}"
        )
        try:
            async with self._client() as client:
                resp = await client.delete(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HmsError(f"HMS delete_document({bank_id}, {document_id}) failed: {exc}") from exc

    async def delete_bank(self, bank_id: str) -> dict[str, Any]:
        """DELETE an HMS bank and all of its data."""
        url = f"{self._base_url}/v1/default/banks/{bank_id}"
        try:
            async with self._client() as client:
                resp = await client.delete(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HmsError(f"HMS delete_bank({bank_id}) failed: {exc}") from exc

    def _client(self) -> httpx.AsyncClient:
        """Build a short-lived client.

        ``trust_env=False`` so the MP→hms-api call stays on the internal docker
        network and never picks up host HTTP_PROXY/ALL_PROXY env vars (which
        would otherwise leak into the container and break the internal call).
        """
        return httpx.AsyncClient(timeout=self._timeout, trust_env=False)


__all__ = ["HmsClient", "HmsError"]
