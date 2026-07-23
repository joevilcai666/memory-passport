"""POST /v1/policies — authoritative policy create/update."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, OperatorOrAdminDep, TenantDep
from app.schemas.policies import PolicyResponse, PolicyUpsertRequest
from app.services.policies import get_policy, upsert_policy

router = APIRouter(prefix="/v1/policies", tags=["policies"])


@router.get("", response_model=PolicyResponse)
def read_policy(
    app_id: str,
    agent_id: str,
    db: Session = DbDep,
    tenant=TenantDep,
) -> PolicyResponse:
    return PolicyResponse.model_validate(
        get_policy(db, tenant, app_id=app_id, agent_id=agent_id)
    )


# Policy mutation is an operator-only action (issue #32 RBAC): Owner/Admin may
# change it; Support and any lower role receive 403 insufficient_role.
@router.post("", response_model=PolicyResponse, dependencies=[OperatorOrAdminDep])
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
