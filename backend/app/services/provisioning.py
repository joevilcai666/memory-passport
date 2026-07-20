"""Provisioning service — domain logic for the 7 creation endpoints.

Each function takes the resolved :class:`TenantContext`, a request model, and
the request-scoped :class:`Session`, and returns the created ORM row. They
encapsulate:

* **Tenant isolation** — every lookup filters by ``context.tenant.id``. A
  cross-tenant reference (e.g. an ``app_id`` from another tenant) raises the
  shared ``not_found`` error so existence isn't leaked.
* **The device state machine** — ``bind`` is only legal from ``registered``,
  ``unbind`` only from ``bound``; anything else raises ``conflict_illegal_state``.
* **Pairing-code authorization** — ``register`` issues a one-time code stored
  against the device; ``bind`` must present the same code (anonymous or
  mismatched binds are rejected with 403).
* **User idempotency** — ``create_user`` is idempotent on
  ``(app_id, external_user_id)``; a repeat returns the existing user and skips
  HMS bank provisioning.

Audit rows are written inline (one per successful creation) via
:func:`app.services.audit.write_audit`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import conflict_illegal_state, forbidden, not_found
from app.auth import TenantContext
from app.models.enums import AuditAction, DeviceStatus
from app.models.identity import Agent, Device, Relationship, User
from app.models.tenant import ApiKey, App
from app.services.audit import api_actor, write_audit
from app.services.ids import (
    new_agent_id,
    new_api_key,
    new_apikey_id,
    new_app_id,
    new_device_id,
    new_pairing_code,
    new_passport_id,
    new_relationship_id,
    new_user_id,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


# Pairing codes are held in a process-local map keyed by device_id. Slice 2
# doesn't persist them (they're one-time, short-lived); a later slice will move
# them to a dedicated ``device_pairing_codes`` table with expiry + rotation.
# Single-node V0.1 (one uvicorn process behind the compose network) is the
# documented deployment shape, so an in-process map is sufficient here.
# NOTE: this is intentionally module-level so the code survives across the
# register / bind *requests* (different sessions, different ORM instances).
_PAIRING_CODES: dict[str, str] = {}


def _issue_pairing_code(device_id: str) -> str:
    """Mint + store a one-time pairing code against ``device_id``."""
    code = new_pairing_code()
    _PAIRING_CODES[device_id] = code
    return code


def _consume_pairing_code(device_id: str, presented: str) -> bool:
    """Return True iff ``presented`` matches the issued code; consume it on success.

    A missing/already-consumed/mismatched code returns False (the caller raises
    403). Comparison is constant-time.
    """
    import hmac

    issued = _PAIRING_CODES.get(device_id)
    if not issued:
        return False
    ok = hmac.compare_digest(issued.encode(), presented.encode())
    if ok:
        # One-time: drop the code so it can't be replayed.
        _PAIRING_CODES.pop(device_id, None)
    return ok


def reset_pairing_codes_for_tests() -> None:
    """Test hook — wipe the pairing-code map between tests."""
    _PAIRING_CODES.clear()


# ---------------------------------------------------------------------------
# Tenant-isolation lookups — single source of truth for "exists in this tenant?"
# ---------------------------------------------------------------------------


def _get_app_in_tenant(db: Session, tenant_id: str, app_id: str) -> App:
    """Return the App iff it belongs to ``tenant_id``; else 404."""
    row = db.scalar(select(App).where(App.id == app_id, App.tenant_id == tenant_id))
    if row is None:
        raise not_found("App", app_id)
    return row


def _get_user_in_tenant(db: Session, tenant_id: str, user_id: str) -> User:
    row = db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    if row is None:
        raise not_found("User", user_id)
    return row


def _get_device_in_tenant(db: Session, tenant_id: str, device_id: str) -> Device:
    row = db.scalar(
        select(Device).where(Device.id == device_id, Device.tenant_id == tenant_id)
    )
    if row is None:
        raise not_found("Device", device_id)
    return row


def _get_agent_in_tenant(db: Session, tenant_id: str, agent_id: str) -> Agent:
    # Agents are scoped via app -> tenant. The Agent model has no app
    # relationship, so join to apps explicitly.
    row = db.scalar(
        select(Agent)
        .join(App, App.id == Agent.app_id)
        .where(Agent.id == agent_id, App.tenant_id == tenant_id)
    )
    if row is None:
        raise not_found("Agent", agent_id)
    return row


# ---------------------------------------------------------------------------
# Provisioning operations
# ---------------------------------------------------------------------------


def create_app(
    db: Session,
    context: TenantContext,
    *,
    name: str,
    product_type,
    environment,
    data_region,
    show_powered_by: bool,
) -> tuple[App, ApiKey]:
    """Create an App under the caller's tenant + its first auto-generated key.

    Returns ``(app, api_key)``. The key's ``key`` field is the full bearer token
    ``mp_<env>_<secret>`` — the only time it's returned in full to the caller.
    """
    tenant = context.tenant
    now = _now()

    app = App(
        id=new_app_id(),
        tenant_id=tenant.id,
        name=name,
        product_type=product_type,
        environment=environment,
        data_region=data_region,
        show_powered_by=show_powered_by,
        status="active",
        created_at=now,
    )
    db.add(app)
    db.flush()  # populate app.id for the FK + audit target

    key = ApiKey(
        id=new_apikey_id(),
        app_id=app.id,
        label=f"{environment.capitalize()} — Default",
        environment=environment,
        key=new_api_key(environment.value if hasattr(environment, "value") else str(environment)),
        created_at=now,
        last_used_at=None,
    )
    db.add(key)
    db.flush()

    write_audit(
        db,
        tenant_id=tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.APP_CREATED,
        target=app.id,
        detail=f"Created App '{app.name}' ({product_type}/{environment})",
    )
    return app, key


def create_agent(
    db: Session,
    context: TenantContext,
    *,
    app_id: str,
    name: str,
    type,
    persona_version: str,
    allowed_memory_types: list[str],
    emoji: str,
) -> Agent:
    """Create an Agent under ``app_id`` (must belong to the caller's tenant)."""
    _get_app_in_tenant(db, context.tenant.id, app_id)

    agent = Agent(
        id=new_agent_id(),
        app_id=app_id,
        name=name,
        type=type,
        persona_version=persona_version,
        memory_policy_id=None,  # no policy until Slice N wires MemoryPolicy creation
        allowed_memory_types=list(allowed_memory_types),
        created_at=_now(),
        emoji=emoji,
    )
    db.add(agent)
    db.flush()

    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.AGENT_CREATED,
        target=agent.id,
        detail=f"Created Agent '{agent.name}' ({type}) under {app_id}",
    )
    return agent


