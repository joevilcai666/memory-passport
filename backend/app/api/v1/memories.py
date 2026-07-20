"""Memory CRUD plus the semantic retrieve endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.config import get_settings
from app.hms import HmsClient, HmsError
from app.models.enums import MemoryScope, MemoryStatus, MemoryType
from app.schemas.memory_crud import MemoryListResponse, MemoryPatch, MemoryRecordResponse
from app.schemas.retrieve import RetrievedMemory, RetrieveRequest, RetrieveResponse
from app.services.memory_crud import (
    MemoryFilters,
    delete_memory,
    edit_memory,
    list_memories,
    transition_memory,
)
from app.services.retrieve import retrieve_memories

router = APIRouter(prefix="/v1/memories", tags=["retrieve"])


def _hms_client() -> HmsClient:
    settings = get_settings()
    return HmsClient(base_url=settings.hms_api_url, api_key=settings.hms_api_key)


@router.get("", response_model=MemoryListResponse)
def get_memories(
    db: Session = DbDep,
    tenant=TenantDep,
    user_id: str | None = None,
    type: MemoryType | None = None,
    status_filter: Annotated[MemoryStatus | None, Query(alias="status")] = None,
    scope: MemoryScope | None = None,
    relationship_id: str | None = None,
    agent_id: str | None = None,
    device_id: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    include_deleted: bool = False,
) -> MemoryListResponse:
    result = list_memories(
        db,
        tenant.tenant.id,
        MemoryFilters(
            user_id=user_id,
            type=type,
            status=status_filter,
            scope=scope,
            relationship_id=relationship_id,
            agent_id=agent_id,
            device_id=device_id,
        ),
        page,
        page_size,
        include_deleted,
    )
    return MemoryListResponse(**result.__dict__)


@router.patch("/{memory_id}", response_model=MemoryRecordResponse)
async def patch_memory(
    memory_id: str,
    body: MemoryPatch,
    db: Session = DbDep,
    tenant=TenantDep,
) -> MemoryRecordResponse:
    try:
        if body.content is not None:
            record = await edit_memory(db, tenant, _hms_client(), memory_id, body.content)
        else:
            assert body.status is not None
            record = await transition_memory(db, tenant, _hms_client(), memory_id, body.status)
    except HmsError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hms_mutation_failed", "message": str(exc)},
        ) from exc
    db.commit()
    db.refresh(record)
    return MemoryRecordResponse.model_validate(record)


@router.delete("/{memory_id}", response_model=MemoryRecordResponse)
async def remove_memory(
    memory_id: str,
    db: Session = DbDep,
    tenant=TenantDep,
) -> MemoryRecordResponse:
    try:
        record = await delete_memory(db, tenant, _hms_client(), memory_id)
    except HmsError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hms_mutation_failed", "message": str(exc)},
        ) from exc
    db.commit()
    db.refresh(record)
    return MemoryRecordResponse.model_validate(record)


@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    status_code=status.HTTP_200_OK,
)
async def retrieve(
    body: RetrieveRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> RetrieveResponse:
    try:
        outcome = await retrieve_memories(
            db,
            tenant,
            hms_client=_hms_client(),
            user_id=body.user_id,
            agent_id=body.agent_id,
            relationship_id=body.relationship_id,
            query=body.query,
            model=body.model,
            device_id=body.device_id,
        )
    except HmsError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hms_recall_failed", "message": str(exc)},
        ) from exc

    db.commit()
    return RetrieveResponse(
        trace_id=outcome.trace_id,
        results=[RetrievedMemory(**p) for p in outcome.projected],
    )
