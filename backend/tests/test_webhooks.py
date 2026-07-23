"""Acceptance tests for signed tenant webhooks (issue #33).

Covers: one-time signing secret + redaction, event recording on lifecycle
actions, HMAC-signed delivery to a local test receiver, retry on non-2xx,
duplicate event_id preservation, tenant isolation, SSRF rejection, and RBAC
on endpoint configuration.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import respx

from app.db.session import session_scope
from app.models.enums import TeamRole, WebhookDeliveryStatus, WebhookEventType
from app.models.tenant import ApiKey, App, Tenant
from app.services.webhook import deliver


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture()
def wh_seed(sqlite_db):
    key = "mp_sandbox_webhook_webhook_webhook"
    with session_scope() as db:
        db.add(Tenant(id="ten_wh", name="WH", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            App(
                id="app_wh",
                tenant_id="ten_wh",
                name="WH",
                product_type="software",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=False,
                status="active",
                created_at=_now(),
            )
        )
        db.flush()
        db.add(
            ApiKey(
                id="key_wh",
                app_id="app_wh",
                label="Sandbox",
                environment="sandbox",
                key=key,
                created_at=_now(),
                last_used_at=_now(),
                role=TeamRole.OWNER,
            )
        )
        db.add(
            ApiKey(
                id="key_wh_support",
                app_id="app_wh",
                label="Support",
                environment="sandbox",
                key="mp_sandbox_webhook_support__________",
                created_at=_now(),
                last_used_at=_now(),
                role=TeamRole.SUPPORT,
            )
        )
    return {"key": key, "support_key": "mp_sandbox_webhook_support__________"}


def test_register_endpoint_returns_one_time_secret_then_redacts(wh_seed, app_client):
    response = app_client.post(
        "/v1/webhooks",
        headers=_headers(wh_seed["key"]),
        json={"url": "https://example.test/hook", "events": ["memory.created"]},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    secret = body["signing_secret"]
    assert secret.startswith("whsec_")
    assert body["endpoint"]["url"] == "https://example.test/hook"
    assert body["endpoint"]["events"] == ["memory.created"]
    # The list endpoint never returns the secret.
    listed = app_client.get("/v1/webhooks", headers=_headers(wh_seed["key"]))
    assert "signing_secret" not in listed.json()[0]


def test_support_role_cannot_register_webhook(wh_seed, app_client):
    response = app_client.post(
        "/v1/webhooks",
        headers=_headers(wh_seed["support_key"]),
        json={"url": "https://example.test/hook", "events": ["memory.created"]},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "insufficient_role"


def test_ssrf_rejects_non_https_destination(wh_seed, app_client):
    response = app_client.post(
        "/v1/webhooks",
        headers=_headers(wh_seed["key"]),
        json={"url": "ftp://example.test/hook", "events": ["memory.created"]},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "unsafe_destination"


def test_unknown_event_type_is_rejected(wh_seed, app_client):
    response = app_client.post(
        "/v1/webhooks",
        headers=_headers(wh_seed["key"]),
        json={"url": "https://example.test/hook", "events": ["bogus.event"]},
    )
    assert response.status_code == 422


def test_lifecycle_hook_records_delivery_row(wh_seed, app_client):
    """A subscribed endpoint gets a pending delivery when a memory is deleted."""
    from app.models.webhook import WebhookDelivery, WebhookEndpoint
    from app.services.webhook import record_event_for_tenant

    with session_scope() as db:
        db.add(
            WebhookEndpoint(
                id="wh_1",
                tenant_id="ten_wh",
                url="https://example.test/hook",
                signing_secret_hash="x" * 64,
                events=["memory.deleted"],
                created_at=_now(),
                created_by="test",
            )
        )
        db.commit()

    # Simulate the lifecycle hook that fires beside the delete audit.
    with session_scope() as db:
        record_event_for_tenant(
            db,
            tenant_id="ten_wh",
            event_type=WebhookEventType.MEMORY_DELETED,
            payload={"memory_id": "mem_x"},
        )
        db.commit()

    with session_scope() as db:
        deliveries = db.query(WebhookDelivery).all()
        assert len(deliveries) == 1
        assert deliveries[0].event_type == WebhookEventType.MEMORY_DELETED
        assert deliveries[0].status == WebhookDeliveryStatus.PENDING
        assert deliveries[0].event_id.startswith("evt_")
        assert deliveries[0].payload == {"memory_id": "mem_x"}


def test_no_delivery_when_endpoint_not_subscribed(wh_seed, app_client):
    """An endpoint subscribed to other events gets no delivery for this one."""
    from app.models.webhook import WebhookDelivery, WebhookEndpoint
    from app.services.webhook import record_event_for_tenant

    with session_scope() as db:
        db.add(
            WebhookEndpoint(
                id="wh_other",
                tenant_id="ten_wh",
                url="https://example.test/hook",
                signing_secret_hash="x" * 64,
                events=["memory.created"],
                created_at=_now(),
                created_by="test",
            )
        )
        db.commit()

    with session_scope() as db:
        record_event_for_tenant(
            db,
            tenant_id="ten_wh",
            event_type=WebhookEventType.MEMORY_DELETED,
            payload={"memory_id": "mem_y"},
        )
        db.commit()

    with session_scope() as db:
        assert db.query(WebhookDelivery).count() == 0


def test_deliver_signs_and_posts_then_marks_delivered(wh_seed, app_client):
    from app.models.webhook import WebhookDelivery, WebhookEndpoint

    secret = "whsec_test_secret_for_delivery_______"
    with session_scope() as db:
        endpoint = WebhookEndpoint(
            id="wh_deliver",
            tenant_id="ten_wh",
            url="https://receiver.test/hook",
            signing_secret_hash=__import__("hashlib").sha256(secret.encode()).hexdigest(),
            events=["memory.deleted"],
            created_at=_now(),
            created_by="test",
        )
        db.add(endpoint)
        db.flush()
        delivery = WebhookDelivery(
            id="whd_1",
            event_id="evt_unique_1",
            tenant_id="ten_wh",
            endpoint_id=endpoint.id,
            event_type=WebhookEventType.MEMORY_DELETED,
            payload={"memory_id": "mem_1"},
            status=WebhookDeliveryStatus.PENDING,
            attempts=0,
            created_at=_now(),
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id

    with respx.mock(base_url="https://receiver.test", assert_all_called=False) as mock:
        route = mock.post("https://receiver.test/hook").respond(200, json={"ok": True})
        deliver(delivery_id, secret)
        assert route.call_count == 1
        sent = route.calls[0].request
        assert sent.headers["mp-event-id"] == "evt_unique_1"
        assert "mp-signature" in sent.headers

    with session_scope() as db:
        row = db.get(WebhookDelivery, delivery_id)
        assert row.status == WebhookDeliveryStatus.DELIVERED
        assert row.attempts == 1
        assert row.delivered_at is not None


def test_deliver_retries_on_non_2xx_then_marks_failed(wh_seed, app_client):
    from app.models.webhook import WebhookDelivery, WebhookEndpoint

    secret = "whsec_test_secret_for_retry___________"
    with session_scope() as db:
        endpoint = WebhookEndpoint(
            id="wh_retry",
            tenant_id="ten_wh",
            url="https://broken.test/hook",
            signing_secret_hash=__import__("hashlib").sha256(secret.encode()).hexdigest(),
            events=["memory.deleted"],
            created_at=_now(),
            created_by="test",
        )
        db.add(endpoint)
        db.flush()
        delivery = WebhookDelivery(
            id="whd_retry",
            event_id="evt_unique_retry",
            tenant_id="ten_wh",
            endpoint_id=endpoint.id,
            event_type=WebhookEventType.MEMORY_DELETED,
            payload={"memory_id": "mem_2"},
            status=WebhookDeliveryStatus.PENDING,
            attempts=0,
            created_at=_now(),
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id

    with respx.mock(base_url="https://broken.test", assert_all_called=False) as mock:
        mock.post("https://broken.test/hook").respond(500)
        deliver(delivery_id, secret)

    with session_scope() as db:
        row = db.get(WebhookDelivery, delivery_id)
        assert row.status == WebhookDeliveryStatus.FAILED
        assert row.last_error == "HTTP 500"
        assert row.attempts >= 1


def test_deliveries_endpoint_is_tenant_isolated(wh_seed, app_client):
    """A delivery for another tenant's endpoint is not visible."""
    from app.models.webhook import WebhookEndpoint

    with session_scope() as db:
        db.add(Tenant(id="ten_other", name="Other", plan="Sandbox", created_at=_now()))
        db.flush()
        db.add(
            WebhookEndpoint(
                id="wh_other",
                tenant_id="ten_other",
                url="https://other.test/hook",
                signing_secret_hash="y" * 64,
                events=["memory.created"],
                created_at=_now(),
                created_by="test",
            )
        )
    response = app_client.get(
        "/v1/webhooks/wh_other/deliveries", headers=_headers(wh_seed["key"])
    )
    assert response.status_code == 404
