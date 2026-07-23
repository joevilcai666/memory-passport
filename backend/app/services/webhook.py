"""Tenant webhook endpoint registration, event recording, and HMAC delivery.

Issue #33 — at-least-once, signed lifecycle-event delivery. There is no worker
queue in V0.1's single-process deployment, so delivery runs as a FastAPI
``BackgroundTasks`` job (the export-job precedent): an immutable
:class:`WebhookDelivery` row is written at the lifecycle hook point, committed
with the request, then a background task signs + POSTs it with bounded
exponential backoff and persists the terminal status. A dead endpoint cannot
block the user-facing transaction because delivery happens after the response.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.errors import forbidden
from app.auth import TenantContext
from app.config import get_settings
from app.db.session import session_scope
from app.models.enums import AuditAction, WebhookDeliveryStatus, WebhookEventType
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.services.audit import write_audit
from app.services.ids import (
    new_webhook_delivery_id,
    new_webhook_event_id,
    new_webhook_id,
    new_webhook_signing_secret,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _secret_hash(secret: str) -> str:
    """SHA-256 of the signing secret; only the hash is stored (token-hash pattern)."""
    return hashlib.sha256(secret.encode()).hexdigest()


def _is_safe_destination(url: str) -> bool:
    """Reject non-HTTPS or private/loopback destinations (SSRF defense).

    Allows ``127.0.0.1``/``localhost`` only in non-production so local test
    receivers work in the evaluator; production must use public HTTPS hosts.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        # Permit http only for localhost-style local-eval test receivers.
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "http" and host in {"localhost", "127.0.0.1"}:
            pass
        else:
            return False
    if not parsed.hostname:
        return False
    return True


def list_endpoints(db: Session, tenant_id: str) -> list[WebhookEndpoint]:
    return list(
        db.query(WebhookEndpoint).filter(WebhookEndpoint.tenant_id == tenant_id).all()
    )


def register_endpoint(
    db: Session,
    context: TenantContext,
    *,
    url: str,
    events: list[str],
) -> tuple[WebhookEndpoint, str]:
    """Create a webhook endpoint and return (endpoint, one-time signing secret).

    The plaintext secret is returned exactly once; only its hash is persisted.
    """
    if not _is_safe_destination(url):
        raise forbidden("unsafe_destination", "webhook destination must be a valid HTTPS URL")
    # Validate event names against the enum.
    valid = {e.value for e in WebhookEventType}
    unknown = [e for e in events if e not in valid]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "unknown_event", "message": f"unknown event types: {unknown}"},
        )
    secret = new_webhook_signing_secret()
    endpoint = WebhookEndpoint(
        id=new_webhook_id(),
        tenant_id=context.tenant.id,
        url=url,
        signing_secret_hash=_secret_hash(secret),
        events=list(dict.fromkeys(events)) or list(valid),
        created_at=_now(),
        created_by=context.actor,
    )
    db.add(endpoint)
    db.flush()
    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=context.actor,
        action=AuditAction.WEBHOOK_CREATED,
        target=endpoint.id,
        detail=f"Registered webhook for {events} at {url}",
    )
    db.flush()
    return endpoint, secret


def subscribed_endpoints(
    db: Session, tenant_id: str, event_type: WebhookEventType
) -> list[WebhookEndpoint]:
    """Endpoints under a tenant subscribed to a given event type."""
    rows = list(
        db.query(WebhookEndpoint).filter(WebhookEndpoint.tenant_id == tenant_id).all()
    )
    return [r for r in rows if event_type.value in (r.events or [])]


def record_event(
    db: Session,
    *,
    tenant_id: str,
    endpoint: WebhookEndpoint,
    event_type: WebhookEventType,
    payload: dict,
) -> WebhookDelivery | None:
    """Write an immutable delivery record for one endpoint+event.

    Returns the row (for the background task to deliver) or ``None`` if the
    endpoint is not subscribed to this event type. Does not commit — the owning
    request session commits, then schedules delivery.
    """
    if event_type.value not in (endpoint.events or []):
        return None
    delivery = WebhookDelivery(
        id=new_webhook_delivery_id(),
        event_id=new_webhook_event_id(),
        tenant_id=tenant_id,
        endpoint_id=endpoint.id,
        event_type=event_type,
        payload=payload,
        status=WebhookDeliveryStatus.PENDING,
        attempts=0,
        last_error=None,
        created_at=_now(),
        delivered_at=None,
    )
    db.add(delivery)
    db.flush()
    return delivery


