"""Tenant webhook endpoints and immutable delivery records — issue #33.

Mirrors the AuditLog/AuditAction pattern: every subscribed lifecycle event
writes an immutable :class:`WebhookDelivery` row, which a background task
delivers to the tenant's configured HTTPS destination with an HMAC signature.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, jsonb, text_array
from app.models.enums import (
    PG_WEBHOOK_DELIVERY_STATUS,
    PG_WEBHOOK_EVENT_TYPE,
    WebhookDeliveryStatus,
    WebhookEventType,
)


class WebhookEndpoint(Base):
    """A tenant's configured HTTPS webhook destination.

    Only the SHA-256 hash of the one-time signing secret is stored; the
    plaintext secret is returned exactly once at creation time (mirrors the
    team-invite token-hash pattern).
    """

    __tablename__ = "webhook_endpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    signing_secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    events: Mapped[list[str]] = mapped_column(text_array(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<WebhookEndpoint {self.id} ({self.url})>"


class WebhookDelivery(Base):
    """An immutable, at-least-once delivery record for one lifecycle event.

    Created at the lifecycle hook point (beside ``write_audit``); a background
    task delivers it and persists the terminal status. ``event_id`` is globally
    unique so receivers can deduplicate under at-least-once semantics.
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint_id: Mapped[str] = mapped_column(
        ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[WebhookEventType] = mapped_column(
        PG_WEBHOOK_EVENT_TYPE, nullable=False
    )
    payload: Mapped[dict] = mapped_column(jsonb(), nullable=False)
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        PG_WEBHOOK_DELIVERY_STATUS,
        nullable=False,
        default=WebhookDeliveryStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_webhook_deliveries_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<WebhookDelivery {self.event_id} ({self.event_type})>"


__all__ = ["WebhookDelivery", "WebhookEndpoint"]
