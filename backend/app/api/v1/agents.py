"""POST /v1/agents — create an Agent under an App."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.schemas.provisioning import AgentCreateRequest, AgentResponse
from app.services import provisioning

router = APIRouter(prefix="/v1", tags=["provisioning"])


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreateRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> AgentResponse:
    agent = provisioning.create_agent(
        db,
        tenant,
        app_id=body.app_id,
        name=body.name,
        type=body.type,
        persona_version=body.persona_version,
        allowed_memory_types=body.allowed_memory_types,
        emoji=body.emoji,
    )
    db.commit()
    return AgentResponse.model_validate(agent)
