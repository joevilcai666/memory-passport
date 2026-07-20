"""Device provisioning endpoints — register / bind / unbind.

State machine (PRD §9.1):

    registered --bind-->   bound    --unbind--> unbound

``bind`` requires the one-time pairing code issued at ``register`` (anonymous or
code-less binds are rejected with 403). ``wipe`` and ``transfer`` are deferred
to later slices. Each transition writes an AuditLog row.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.schemas.provisioning import (
    DeviceBindRequest,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceResponse,
    DeviceUnbindRequest,
)
from app.services import provisioning

router = APIRouter(prefix="/v1/devices", tags=["provisioning"])


@router.post(
    "/register",
    response_model=DeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_device(
    body: DeviceRegisterRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> DeviceRegisterResponse:
    device, pairing_code = provisioning.register_device(
        db,
        tenant,
        model=body.model,
        generation=body.generation,
        serial_number_hash=body.serial_number_hash,
    )
    db.commit()
    return DeviceRegisterResponse(
        device=DeviceResponse.model_validate(device),
        pairing_code=pairing_code,
    )


@router.post("/bind", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
def bind_device(
    body: DeviceBindRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> DeviceResponse:
    device = provisioning.bind_device(
        db,
        tenant,
        device_id=body.device_id,
        user_id=body.user_id,
        pairing_code=body.pairing_code,
    )
    db.commit()
    return DeviceResponse.model_validate(device)


@router.post("/unbind", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
def unbind_device(
    body: DeviceUnbindRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> DeviceResponse:
    device = provisioning.unbind_device(db, tenant, device_id=body.device_id)
    db.commit()
    return DeviceResponse.model_validate(device)
