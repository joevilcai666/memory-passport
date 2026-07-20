"""Contract tests for the credential-free HMS-compatible demo service."""

from __future__ import annotations

from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer test-hms-key"}


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("HMS_API_TENANT_API_KEY", "test-hms-key")

    from app.demo_hms import create_demo_hms_app

    database_url = f"sqlite:///{tmp_path / 'demo-hms.sqlite3'}"
    return TestClient(create_demo_hms_app(database_url))


def test_demo_hms_requires_the_configured_bearer_token(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    assert client.get("/v1/default/banks").status_code == 401
    assert (
        client.get(
            "/v1/default/banks",
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )


def test_demo_hms_bank_retain_recall_and_delete_contract(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "healthy", "mode": "demo"}

    created = client.put("/v1/default/banks/usr_1", json={}, headers=AUTH)
    assert created.status_code == 200
    assert created.json()["bank_id"] == "usr_1"

    item = {
        "content": "Mia likes jasmine tea",
        "document_id": "evt_1",
        "context": "chat",
        "timestamp": "2026-07-20T12:00:00Z",
        "tags": ["rel:rel_1", "scope:relationship_only"],
        "metadata": {"memory_type": "preference", "sensitivity": "S1"},
    }
    retained = client.post(
        "/v1/default/banks/usr_1/memories",
        json={"items": [item], "async": False},
        headers=AUTH,
    )
    assert retained.status_code == 200
    assert retained.json()["success"] is True
    assert retained.json()["items_count"] == 1

    # The deterministic implementation is idempotent for the same bank,
    # document, and content, which keeps demo runs reproducible.
    duplicate = client.post(
        "/v1/default/banks/usr_1/memories",
        json={"items": [item], "async": False},
        headers=AUTH,
    )
    assert duplicate.status_code == 200

    listing = client.get(
        "/v1/default/banks/usr_1/memories/list",
        params={"limit": 1, "offset": 0},
        headers=AUTH,
    )
    assert listing.status_code == 200
    listing_body = listing.json()
    assert listing_body["total"] == 1
    assert listing_body["limit"] == 1
    assert listing_body["offset"] == 0
    assert listing_body["items"][0]["document_id"] == "evt_1"
    assert listing_body["items"][0]["text"] == "Mia likes jasmine tea"
    assert listing_body["items"][0]["id"]

    recalled = client.post(
        "/v1/default/banks/usr_1/memories/recall",
        json={
            "query": "tea",
            "tags": ["rel:rel_1"],
            "tags_match": "any",
        },
        headers=AUTH,
    )
    assert recalled.status_code == 200
    assert recalled.json()["results"] == [listing_body["items"][0]]

    unrelated = client.post(
        "/v1/default/banks/usr_1/memories/recall",
        json={"query": "snowboard", "tags_match": "any"},
        headers=AUTH,
    )
    assert unrelated.status_code == 200
    assert unrelated.json()["results"] == []

    deleted_document = client.delete(
        "/v1/default/banks/usr_1/documents/evt_1",
        headers=AUTH,
    )
    assert deleted_document.status_code == 200
    assert deleted_document.json()["memory_units_deleted"] == 1

    deleted_bank = client.delete("/v1/default/banks/usr_1", headers=AUTH)
    assert deleted_bank.status_code == 200
    assert deleted_bank.json()["success"] is True
    assert client.get("/v1/default/banks", headers=AUTH).json() == {"banks": []}


def test_demo_hms_recall_preserves_rank_and_applies_strict_tags(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.put("/v1/default/banks/usr_1", json={}, headers=AUTH)
    client.post(
        "/v1/default/banks/usr_1/memories",
        json={
            "items": [
                {
                    "content": "tea with jasmine",
                    "document_id": "evt_1",
                    "tags": ["rel:rel_1"],
                },
                {
                    "content": "tea tea with mint",
                    "document_id": "evt_2",
                    "tags": ["rel:rel_2"],
                },
            ],
            "async": False,
        },
        headers=AUTH,
    )

    response = client.post(
        "/v1/default/banks/usr_1/memories/recall",
        json={
            "query": "tea mint",
            "tags": ["rel:rel_1"],
            "tags_match": "any_strict",
        },
        headers=AUTH,
    )

    assert response.status_code == 200
    assert [row["document_id"] for row in response.json()["results"]] == ["evt_1"]