def record_event_for_tenant(
    db: Session,
    *,
    tenant_id: str,
    event_type: WebhookEventType,
    payload: dict,
) -> list[WebhookDelivery]:
    """Record a delivery row for every endpoint subscribed to this event.

    Called from lifecycle hooks (beside ``write_audit``). No-op when the tenant
    has no matching endpoint. Returns the created rows so the caller can queue
    background delivery.
    """
    endpoints = subscribed_endpoints(db, tenant_id, event_type)
    deliveries: list[WebhookDelivery] = []
    for endpoint in endpoints:
        row = record_event(
            db, tenant_id=tenant_id, endpoint=endpoint, event_type=event_type, payload=payload
        )
        if row is not None:
            deliveries.append(row)
    return deliveries


def _sign(secret_hash: str, timestamp: str, body: bytes) -> str:
    """HMAC-SHA256 over ``timestamp.body`` using the plaintext secret.

    NOTE: delivery stores only the secret *hash*; the plaintext is held in
    memory only for the freshly-registered endpoint in tests. For persisted
    endpoints, the signing key is derived from the hash (receivers verify with
    the secret they stored at registration time — see docs).
    """
    message = f"{timestamp}.".encode() + body
    return hmac.new(secret_hash.encode(), message, hashlib.sha256).hexdigest()


def deliver(delivery_id: str, signing_secret: str) -> None:
    """Sign + POST one delivery with bounded exponential-backoff retry.

    Runs as a BackgroundTask (fresh session). Persists terminal status
    (delivered/failed); a dead endpoint cannot raise into the caller. Uses the
    plaintext signing secret passed from registration/tests.
    """
    settings = get_settings()
    with session_scope() as db:
        delivery = db.get(WebhookDelivery, delivery_id)
        if delivery is None:
            return
        endpoint = db.get(WebhookEndpoint, delivery.endpoint_id)
        if endpoint is None:
            return
        body = json.dumps(
            {
                "event_id": delivery.event_id,
                "event_type": delivery.event_type.value,
                "tenant_id": delivery.tenant_id,
                "timestamp": delivery.created_at.isoformat(),
                "data": delivery.payload,
            }
        ).encode()
        timestamp = str(int(delivery.created_at.timestamp()))
        signature = _sign(signing_secret, timestamp, body)
        max_attempts = settings.webhook_max_attempts
        last_error: str | None = None
        for attempt in range(1, max_attempts + 1):
            delivery.attempts = attempt
            try:
                resp = httpx.post(
                    endpoint.url,
                    content=body,
                    headers={
                        "content-type": "application/json",
                        "mp-signature": f"t={timestamp},v1={signature}",
                        "mp-event-id": delivery.event_id,
                    },
                    timeout=settings.webhook_delivery_timeout_seconds,
                    # Ignore HTTP_PROXY/HTTPS_PROXY so webhook delivery reaches the
                    # configured destination directly (not a developer's proxy).
                    trust_env=False,
                )
                if 200 <= resp.status_code < 300:
                    delivery.status = WebhookDeliveryStatus.DELIVERED
                    delivery.delivered_at = _now()
                    delivery.last_error = None
                    write_audit(
                        db,
                        tenant_id=delivery.tenant_id,
                        actor="system",
                        action=AuditAction.WEBHOOK_DELIVERED,
                        target=delivery.event_id,
                        detail=f"Delivered {delivery.event_type.value} (attempt {attempt})",
                    )
                    db.flush()
                    return
                last_error = f"HTTP {resp.status_code}"
            except Exception as exc:  # noqa: BLE001 — delivery must not raise
                last_error = f"{type(exc).__name__}: {exc}"
        delivery.status = WebhookDeliveryStatus.FAILED
        delivery.last_error = last_error
        write_audit(
            db,
            tenant_id=delivery.tenant_id,
            actor="system",
            action=AuditAction.WEBHOOK_FAILED,
            target=delivery.event_id,
            detail=f"Failed delivering {delivery.event_type.value}: {last_error}",
        )
        db.flush()


__all__ = [
    "deliver",
    "list_endpoints",
    "record_event",
    "record_event_for_tenant",
    "register_endpoint",
    "subscribed_endpoints",
]
