"""HTTP endpoints for exports and delete-user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.config import get_settings
from app.hms import HmsClient, HmsError
from app.schemas.data_ops import (
    DeleteUserRequest,
    DeleteUserResponse,
    ExportCreateRequest,
    ExportCreateResponse,
    ExportStatusResponse,
)
from app.services.data_ops import (
    create_export_job,
    delete_user,
    get_export_status,
    resolve_export_download,
    run_export_job,
)

router = APIRouter(prefix="/v1", tags=["data-operations"])


def _hms_client() -> HmsClient:
    settings = get_settings()
    return HmsClient(base_url=settings.hms_api_url, api_key=settings.hms_api_key)


@router.post(
    "/exports",
    response_model=ExportCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def post_export(
    body: ExportCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = DbDep,
    tenant=TenantDep,
) -> ExportCreateResponse:
    job = create_export_job(db, tenant, body.user_id)
    db.commit()
    background_tasks.add_task(run_export_job, job.id)
    return ExportCreateResponse(export_id=job.id)


@router.get("/exports/{export_id}", response_model=ExportStatusResponse)
def read_export(
    export_id: str,
    db: Session = DbDep,
    tenant=TenantDep,
) -> ExportStatusResponse:
    return get_export_status(db, tenant.tenant.id, export_id)


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: str,
    token: Annotated[str, Query(min_length=1)],
    db: Session = DbDep,
    tenant=TenantDep,
) -> FileResponse:
    artifact = resolve_export_download(db, tenant.tenant.id, export_id, token)
    # Persist the one-shot token clear before streaming the artifact so a
    # replay can't pick up the same token on another worker. See issue #13.
    db.commit()
    return FileResponse(
        artifact,
        media_type="application/json",
        filename=f"memory-passport-{export_id}.json",
    )


@router.post("/delete_user", response_model=DeleteUserResponse)
async def post_delete_user(
    body: DeleteUserRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> DeleteUserResponse:
    try:
        response = await delete_user(db, tenant, _hms_client(), body.user_id)
    except HmsError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hms_bank_delete_failed", "message": str(exc)},
        ) from exc
    db.commit()
    return response


__all__ = ["router"]
