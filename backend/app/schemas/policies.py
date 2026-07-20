"""Request and response schemas for authoritative memory policies."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import (
    AutoWriteAction,
    MemorySensitivity,
    MemoryType,
    PortabilityLayer,
)
from app.schemas.common import ID, _OrmModel


class AutoWriteRuleRequest(BaseModel):
    memory_type: MemoryType
    action: AutoWriteAction
    sensitivity: MemorySensitivity
    ttl_days: int | None = Field(default=None, ge=1)


class PortabilityRequest(BaseModel):
    layer: PortabilityLayer = PortabilityLayer.PORTABLE
    cross_device: bool = True
    cross_role: bool = True
    cross_model: bool = True
    cross_brand_app: bool = False


class RetrievalPolicyRequest(BaseModel):
    max_memories_per_response: int = Field(default=8, ge=1, le=100)
    include_sensitive_in_prompt: bool = False


class PolicyUpsertRequest(BaseModel):
    app_id: ID
    agent_id: ID
    auto_write_rules: list[AutoWriteRuleRequest] = Field(default_factory=list)
    portability: PortabilityRequest = Field(default_factory=PortabilityRequest)
    retrieval: RetrievalPolicyRequest = Field(default_factory=RetrievalPolicyRequest)


class AutoWriteRuleResponse(_OrmModel):
    id: ID
    memory_type: MemoryType
    action: AutoWriteAction
    sensitivity: MemorySensitivity
    ttl_days: int | None


class PolicyResponse(_OrmModel):
    id: ID
    app_id: ID
    agent_id: ID
    auto_write_rules: list[AutoWriteRuleResponse]
    portability: dict[str, object]
    retrieval: dict[str, object]


__all__ = [
    "AutoWriteRuleRequest",
    "AutoWriteRuleResponse",
    "PolicyResponse",
    "PolicyUpsertRequest",
    "PortabilityRequest",
    "RetrievalPolicyRequest",
]
