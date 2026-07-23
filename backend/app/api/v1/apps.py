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
    ApiKeyCreateRequest,
    ApiKeyMaskedResponse,
    ApiKeyResponse,
    AppCreateRequest,
    AppCreateResponse,
    AppDetailResponse,
    AppListResponse,
    AppResponse,
)
from app.services import provisioning

router = APIRouter(prefix="/v1", tags=["provisioning"])


def _app_detail(app) -> AppDetailResponse:
    base = AppResponse.model_validate(app)
    return AppDetailResponse(
        **base.model_dump(),
        api_keys=[
            ApiKeyMaskedResponse.model_validate(key)
            for key in sorted(app.api_keys, key=lambda item: (item.created_at, item.id))
        ],
    )


@router.get("/apps", response_model=AppListResponse)
def read_apps(db: Session = DbDep, tenant=TenantDep) -> AppListResponse:
    return AppListResponse(
        items=[_app_detail(app) for app in provisioning.list_apps(db, tenant)]
    )


@router.get("/apps/{app_id}", response_model=AppDetailResponse)
def read_app(
    app_id: str,
    db: Session = DbDep,
    tenant=TenantDep,
) -> AppDetailResponse:
    return _app_detail(provisioning.get_app(db, tenant, app_id))


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


@router.post(
    "/apps/{app_id}/api-keys",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_key(
    app_id: str,
    body: ApiKeyCreateRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> ApiKeyResponse:
    key = provisioning.create_api_key(
        db,
        tenant,
        app_id=app_id,
        label=body.label,
        environment=body.environment,
    )
    db.commit()
    return ApiKeyResponse.model_validate(key)


@router.post(
    "/apps/{app_id}/api-keys/{key_id}/rotate",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
def rotate_key(
    app_id: str,
    key_id: str,
    db: Session = DbDep,
    tenant=TenantDep,
) -> ApiKeyResponse:
    key = provisioning.rotate_api_key(
        db,
        tenant,
        app_id=app_id,
        key_id=key_id,
    )
    db.commit()
    return ApiKeyResponse.model_validate(key)
