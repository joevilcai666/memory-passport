"""GET /v1/debug/traces/{trace_id} — the retrieval debug chain (Slice 4)."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, TenantDep
from app.auth import TenantContext
from app.schemas.retrieve import DebugTraceResponse
from app.services.retrieve import get_trace

router = APIRouter(prefix="/v1/debug", tags=["debug"])


@router.get(
    "/traces/{trace_id}",
    response_model=DebugTraceResponse,
    status_code=status.HTTP_200_OK,
)
def get_trace_endpoint(
    trace_id: str,
    db: Session = DbDep,
    tenant: TenantContext = TenantDep,
) -> DebugTraceResponse:
    trace = get_trace(db, tenant.tenant.id, trace_id)
    return DebugTraceResponse(
        id=trace.id,
        query=trace.query,
        caller=trace.caller,
        hms_results=trace.hms_results,
        projected=trace.projected,
        retrieval_events=trace.retrieval_events,
        created_at=trace.created_at,
    )
