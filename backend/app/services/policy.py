"""Policy resolution + event classification.

The ingest pipeline asks: given this event, what ``memory_type`` /
``sensitivity`` should the resulting records carry, and what ``action``
(auto_write / confirm / block) does the app's policy dictate?

Resolution
----------
1. Load the agent's :class:`MemoryPolicy` (``agents.memory_policy_id``) + its
   :class:`AutoWriteRule`s. An agent without a policy gets a conservative
   default (S1/auto_write) so ingest still works for freshly-provisioned agents.

Classification
--------------
V0.1 keeps the classifier deterministic + LLM-free (the real classification is
HMS's job — it extracts the facts). MP just needs a per-event (type,
sensitivity, action) so it can:
  * decide the S3 block path (no HMS call at all),
  * set the resulting MP ``MemoryRecord.status`` (active vs candidate),
  * honour the app's auto-write rules.

The classifier matches the event's ``source_type`` to a default sensitivity
(PRD §7), then looks for an :class:`AutoWriteRule` whose ``memory_type`` +
``sensitivity`` match the inferred ones. If none matches, the broadest rule
(any-type, same-sensitivity) is used; failing that, a safe default
(``auto_write`` / S1).

The sensitivity→status mapping (PRD §7, encoded in the MemorySensitivity
comment in ``src/lib/types.ts:120``):
  S0 -> active          (auto-write)
  S1 -> active          (auto-write + visible)
  S2 -> candidate       (user-confirm; visible in console, not in retrieve)
  S3 -> BLOCKED         (no HMS call, no MP record; audit only)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import (
    AutoWriteAction,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
)
from app.models.memory import AutoWriteRule, MemoryPolicy

# Default sensitivities by source_type — a coarse, PRD-aligned prior. The app's
# AutoWriteRule set can still override the *action* (confirm/block) for any
# (type, sensitivity) pair.
_SOURCE_DEFAULTS: dict[str, MemorySensitivity] = {
    "chat": MemorySensitivity.S1,
    "voice": MemorySensitivity.S1,
    "setup": MemorySensitivity.S1,
    "explicit_instruction": MemorySensitivity.S0,  # user told us directly -> trust
    "robot_event": MemorySensitivity.S0,
    "app_event": MemorySensitivity.S0,
}

# When no policy rule is found, infer the memory_type from the source_type:
# explicit/setup turns tend to be preferences; chat tends to be relationship;
# device/robot events are events. Kept simple + overridable by AutoWriteRules.
_SOURCE_DEFAULT_TYPE: dict[str, MemoryType] = {
    "chat": MemoryType.RELATIONSHIP,
    "voice": MemoryType.RELATIONSHIP,
    "setup": MemoryType.PREFERENCE,
    "explicit_instruction": MemoryType.PREFERENCE,
    "robot_event": MemoryType.EVENT,
    "app_event": MemoryType.EVENT,
}

# Fallbacks used when the agent has no MemoryPolicy at all (freshly
# provisioned). Conservative: S1, auto_write, preference.
_DEFAULT_POLICY_PORTABILITY = {
    "layer": "portable",
    "cross_device": True,
    "cross_role": True,
    "cross_model": True,
    "cross_brand_app": False,
}
_DEFAULT_POLICY_RETRIEVAL = {
    "max_memories_per_response": 8,
    "include_sensitive_in_prompt": False,
}


@dataclass(frozen=True)
class Classification:
    """The (type, sensitivity, action) triple the ingest pipeline acts on."""

    memory_type: MemoryType
    sensitivity: MemorySensitivity
    action: AutoWriteAction


@dataclass(frozen=True)
class ResolvedPolicy:
    """Everything the ingest/retrieve pipelines need from the agent's policy."""

    policy: MemoryPolicy | None
    rules: list[AutoWriteRule]
    portability: dict[str, Any]
    retrieval: dict[str, Any]
    created_by_model: str  # recorded on MemoryRecord.model_provenance