async def create_user(
    db: Session,
    context: TenantContext,
    *,
    app_id: str,
    external_user_id: str,
    age_group,
    region: str,
    display_name: str,
    hms_client,
) -> tuple[User, bool]:
    """Create or sync a User under ``app_id`` and (on first sight) provision HMS.

    Idempotent on ``(app_id, external_user_id)``: a repeat returns the existing
    user with ``created=False`` and does NOT call HMS again. On first creation
    the HMS bank is provisioned idempotently (``bank_id == user.id``).

    Returns ``(user, created)``.
    """
    tenant = context.tenant
    _get_app_in_tenant(db, tenant.id, app_id)

    # Idempotency: a user is unique per (tenant, external_user_id). The User
    # table has no app_id column today (the identity model scopes users to a
    # tenant; V0.1 ships one app per tenant per the seed), so we de-dupe on
    # tenant + external_user_id. A later slice may add a UNIQUE index + app_id.
    existing = db.scalar(
        select(User).where(
            User.tenant_id == tenant.id,
            User.external_user_id == external_user_id,
        )
    )
    if existing is not None:
        # Idempotent: do NOT call HMS a second time — the bank already exists.
        return existing, False

    user = User(
        id=new_user_id(),
        tenant_id=tenant.id,
        external_user_id=external_user_id,
        passport_id=new_passport_id(),
        age_group=age_group,
        region=region,
        memory_enabled=True,
        created_at=_now(),
        display_name=display_name,
        avatar_color="#6366f1",  # default indigo; the prototype picks per-user
    )
    db.add(user)
    db.flush()

    # Provision the HMS bank (idempotent on HMS's side too). bank_id == user.id.
    try:
        await hms_client.put_bank(user.id)
    except Exception:
        # Provisioning failure must not leave a half-created user. Roll back so
        # a retry can start clean. The route handler lets the exception surface
        # as a 502/500 — bank provisioning is a hard dependency for users.
        db.rollback()
        raise

    write_audit(
        db,
        tenant_id=tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.USER_CREATED,
        target=user.id,
        detail=(
            f"Created User '{display_name}' (external_user_id={external_user_id}); "
            f"HMS bank provisioned (bank_id={user.id})"
        ),
    )
    return user, True


