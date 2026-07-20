"""POST /v1/apps — create an App under the caller's tenant.

The caller authenticates with an existing App's key for the same tenant and
provisions an *additional* App under that tenant. The response includes the new
App's first auto-generated ApiKey (the full ``mp_<env>_<secret>`` token, shown
once — the caller must store it).
"""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.schemas.provisioning import (
    ApiKeyResponse,
    AppCreateRequest,
    AppCreateResponse,
    AppResponse,
)
from app.services import provisioning

router = APIRouter(prefix="/v1", tags=["provisioning"])


@router.post("/apps", response_model=AppCreateResponse, status_code=status.HTTP_201_CREATED)
def create_app(
    body: AppCreateRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> AppCreateResponse:
    app, api_key = provisioning.create_app(
        db,
        tenant,
        name=body.name,
        product_type=body.product_type,
        environment=body.environment,
        data_region=body.data_region,
        show_powered_by=body.show_powered_by,
    )
    db.commit()
    return AppCreateResponse(
        app=AppResponse.model_validate(app),
        api_key=ApiKeyResponse.model_validate(api_key),
    )
