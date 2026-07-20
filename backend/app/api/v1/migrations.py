"""HTTP routes for the reversible device migration wedge."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.schemas.migrations import (
    MigrationExecuteRequest,
    MigrationPreviewRequest,
    MigrationPreviewResponse,
    MigrationResponse,
)
from app.services.migrations import (
    execute_migration,
    get_migration,
    preview_migration,
    rollback_migration,
)

router = APIRouter(prefix="/v1/migrations", tags=["migrations"])


@router.post("/preview", response_model=MigrationPreviewResponse)
def post_preview(
    body: MigrationPreviewRequest,
    response: Response,
    db: Session = DbDep,
    tenant=TenantDep,
) -> MigrationPreviewResponse:
    outcome = preview_migration(db, tenant, body)
    db.commit()
    response.status_code = status.HTTP_201_CREATED if outcome.created else status.HTTP_200_OK
    return outcome.response


@router.post("/execute", response_model=MigrationResponse)
def post_execute(
    body: MigrationExecuteRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> MigrationResponse:
    migration = execute_migration(db, tenant, body)
    db.commit()
    db.refresh(migration)
    return MigrationResponse.model_validate(migration)


@router.get("/{migration_id}", response_model=MigrationResponse)
def read_migration(
    migration_id: str,
    db: Session = DbDep,
    tenant=TenantDep,
) -> MigrationResponse:
    return MigrationResponse.model_validate(
        get_migration(db, tenant.tenant.id, migration_id)
    )


@router.post("/{migration_id}/rollback", response_model=MigrationResponse)
def post_rollback(
    migration_id: str,
    db: Session = DbDep,
    tenant=TenantDep,
) -> MigrationResponse:
    migration = rollback_migration(db, tenant, migration_id)
    db.commit()
    db.refresh(migration)
    return MigrationResponse.model_validate(migration)


__all__ = ["router"]
