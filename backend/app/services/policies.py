"""Create/update policies after tenant and V0.1 portability validation."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import not_found
from app.auth import TenantContext
from app.models.enums import AuditAction
from app.models.identity import Agent
from app.models.memory import AutoWriteRule, MemoryPolicy
from app.models.tenant import App
from app.schemas.policies import PolicyUpsertRequest
from app.services.audit import api_actor, write_audit
from app.services.ids import new_policy_id, new_rule_id


@dataclass(frozen=True)
class PolicyUpsertOutcome:
    policy: MemoryPolicy
    created: bool


def upsert_policy(
    db: Session,
    context: TenantContext,
    request: PolicyUpsertRequest,
) -> PolicyUpsertOutcome:
    """Persist one live policy for an in-tenant app/agent pair."""
    if request.portability.cross_brand_app:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "cross_brand_app portability is deferred to P2 and cannot be "
                "enabled in V0.1"
            ),
        )

    agent = db.scalar(
        select(Agent)
        .join(App, App.id == Agent.app_id)
        .where(
            Agent.id == request.agent_id,
            Agent.app_id == request.app_id,
            App.tenant_id == context.tenant.id,
        )
    )
    if agent is None:
        raise not_found("App/agent policy target", f"{request.app_id}/{request.agent_id}")

    policy = db.scalar(
        select(MemoryPolicy).where(
            MemoryPolicy.app_id == request.app_id,
            MemoryPolicy.agent_id == request.agent_id,
        )
    )
    created = policy is None
    if policy is None:
        policy = MemoryPolicy(
            id=new_policy_id(),
            app_id=request.app_id,
            agent_id=request.agent_id,
            portability={},
            retrieval={},
        )
        db.add(policy)
        db.flush()

    policy.portability = request.portability.model_dump(mode="json")
    policy.retrieval = request.retrieval.model_dump(mode="json")
    policy.auto_write_rules = [
        AutoWriteRule(
            id=new_rule_id(),
            policy_id=policy.id,
            memory_type=rule.memory_type,
            action=rule.action,
            sensitivity=rule.sensitivity,
            ttl_days=rule.ttl_days,
        )
        for rule in request.auto_write_rules
    ]
    agent.memory_policy_id = policy.id
    db.flush()

    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.POLICY_CHANGED,
        target=policy.id,
        detail=("Created" if created else "Updated")
        + f" policy for app {request.app_id} and agent {request.agent_id}",
    )
    return PolicyUpsertOutcome(policy=policy, created=created)


__all__ = ["PolicyUpsertOutcome", "upsert_policy"]
