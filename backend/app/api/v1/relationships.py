"""POST /v1/relationships — link a user × agent (+ optional device)."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.schemas.provisioning import RelationshipCreateRequest, RelationshipResponse
from app.services import provisioning

router = APIRouter(prefix="/v1", tags=["provisioning"])


@router.post(
    "/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    body: RelationshipCreateRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> RelationshipResponse:
    rel = provisioning.create_relationship(
        db,
        tenant,
        user_id=body.user_id,
        agent_id=body.agent_id,
        device_id=body.device_id,
        relationship_type=body.relationship_type,
        memory_enabled=body.memory_enabled,
    )
    db.commit()
    return RelationshipResponse.model_validate(rel)
