"""POST /v1/memories/retrieve — the read-side counterpart to ingest (Slice 4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.config import get_settings
from app.hms import HmsClient, HmsError
from app.schemas.retrieve import RetrievedMemory, RetrieveRequest, RetrieveResponse
from app.services.retrieve import retrieve_memories

router = APIRouter(prefix="/v1/memories", tags=["retrieve"])


def _hms_client() -> HmsClient:
    settings = get_settings()
    return HmsClient(base_url=settings.hms_api_url, api_key=settings.hms_api_key)


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
