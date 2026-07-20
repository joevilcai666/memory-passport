"""POST /v1/policies — authoritative policy create/update."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.schemas.policies import PolicyResponse, PolicyUpsertRequest
from app.services.policies import upsert_policy

router = APIRouter(prefix="/v1/policies", tags=["policies"])


@router.post("", response_model=PolicyResponse)
def post_policy(
    body: PolicyUpsertRequest,
    response: Response,
    db: Session = DbDep,
    tenant=TenantDep,
) -> PolicyResponse:
    outcome = upsert_policy(db, tenant, body)
    db.commit()
    db.refresh(outcome.policy)
    response.status_code = (
        status.HTTP_201_CREATED if outcome.created else status.HTTP_200_OK
    )
    return PolicyResponse.model_validate(outcome.policy)


__all__ = ["router"]
