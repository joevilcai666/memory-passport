"""POST/GET /v1/webhooks — register and inspect tenant webhook endpoints (#33).

Configuration is operator-only: only Owner/Admin may register an endpoint
(``require_role``). Delivery records are observable without the signing secret.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy.orm import Session

from app.api.deps import DbDep, OperatorOrAdminDep, TenantDep
from app.api.errors import not_found
from app.auth import TenantContext
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.schemas.webhooks import (
    WebhookDeliveryResponse,
    WebhookEndpointCreateRequest,
    WebhookEndpointCreateResponse,
    WebhookEndpointResponse,
)
from app.services.webhook import list_endpoints, register_endpoint

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.get("", response_model=list[WebhookEndpointResponse])
def list_webhooks(
    db: Session = DbDep,
    tenant: TenantContext = TenantDep,
) -> list[WebhookEndpointResponse]:
    return [WebhookEndpointResponse.model_validate(e) for e in list_endpoints(db, tenant.tenant.id)]


# Registration is an operator-only action (issue #32 RBAC): Owner/Admin may
# configure the destination + one-time signing secret; Support gets 403.
@router.post(
    "",
    response_model=WebhookEndpointCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[OperatorOrAdminDep],
)
def create_webhook(
    body: WebhookEndpointCreateRequest,
    response: Response,
    db: Session = DbDep,
    tenant: TenantContext = TenantDep,
) -> WebhookEndpointCreateResponse:
    endpoint, secret = register_endpoint(db, tenant, url=body.url, events=body.events)
    db.commit()
    db.refresh(endpoint)
    return WebhookEndpointCreateResponse(
        endpoint=WebhookEndpointResponse.model_validate(endpoint),
        signing_secret=secret,
    )


@router.get("/{endpoint_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_deliveries(
    endpoint_id: str,
    db: Session = DbDep,
    tenant: TenantContext = TenantDep,
) -> list[WebhookDeliveryResponse]:
    endpoint = (
        db.query(WebhookEndpoint)
        .filter(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.tenant_id == tenant.tenant.id,
        )
        .one_or_none()
    )
    if endpoint is None:
        raise not_found("Webhook endpoint", endpoint_id)
    rows = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.endpoint_id == endpoint_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(100)
        .all()
    )
    return [WebhookDeliveryResponse.model_validate(r) for r in rows]


__all__ = ["router"]