def resolve_policy(db: Session, agent_id: str) -> ResolvedPolicy | None:
    """Load the agent's MemoryPolicy + AutoWriteRules, eager-loading rules.

    Returns ``None`` if the agent doesn't exist. An agent with no policy still
    resolves (to a ResolvedPolicy with ``policy=None`` + conservative defaults)
    so ingest/retrieve work for freshly-provisioned agents.
    """
    # Join Agent -> MemoryPolicy in one query; rules are a separate collection
    # but small (the seed has 6), so a second select is fine.
    from app.models.identity import Agent

    row = db.scalar(
        select(Agent).where(Agent.id == agent_id)
    )
    if row is None:
        return None

    policy = None
    rules: list[AutoWriteRule] = []
    if row.memory_policy_id is not None:
        policy = db.scalar(
            select(MemoryPolicy).where(MemoryPolicy.id == row.memory_policy_id)
        )
    if policy is None:
        policy = db.scalar(select(MemoryPolicy).where(MemoryPolicy.agent_id == agent_id))
    if policy is not None:
        rules = db.scalars(
            select(AutoWriteRule).where(AutoWriteRule.policy_id == policy.id)
        ).all()

    return ResolvedPolicy(
        policy=policy,
        rules=list(rules),
        portability=(
            policy.portability if policy is not None else dict(_DEFAULT_POLICY_PORTABILITY)
        ),
        retrieval=(
            policy.retrieval if policy is not None else dict(_DEFAULT_POLICY_RETRIEVAL)
        ),
        # HMS does the extraction; we record the bank's configured model when
        # known. V0.1 default is the seed's "gpt-4o" so the prototype's
        # model_provenance shape round-trips faithfully.
        created_by_model="gpt-4o",
    )


def classify(
    resolved: ResolvedPolicy,
    *,
    source_type: str,
    content: str,
) -> Classification:
    """Decide the (memory_type, sensitivity, action) for one event.

    The classifier is a coarse prior (no LLM): pick a default sensitivity +
    memory_type from the source_type, then look for an AutoWriteRule that
    matches (type, sensitivity). If a rule says ``block``, the ingest pipeline
    takes the S3 path (no HMS call). If it says ``confirm``, the resulting MP
    record lands in ``candidate`` status. Otherwise ``active``.
    """
    sensitivity = _SOURCE_DEFAULTS.get(source_type, MemorySensitivity.S1)
    memory_type = _SOURCE_DEFAULT_TYPE.get(source_type, MemoryType.PREFERENCE)

    # Find a matching rule: exact (type, sensitivity) first, then any-type for
    # the same sensitivity. The seed policy covers (profile/preference/
    # relationship/event/task) x (S0/S1/S2/S3) — so most events hit a rule.
    rule = _match_rule(resolved.rules, memory_type, sensitivity)
    if rule is not None:
        action = rule.action
        # A block rule overrides the inferred type/sensitivity to the rule's
        # own (so the audit row records what the policy actually said).
        memory_type = rule.memory_type
        sensitivity = rule.sensitivity
    else:
        # No rule: S3 is always blocked by default (safety), everything else
        # auto-writes. Matches PRD §7's S3=block/safety semantics.
        if sensitivity == MemorySensitivity.S3:
            action = AutoWriteAction.BLOCK
        else:
            action = AutoWriteAction.AUTO_WRITE

    return Classification(
        memory_type=memory_type,
        sensitivity=sensitivity,
        action=action,
    )


def _match_rule(
    rules: list[AutoWriteRule],
    memory_type: MemoryType,
    sensitivity: MemorySensitivity,
) -> AutoWriteRule | None:
    exact = next(
        (
            r
            for r in rules
            if r.memory_type == memory_type and r.sensitivity == sensitivity
        ),
        None,
    )
    if exact is not None:
        return exact
    # Fall back to any rule matching the sensitivity (covers the case where the
    # inferred memory_type isn't in the rule set but the sensitivity is).
    return next((r for r in rules if r.sensitivity == sensitivity), None)


def match_auto_write_rule(
    policy: ResolvedPolicy,
    memory_type: MemoryType,
    sensitivity: MemorySensitivity,
) -> AutoWriteAction:
    """Return the live matching action or the conservative default action."""
    rule = _match_rule(policy.rules, memory_type, sensitivity)
    if rule is not None:
        return rule.action
    return (
        AutoWriteAction.BLOCK
        if sensitivity == MemorySensitivity.S3
        else AutoWriteAction.AUTO_WRITE
    )


def status_for_sensitivity(sensitivity: MemorySensitivity, action: AutoWriteAction) -> MemoryStatus:
    """Map a (sensitivity, action) to the resulting MemoryRecord.status.

    S3 + block   -> the record is never created (handled by the ingest pipeline).
    S2 / confirm -> ``candidate`` (visible in console, not in retrieve by default).
    S0/S1 + auto -> ``active``.
    Any action when sensitivity is S3 -> treated as blocked upstream.
    """
    if action == AutoWriteAction.CONFIRM or sensitivity == MemorySensitivity.S2:
        return MemoryStatus.CANDIDATE
    return MemoryStatus.ACTIVE


def is_blocked(classification: Classification) -> bool:
    """True iff the event should be blocked end-to-end (no HMS call, no MP row)."""
    return (
        classification.action == AutoWriteAction.BLOCK
        or classification.sensitivity == MemorySensitivity.S3
    )
