"""Focused HTTP-contract tests for the MP-to-HMS client."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.hms import HmsClient


@pytest.mark.asyncio
async def test_hms_client_updates_document_tags() -> None:
    client = HmsClient("http://hms.test", "secret")
    with respx.mock(base_url="http://hms.test") as mock:
        route = mock.patch("/v1/default/banks/usr_1/documents/evt_1").mock(
            return_value=Response(200, json={"success": True})
        )
        result = await client.update_document_tags(
            "usr_1",
            "evt_1",
            ["rel:rel_1", "mp:suppressed"],
        )

    assert result == {"success": True}
    assert route.calls.last.request.headers["Authorization"] == "Bearer secret"
    assert route.calls.last.request.content == (
        b'{"tags":["rel:rel_1","mp:suppressed"]}'
    )


@pytest.mark.asyncio
async def test_hms_client_deletes_document_and_bank() -> None:
    client = HmsClient("http://hms.test", "secret")
    with respx.mock(base_url="http://hms.test") as mock:
        document = mock.delete("/v1/default/banks/usr_1/documents/evt_1").mock(
            return_value=Response(
                200,
                json={"success": True, "memory_units_deleted": 1},
            )
        )
        bank = mock.delete("/v1/default/banks/usr_1").mock(
            return_value=Response(200, json={"success": True})
        )

        assert (await client.delete_document("usr_1", "evt_1"))["success"] is True
        assert (await client.delete_bank("usr_1"))["success"] is True

    assert document.called
    assert bank.called
