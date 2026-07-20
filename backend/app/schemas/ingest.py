"""Schemas for POST /v1/events/ingest (Slice 3).

Request mirrors the raw-event shape the frontend's ``runTestEvent`` quickstart
action produces; response mirrors what that action expects
(``{event_id, results:[{id, action}]}``).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ID

# The per-fact action taken by the ingest pipeline. Matches the values the
# frontend's quickstart flow keys on (ADD / UPDATE / NOOP / BLOCKED).
IngestAction = Literal["ADD", "UPDATE", "NOOP", "BLOCKED"]


class IngestEventRequest(BaseModel):
    """POST /v1/events/ingest — a raw event to be turned into memories."""

    user_id: ID
    agent_id: ID
    relationship_id: ID
    device_id: ID | None = None
    source_type: str = Field(
        ...,
        description="One of: chat, voice, setup, explicit_instruction, robot_event, app_event",
    )
    content: str = Field(..., min_length=1, description="The raw event text to remember.")
    quote: str | None = Field(
        None,
        description=(
            "The exact user utterance (defaults to content). "
            "Preserved verbatim as source.quote."
        ),
    )
    event_id: str | None = Field(
        None,
        description="Optional client-supplied idempotency/correlation key. Generated if omitted.",
    )


class IngestResultItem(BaseModel):
    """One entry per resulting memory — the id + what happened to it."""

    id: ID
    action: IngestAction


class IngestEventResponse(BaseModel):
    """The response shape the frontend quickstart action expects."""

    event_id: str
    results: list[IngestResultItem]


__all__ = ["IngestAction", "IngestEventRequest", "IngestEventResponse", "IngestResultItem"]
