"""Schemas for tenant webhook endpoints and delivery records (issue #33)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import WebhookDeliveryStatus, WebhookEventType
from app.schemas.common import ID, _OrmModel


class WebhookEndpointCreateRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    events: list[str] = Field(..., min_length=1)

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        return value.strip()

    @field_validator("events")
    @classmethod
    def dedupe_events(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class WebhookEndpointResponse(_OrmModel):
    id: ID
    url: str
    events: list[str]
    created_at: datetime


class WebhookEndpointCreateResponse(BaseModel):
    endpoint: WebhookEndpointResponse
    signing_secret: str  # one-time; never returned again


class WebhookDeliveryResponse(_OrmModel):
    id: ID
    event_id: str
    event_type: WebhookEventType
    status: WebhookDeliveryStatus
    attempts: int
    last_error: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None


__all__ = [
    "WebhookDeliveryResponse",
    "WebhookEndpointCreateRequest",
    "WebhookEndpointCreateResponse",
    "WebhookEndpointResponse",
]
