"""POST /v1/events/ingest — the architecture-validating tracer (Slice 3).

Accepts a raw event, runs the policy classifier, and either blocks (S3),
no-ops (dedup), or calls HMS retain + mirrors the resulting units as MP
MemoryRecords. See ``app.services.ingest`` for the full pipeline.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.hms import HmsError, hms_client_for_tenant
from app.schemas.ingest import IngestEventRequest, IngestEventResponse, IngestResultItem
from app.services.ingest import ingest_event

router = APIRouter(prefix="/v1/events", tags=["ingest"])


@router.post("/ingest", response_model=IngestEventResponse, status_code=status.HTTP_201_CREATED)
async def ingest(
    body: IngestEventRequest,
    db: Session = DbDep,
    tenant=TenantDep,
) -> IngestEventResponse:
    try:
        outcome = await ingest_event(
            db,
            tenant,
            hms_client=hms_client_for_tenant(tenant.tenant.hms_api_key),
            user_id=body.user_id,
            agent_id=body.agent_id,
            relationship_id=body.relationship_id,
            source_type=body.source_type,
            content=body.content,
            quote=body.quote,
            event_id=body.event_id,
            device_id=body.device_id,
        )
    except HmsError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "hms_retain_failed", "message": str(exc)},
        ) from exc

    db.commit()
    return IngestEventResponse(
        event_id=outcome.event_id,
        results=[IngestResultItem(id=mid, action=action) for mid, action in outcome.results],
    )
