"""POST /v1/users — create or sync a User, idempotently provisioning an HMS bank.

First call with a given ``(app_id, external_user_id)`` creates the User,
generates a ``passport_id``, and provisions an HMS bank with
``bank_id == user.id``. Subsequent calls with the same pair return the existing
User and do NOT hit HMS again (idempotent).

A failure to provision the HMS bank aborts the request (bank provisioning is a
hard dependency for users) — the service rolls back so no half-created User row
survives. HMS transport errors surface as a 502 ``hms_provisioning_failed``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.hms import HmsError, hms_client_for_tenant
from app.schemas.provisioning import UserConsentRequest, UserCreateRequest, UserResponse
from app.services import provisioning

router = APIRouter(prefix="/v1", tags=["provisioning"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> UserResponse:
    try:
        user, _created = await provisioning.create_user(
            db,
            tenant,
            app_id=body.app_id,
            external_user_id=body.external_user_id,
            age_group=body.age_group,
            region=body.region,
            display_name=body.display_name,
            hms_client=hms_client_for_tenant(tenant.tenant.hms_api_key),
        )
    except HmsError as exc:
        # Bank provisioning failed — surface as 502 so clients can distinguish
        # it from a 4xx validation error and retry cleanly.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hms_provisioning_failed", "message": str(exc)},
        ) from exc

    db.commit()
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/consent", response_model=UserResponse)
def update_user_consent(
    user_id: str,
    body: UserConsentRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> UserResponse:
    user = provisioning.set_user_consent(
        db,
        tenant,
        user_id=user_id,
        memory_enabled=body.memory_enabled,
    )
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
