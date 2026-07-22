"""Request + response schemas for the Slice 2 provisioning endpoints.

Response models mirror the interfaces in ``src/lib/types.ts`` 1:1 (field names,
types, optionality). Request models are the strict subset each endpoint accepts
— server-generated fields (id, created_at, passport_id, …) never appear in a
request body.

Endpoint → response map:
    POST /v1/apps               -> AppCreateResponse  ({ app, api_key })
    POST /v1/agents             -> AgentResponse
    POST /v1/users              -> UserResponse
    POST /v1/relationships      -> RelationshipResponse
    POST /v1/devices/register   -> DeviceRegisterResponse ({ device, pairing_code })
    POST /v1/devices/bind       -> DeviceResponse
    POST /v1/devices/unbind     -> DeviceResponse
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    AgeGroup,
    AgentType,
    AppStatus,
    DataRegion,
    DeviceStatus,
    Environment,
    ProductType,
    RelationshipType,
)
from app.schemas.common import ID, _OrmModel

# ---------------------------------------------------------------------------
# Response models (mirror types.ts interfaces exactly)
# ---------------------------------------------------------------------------


class TenantResponse(_OrmModel):
    """``Tenant`` — see src/lib/types.ts:11."""

    id: ID
    name: str
    plan: str
    created_at: datetime


class ApiKeyResponse(_OrmModel):
    """``ApiKey`` — see src/lib/types.ts:34.

    ``key`` is returned in full only once (on App creation); other flows return
    it too because the B side owns/rotates its own keys.
    """

    id: ID
    label: str
    environment: Environment
    key: str
    created_at: datetime
    last_used_at: datetime | None = None


class ApiKeyMaskedResponse(_OrmModel):
    """Key metadata safe for repeated list/detail responses."""

    id: ID
    label: str
    environment: Environment
    masked_key: str
    created_at: datetime
    last_used_at: datetime | None = None


class AppResponse(_OrmModel):
    """``App`` — see src/lib/types.ts:21.

    ``api_keys`` is omitted from the provisioning response to keep the create
    payload small; the dedicated ``POST /v1/apps`` returns the new key alongside.
    """

    id: ID
    tenant_id: ID
    name: str
    product_type: ProductType
    environment: Environment
    data_region: DataRegion
    show_powered_by: bool
    status: AppStatus
    created_at: datetime


class AppDetailResponse(AppResponse):
    api_keys: list[ApiKeyMaskedResponse]


class AppListResponse(BaseModel):
    items: list[AppDetailResponse]


class UserResponse(_OrmModel):
    """``User`` — see src/lib/types.ts:47."""

    id: ID
    external_user_id: str
    passport_id: str
    age_group: AgeGroup
    region: str
    memory_enabled: bool
    created_at: datetime
    display_name: str
    avatar_color: str


class AgentResponse(_OrmModel):
    """``Agent`` — see src/lib/types.ts:61."""

    id: ID
    app_id: ID
    name: str
    type: AgentType
    persona_version: str
    memory_policy_id: ID | None = None
    allowed_memory_types: list[str]
    created_at: datetime
    emoji: str


class DeviceResponse(_OrmModel):
    """``Device`` — see src/lib/types.ts:77."""

    id: ID
    model: str
    generation: str
    serial_number_hash: str
    status: DeviceStatus
    bound_user_id: ID | None = None
    last_seen_at: datetime | None = None


class RelationshipResponse(_OrmModel):
    """``Relationship`` — see src/lib/types.ts:91."""

    id: ID
    user_id: ID
    agent_id: ID
    device_id: ID | None = None
    relationship_type: RelationshipType
    memory_enabled: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AppCreateRequest(BaseModel):
    """POST /v1/apps — create an App under the caller's tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    product_type: ProductType
    environment: Environment
    data_region: DataRegion
    show_powered_by: bool = True


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    environment: Environment


class AgentCreateRequest(BaseModel):
    """POST /v1/agents — create an Agent under an App."""

    app_id: ID
    name: str = Field(..., min_length=1, max_length=255)
    type: AgentType
    persona_version: str = Field(..., min_length=1, max_length=64)
    allowed_memory_types: list[str] = Field(default_factory=list)
    emoji: str = Field(default="🤖", max_length=16)


class UserCreateRequest(BaseModel):
    """POST /v1/users — create or sync a User under an App.

    Idempotent on ``(app_id, external_user_id)``: a second call with the same
    pair returns the existing user and does NOT call HMS again.
    """

    app_id: ID
    external_user_id: str = Field(..., min_length=1, max_length=255)
    age_group: AgeGroup = AgeGroup.UNKNOWN
    region: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=255)


class UserConsentRequest(BaseModel):
    """PATCH /v1/users/{user_id}/consent — set explicit memory consent."""

    memory_enabled: bool


class RelationshipCreateRequest(BaseModel):
    """POST /v1/relationships — link a user × agent (+ optional device)."""

    user_id: ID
    agent_id: ID
    device_id: ID | None = None
    relationship_type: RelationshipType
    memory_enabled: bool = True


class DeviceRegisterRequest(BaseModel):
    """POST /v1/devices/register — register a device (status=registered)."""

    model: str = Field(..., min_length=1, max_length=255)
    generation: str = Field(..., min_length=1, max_length=32)
    serial_number_hash: str = Field(..., min_length=1, max_length=128)


class DeviceBindRequest(BaseModel):
    """POST /v1/devices/bind — bind a registered device to a user.

    ``pairing_code`` is the one-time code returned by /register (PRD §9.1
    device authorization — anonymous binds are rejected by the schema itself,
    since ``user_id`` is required).
    """

    device_id: ID
    user_id: ID
    pairing_code: str = Field(..., min_length=1, max_length=128)


class DeviceUnbindRequest(BaseModel):
    """POST /v1/devices/unbind — unbind a bound device."""

    device_id: ID


class DeviceWipeRequest(BaseModel):
    """POST /v1/devices/wipe — factory-reset a bound device."""

    device_id: ID


# ---------------------------------------------------------------------------
# Composite responses
# ---------------------------------------------------------------------------


class AppCreateResponse(BaseModel):
    """POST /v1/apps returns the new App + its first auto-generated ApiKey."""

    app: AppResponse
    api_key: ApiKeyResponse


class DeviceRegisterResponse(BaseModel):
    """POST /v1/devices/register returns the device + the one-time pairing code."""

    device: DeviceResponse
    pairing_code: str


class DeviceWipeResponse(BaseModel):
    """POST /v1/devices/wipe returns the wiped device + tombstone count."""

    device: DeviceResponse
    tombstoned_memories: int


__all__ = [
    "AgentCreateRequest",
    "AgentResponse",
    "ApiKeyResponse",
    "ApiKeyCreateRequest",
    "ApiKeyMaskedResponse",
    "AppCreateRequest",
    "AppCreateResponse",
    "AppDetailResponse",
    "AppListResponse",
    "AppResponse",
    "DeviceBindRequest",
    "DeviceRegisterRequest",
    "DeviceRegisterResponse",
    "DeviceResponse",
    "DeviceUnbindRequest",
    "DeviceWipeRequest",
    "DeviceWipeResponse",
    "RelationshipCreateRequest",
    "RelationshipResponse",
    "TenantResponse",
    "UserCreateRequest",
    "UserConsentRequest",
    "UserResponse",
]