def create_relationship(
    db: Session,
    context: TenantContext,
    *,
    user_id: str,
    agent_id: str,
    device_id: str | None,
    relationship_type,
    memory_enabled: bool,
) -> Relationship:
    """Create a Relationship linking user × agent (+ optional device) in-tenant."""
    tenant = context.tenant
    _get_user_in_tenant(db, tenant.id, user_id)
    _get_agent_in_tenant(db, tenant.id, agent_id)
    if device_id is not None:
        _get_device_in_tenant(db, tenant.id, device_id)

    rel = Relationship(
        id=new_relationship_id(),
        tenant_id=tenant.id,
        user_id=user_id,
        agent_id=agent_id,
        device_id=device_id,
        relationship_type=relationship_type,
        memory_enabled=memory_enabled,
        created_at=_now(),
    )
    db.add(rel)
    db.flush()

    write_audit(
        db,
        tenant_id=tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.RELATIONSHIP_CREATED,
        target=rel.id,
        detail=f"Created Relationship {user_id} x {agent_id} ({relationship_type})",
    )
    return rel


def register_device(
    db: Session,
    context: TenantContext,
    *,
    model: str,
    generation: str,
    serial_number_hash: str,
) -> tuple[Device, str]:
    """Register a device (status=registered) and issue a one-time pairing code."""
    device = Device(
        id=new_device_id(),
        tenant_id=context.tenant.id,
        model=model,
        generation=generation,
        serial_number_hash=serial_number_hash,
        status=DeviceStatus.REGISTERED,
        bound_user_id=None,
        last_seen_at=None,
    )
    db.add(device)
    db.flush()

    code = _issue_pairing_code(device.id)

    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.DEVICE_REGISTERED,
        target=device.id,
        detail=f"Registered Device {model}/{generation} (pairing code issued)",
    )
    return device, code


def bind_device(
    db: Session,
    context: TenantContext,
    *,
    device_id: str,
    user_id: str,
    pairing_code: str,
) -> Device:
    """Bind a registered device to a user.

    State machine: ``registered -> bound``. Requires a valid pairing code that
    matches the one issued at registration. Anonymous binds (no user_id) are
    rejected by the request schema; this function additionally enforces the
    state + code.
    """
    device = _get_device_in_tenant(db, context.tenant.id, device_id)
    user = _get_user_in_tenant(db, context.tenant.id, user_id)

    if device.status != DeviceStatus.REGISTERED:
        raise conflict_illegal_state(current=device.status.value, action="bind")

    # PRD §9.1 device authorization: a valid pairing code (or equivalent signed
    # claim) is mandatory. No code issued / already used / mismatch -> 403.
    if not _consume_pairing_code(device.id, pairing_code):
        raise forbidden(
            code="invalid_pairing_code",
            message="pairing code is missing, already used, or incorrect",
        )

    device.status = DeviceStatus.BOUND
    device.bound_user_id = user.id
    device.last_seen_at = _now()
    db.flush()

    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.DEVICE_BOUND,
        target=device.id,
        detail=f"Bound Device to user {user.id} via pairing code",
    )
    return device


def unbind_device(db: Session, context: TenantContext, *, device_id: str) -> Device:
    """Unbind a bound device.

    State machine: ``bound -> unbound``. Clears ``bound_user_id``.
    """
    device = _get_device_in_tenant(db, context.tenant.id, device_id)

    if device.status != DeviceStatus.BOUND:
        raise conflict_illegal_state(current=device.status.value, action="unbind")

    previous_user = device.bound_user_id
    device.status = DeviceStatus.UNBOUND
    device.bound_user_id = None
    db.flush()

    write_audit(
        db,
        tenant_id=context.tenant.id,
        actor=api_actor(context.api_key.id),
        action=AuditAction.DEVICE_UNBOUND,
        target=device.id,
        detail=(
            f"Unbound Device (previously bound to {previous_user})"
            if previous_user
            else "Unbound Device"
        ),
    )
    return device


