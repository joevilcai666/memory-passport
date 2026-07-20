"""Schemas for POST /v1/memories/retrieve + GET /v1/debug/traces/{trace_id} (Slice 4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ID


class RetrieveRequest(BaseModel):
    """POST /v1/memories/retrieve — semantic search across a user's memories."""

    user_id: ID
    agent_id: ID
    relationship_id: ID
    query: str = Field(..., min_length=1)
    device_id: ID | None = Field(
        None,
        description=(
            "If the caller is a device, its id. device_only memories are only "
            "returned when this device is currently bound."
        ),
    )
    model: str = Field(
        "unknown",
        description=(
            "The model id making the retrieve (e.g. 'gpt-4o'). Recorded on "
            "each returned memory's model_provenance.retrieval_history."
        ),
    )


class RetrievedMemory(BaseModel):
    """One projected memory in the retrieve response (after scope + masking)."""

    id: ID
    type: str
    content: str
    scope: str
    sensitivity: str
    status: str
    confidence: float
    source: dict[str, Any]
    portability: dict[str, Any]
    model_provenance: dict[str, Any]
    usage_count: int
    last_used_at: str | None = None


class RetrieveResponse(BaseModel):
    """The retrieve response — the projected memories + a trace_id."""

    trace_id: ID
    results: list[RetrievedMemory]


class DebugTraceResponse(BaseModel):
    """GET /v1/debug/traces/{trace_id} — the full retrieval event chain."""

    id: ID
    query: str
    caller: dict[str, Any]
    hms_results: dict[str, Any]
    projected: dict[str, Any]
    retrieval_events: dict[str, Any]
    created_at: datetime


__all__ = [
    "DebugTraceResponse",
    "RetrieveRequest",
    "RetrieveResponse",
    "RetrievedMemory",
]
