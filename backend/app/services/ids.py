"""ID + secret generators for provisioning.

All MP ids are opaque, prefixed, base62-ish strings (``secrets.token_urlsafe``
gives 43 chars of URL-safe entropy from 32 bytes — plenty for collision
resistance and unguessability). The prefix makes a row's type obvious in logs.

Conventions (mirrors the seeded ids in ``app/seed/data.py``):
    app_<token>   agt_<token>   usr_<token>   pp_<token>
    rel_<token>   dev_<token>   key_<token>   al_<token>
"""

from __future__ import annotations

import secrets

# Length of the random token suffix (in characters). token_urlsafe(n) emits
# ~1.33*n chars; 12 bytes -> 16 chars, short enough to copy-paste, long enough
# that birthday collisions are astronomically unlikely across a tenant's rows.
_TOKEN_BYTES = 12

# Pairing codes are short (8 chars) because a human reads/types them off a
# device screen during the bind flow. Alphanumeric only (strip ``-_`` from the
# url-safe alphabet) so they're unambiguous when read aloud.
_PAIRING_BYTES = 6
_PAIRING_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# API key secrets: 24 bytes -> ~32 chars. The full key is ``mp_<env>_<secret>``.
_APIKEY_SECRET_BYTES = 24


def _token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(_TOKEN_BYTES)}"


def new_app_id() -> str:
    return _token("app")


def new_agent_id() -> str:
    return _token("agt")


def new_user_id() -> str:
    return _token("usr")


def new_passport_id() -> str:
    """The user-ownership anchor (PRD §9.1). Prefixed ``pp_``."""
    return _token("pp")


def new_relationship_id() -> str:
    return _token("rel")


def new_memory_id() -> str:
    """MP MemoryRecord id (mirrors the seeded ``mem_…`` convention)."""
    return _token("mem")


def new_event_id() -> str:
    """Ingest event id (the correlation key sent to HMS as document_id)."""
    return _token("evt")


def new_trace_id() -> str:
    """RetrievalTrace id (returned to the caller as trace_id)."""
    return _token("trc")


def new_device_id() -> str:
    return _token("dev")


def new_apikey_id() -> str:
    return _token("key")


def new_audit_id() -> str:
    return _token("al")


def new_policy_id() -> str:
    return _token("pol")


def new_rule_id() -> str:
    return _token("rule")


def new_migration_id() -> str:
    return _token("mig")


def new_usage_id() -> str:
    return _token("use")


def new_export_id() -> str:
    return _token("exp")


def new_pairing_code() -> str:
    """8-char alphanumeric one-time code for device bind authorization."""
    # Rejection-sample from the url-safe alphabet so the code is unambiguous
    # when read off a device screen (no ``-`` / ``_`` / ``0`` / ``O`` look-alikes).
    rand = secrets.token_bytes(_PAIRING_BYTES * 4)  # plenty of entropy
    out = []
    i = 0
    while len(out) < 8:
        b = rand[i % len(rand)]
        i += 1
        idx = b % len(_PAIRING_ALPHABET)
        # Skip ambiguous chars (0, O, l, 1, I) for legibility.
        ch = _PAIRING_ALPHABET[idx]
        if ch in "0O1lI":
            continue
        out.append(ch)
    return "".join(out)


def new_api_key(environment: str) -> str:
    """Build a full bearer token: ``mp_<env>_<secret>``.

    ``environment`` is the app's environment (``sandbox`` / ``production``),
    matching the seeded key format ``mp_sandbox_…`` / ``mp_live_…``. We accept
    the literal env value; production keys are historically ``mp_live_…``
    (the seeded prod key uses ``mp_live_``), so map ``production`` -> ``live``
    to stay consistent with the existing dataset.
    """
    env_segment = "live" if environment == "production" else environment
    secret = secrets.token_urlsafe(_APIKEY_SECRET_BYTES)
    return f"mp_{env_segment}_{secret}"
