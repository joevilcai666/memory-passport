"""Luna seed dataset — faithful port of ``src/lib/mock-data.ts``.

Timestamps are computed at seed time (relative to "now"), mirroring the
``daysAgo`` / ``hoursAgo`` / ``minsAgo`` helpers in the TypeScript source, so
the dataset reads as recent no matter when you seed.

Entity counts (the acceptance criteria):
    tenants          1   (ten_luna)
    apps             1   (app_luna)
    api_keys         2   (key_sb_1 sandbox, key_prod_1 production)
    users            4   (usr_mia primary + usr_alex/sam/jordan)
    agents           2   (agt_luna companion, agt_luna_robot robot)
    devices          4   (v1 x3 + v2 x1)
    relationships    1   (rel_mia_luna)
    memory_policies  1   (pol_luna_default, with 6 auto-write rules)
    memory_records   42  (Preferences 12, Relationship 8, Events 9,
                          Boundaries 4, Tasks 6, Archived 3)
    migrations       1   (mig_001, status=preview)
    audit_logs       8

HMS banks (provisioned separately by run_seed): one empty bank per user,
``bank_id == user_id``, under the tenant_luna HMS schema.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

# ---------------------------------------------------------------------------
# Time helpers — match src/lib/mock-data.ts (now/daysAgo/hoursAgo/minsAgo).
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=UTC)


def days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


def hours_ago(n: int) -> datetime:
    return _now() - timedelta(hours=n)


def mins_ago(n: int) -> datetime:
    return _now() - timedelta(minutes=n)


# ---------------------------------------------------------------------------
# Portable / device-local portability presets (same as the TS constants).
# ---------------------------------------------------------------------------

PORTABLE = {
    "layer": "portable",
    "cross_device": True,
    "cross_role": True,
    "cross_model": True,
    "cross_brand_app": False,
}

DEVICE_LOCAL = {
    "layer": "device_local",
    "cross_device": False,
    "cross_role": False,
    "cross_model": False,
    "cross_brand_app": False,
}


# ---------------------------------------------------------------------------
# Raw rows — plain dicts that the seed runner upserts verbatim.
# ---------------------------------------------------------------------------

TENANT_ID = "ten_luna"
APP_ID = "app_luna"
PRIMARY_USER_ID = "usr_mia"
PRIMARY_RELATIONSHIP_ID = "rel_mia_luna"
PRIMARY_AGENT_ID = "agt_luna"
DEVICE_V1_ID = "dev_luna_v1"
DEVICE_V2_ID = "dev_luna_v2"

# Sandbox key from src/lib/mock-data.ts — must match MP_SEED_API_KEY.
SANDBOX_API_KEY = "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd"


def tenant() -> dict:
    # The Luna tenant keeps the legacy shared HMS key (so existing MP↔HMS calls
    # and the seeded banks under tenant_luna keep working unchanged). The key
    # is read from the env so a deployment that already rotated the placeholder
    # honours its real value; the default matches docker-compose.yml. See
    # issue #12 + backend/app/hms/tenant.py.
    import os

    return {
        "id": TENANT_ID,
        "name": "Luna Inc.",
        "plan": "Sandbox",
        "created_at": days_ago(28),
        "hms_api_key": os.getenv("HMS_API_TENANT_API_KEY", "hms_tenant_luna_change_me"),
        "hms_schema": "tenant_luna",
    }


def app() -> dict:
    return {
        "id": APP_ID,
        "tenant_id": TENANT_ID,
        "name": "Luna",
        "product_type": "hybrid",
        "environment": "sandbox",
        "data_region": "us-east-1",
        "show_powered_by": True,
        "status": "active",
        "created_at": days_ago(28),
    }


def api_keys() -> list[dict]:
    # Production key is masked in mock-data.ts (mp_live_••••••); only the
    # sandbox key is seeded unmasked so the auth acceptance test passes.
    return [
        {
            "id": "key_sb_1",
            "app_id": APP_ID,
            "label": "Sandbox — Default",
            "environment": "sandbox",
            "key": SANDBOX_API_KEY,
            "created_at": days_ago(28),
            "last_used_at": mins_ago(12),
        },
        {
            "id": "key_prod_1",
            "app_id": APP_ID,
            "label": "Production — Default",
            "environment": "production",
            "key": "mp_live_REDACTED_SEED_PLACEHOLDER",
            "created_at": days_ago(14),
            "last_used_at": hours_ago(3),
        },
    ]


def users() -> list[dict]:
    return [
        {
            "id": PRIMARY_USER_ID,
            "tenant_id": TENANT_ID,
            "external_user_id": "luna_user_8842",
            "passport_id": "pp_4f2a8c91e3",
            "age_group": "adult",
            "region": "US",
            "memory_enabled": True,
            "created_at": days_ago(25),
            "display_name": "Mia Chen",
            "avatar_color": "#1E3A8A",
        },
        {
            "id": "usr_alex",
            "tenant_id": TENANT_ID,
            "external_user_id": "luna_user_2210",
            "passport_id": "pp_9c1b3d77fa",
            "age_group": "adult",
            "region": "US",
            "memory_enabled": True,
            "created_at": days_ago(18),
            "display_name": "Alex Rivera",
            "avatar_color": "#a855f7",
        },
        {
            "id": "usr_sam",
            "tenant_id": TENANT_ID,
            "external_user_id": "luna_user_5567",
            "passport_id": "pp_2e8f4a1b06",
            "age_group": "unknown",
            "region": "EU",
            "memory_enabled": True,
            "created_at": days_ago(11),
            "display_name": "Sam Okafor",
            "avatar_color": "#10b981",
        },
        {
            "id": "usr_jordan",
            "tenant_id": TENANT_ID,
            "external_user_id": "luna_user_7733",
            "passport_id": "pp_7d3e9c2218",
            "age_group": "adult",
            "region": "US",
            "memory_enabled": False,
            "created_at": days_ago(6),
            "display_name": "Jordan Lee",
            "avatar_color": "#f59e0b",
        },
    ]


def agents() -> list[dict]:
    return [
        {
            "id": PRIMARY_AGENT_ID,
            "app_id": APP_ID,
            "name": "Luna",
            "type": "companion",
            "persona_version": "persona.v3.2",
            "memory_policy_id": "pol_luna_default",
            "allowed_memory_types": [
                "profile",
                "preference",
                "boundary",
                "relationship",
                "event",
                "task",
            ],
            "created_at": days_ago(27),
            "emoji": "🌙",
        },
        {
            "id": "agt_luna_robot",
            "app_id": APP_ID,
            "name": "Luna Robot",
            "type": "robot",
            "persona_version": "robot-fw.v2.0",
            "memory_policy_id": "pol_luna_default",
            "allowed_memory_types": [
                "profile",
                "preference",
                "boundary",
                "event",
                "task",
            ],
            "created_at": days_ago(20),
            "emoji": "🤖",
        },
    ]


def devices() -> list[dict]:
    return [
        {
            "id": DEVICE_V1_ID,
            "tenant_id": TENANT_ID,
            "model": "Luna Robot",
            "generation": "v1",
            "serial_number_hash": "a4f2…c891",
            "status": "bound",
            "bound_user_id": PRIMARY_USER_ID,
            "last_seen_at": hours_ago(2),
        },
        {
            "id": DEVICE_V2_ID,
            "tenant_id": TENANT_ID,
            "model": "Luna Robot",
            "generation": "v2",
            "serial_number_hash": "b8c1…e453",
            "status": "registered",
            "bound_user_id": None,
            "last_seen_at": None,
        },
        {
            "id": "dev_luna_v1_002",
            "tenant_id": TENANT_ID,
            "model": "Luna Robot",
            "generation": "v1",
            "serial_number_hash": "f1d9…a722",
            "status": "bound",
            "bound_user_id": "usr_alex",
            "last_seen_at": hours_ago(8),
        },
        {
            "id": "dev_luna_v1_003",
            "tenant_id": TENANT_ID,
            "model": "Luna Robot",
            "generation": "v1",
            "serial_number_hash": "c3e7…19bd",
            "status": "unbound",
            "bound_user_id": None,
            "last_seen_at": days_ago(9),
        },
    ]


def relationships() -> list[dict]:
    return [
        {
            "id": PRIMARY_RELATIONSHIP_ID,
            "tenant_id": TENANT_ID,
            "user_id": PRIMARY_USER_ID,
            "agent_id": PRIMARY_AGENT_ID,
            "device_id": DEVICE_V1_ID,
            "relationship_type": "companion",
            "memory_enabled": True,
            "created_at": days_ago(25),
        },
    ]


def memory_policy() -> dict:
    """The single policy + its 6 auto-write rules (returned as two lists)."""
    policy = {
        "id": "pol_luna_default",
        "app_id": APP_ID,
        "agent_id": PRIMARY_AGENT_ID,
        "portability": {
            "layer": "portable",
            "cross_device": True,
            "cross_role": True,
            "cross_model": True,
            "cross_brand_app": False,
        },
        "retrieval": {
            "max_memories_per_response": 8,
            "include_sensitive_in_prompt": False,
        },
    }
    rules = [
        {"id": "r1", "policy_id": "pol_luna_default", "memory_type": "profile", "action": "auto_write", "sensitivity": "S1", "ttl_days": None},
        {"id": "r2", "policy_id": "pol_luna_default", "memory_type": "preference", "action": "auto_write", "sensitivity": "S1", "ttl_days": None},
        {"id": "r3", "policy_id": "pol_luna_default", "memory_type": "boundary", "action": "confirm", "sensitivity": "S2", "ttl_days": None},
        {"id": "r4", "policy_id": "pol_luna_default", "memory_type": "relationship", "action": "auto_write", "sensitivity": "S1", "ttl_days": None},
        {"id": "r5", "policy_id": "pol_luna_default", "memory_type": "event", "action": "auto_write", "sensitivity": "S0", "ttl_days": 90},
        {"id": "r6", "policy_id": "pol_luna_default", "memory_type": "task", "action": "auto_write", "sensitivity": "S0", "ttl_days": 7},
    ]
    return {"policy": policy, "rules": rules}


def _mk(mem: dict) -> dict:
    """Fill in the common foreign keys a memory inherits from its owner."""
    base = {
        "tenant_id": TENANT_ID,
        "app_id": APP_ID,
        "passport_id": "pp_4f2a8c91e3",
        "user_id": PRIMARY_USER_ID,
        "relationship_id": PRIMARY_RELATIONSHIP_ID,
        "agent_id": PRIMARY_AGENT_ID,
        "device_id": None,
    }
    base.update(mem)
    return base


def memories() -> list[dict]:
    """All 42 memories — Preferences 12, Relationship 8, Events 9,
    Boundaries 4, Tasks 6, Archived 3.

    Content, confidence, portability, source quotes, retrieval history and
    usage_count are transcribed verbatim from src/lib/mock-data.ts.
    """
    portable = PORTABLE
    device_local = DEVICE_LOCAL

    seeds = [
        # ---- Preferences (12) ----
        dict(id="mem_001", type="preference", content="You prefer calm, light conversations at night.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.94, portability=portable, source={"event_id": "evt_001", "source_type": "chat", "timestamp": days_ago(23), "quote": "At night I prefer calmer replies."}, valid_from=days_ago(23), expires_at=None, version=1, supersedes=None, last_used_at=hours_ago(1), usage_count=47, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": hours_ago(1)}, {"model": "claude-3.5-sonnet", "used": True, "timestamp": days_ago(1)}, {"model": "gpt-4o", "used": True, "timestamp": days_ago(3)}]}),
        dict(id="mem_002", type="preference", content="You prefer quiet mode after 10pm.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.91, portability=portable, source={"event_id": "evt_002", "source_type": "chat", "timestamp": days_ago(22), "quote": "Please keep things quiet after 10pm."}, valid_from=days_ago(22), expires_at=None, version=1, supersedes=None, last_used_at=hours_ago(2), usage_count=38, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": hours_ago(2)}]}),
        dict(id="mem_003", type="preference", content='You like being greeted with "hey Mia".', scope="relationship_only", sensitivity="S1", status="active", confidence=0.88, portability=portable, source={"event_id": "evt_003", "source_type": "setup", "timestamp": days_ago(25), "quote": 'Call me Mia, and start with "hey Mia".'}, valid_from=days_ago(25), expires_at=None, version=1, supersedes=None, last_used_at=hours_ago(5), usage_count=124, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": hours_ago(5)}]}),
        dict(id="mem_004", type="preference", content="Your favorite tea is chamomile.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.82, portability=portable, source={"event_id": "evt_004", "source_type": "chat", "timestamp": days_ago(20), "quote": "I always keep chamomile around."}, valid_from=days_ago(20), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(2), usage_count=9, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": days_ago(2)}]}),
        dict(id="mem_005", type="preference", content="You prefer short replies when you're busy.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.79, portability=portable, source={"event_id": "evt_005", "source_type": "chat", "timestamp": days_ago(18), "quote": "Keep it short, I'm at work."}, valid_from=days_ago(18), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(1), usage_count=22, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "claude-3.5-sonnet", "used": True, "timestamp": days_ago(1)}]}),
        dict(id="mem_006", type="preference", content="You enjoy stargazing and space facts.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.85, portability=portable, source={"event_id": "evt_006", "source_type": "chat", "timestamp": days_ago(15), "quote": "Tell me something about the stars tonight."}, valid_from=days_ago(15), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(3), usage_count=14, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": days_ago(3)}]}),
        dict(id="mem_007", type="preference", content="You prefer English, occasional French endearments.", scope="user_global", sensitivity="S1", status="active", confidence=0.9, portability=portable, source={"event_id": "evt_007", "source_type": "chat", "timestamp": days_ago(14), "quote": "Mix in a little French sometimes, I love it."}, valid_from=days_ago(14), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(4), usage_count=31, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": days_ago(4)}]}),
        dict(id="mem_008", type="preference", content="You prefer voice over text when walking.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.76, portability=portable, source={"event_id": "evt_008", "source_type": "voice", "timestamp": days_ago(12), "quote": "[voice] I'm walking, just talk to me."}, valid_from=days_ago(12), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(2), usage_count=11, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_009", type="preference", content="Your favorite music genre is ambient for focus.", scope="user_global", sensitivity="S1", status="active", confidence=0.81, portability=portable, source={"event_id": "evt_009", "source_type": "chat", "timestamp": days_ago(10), "quote": "Ambient helps me focus when I work."}, valid_from=days_ago(10), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(5), usage_count=7, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_010", type="preference", content="You like reminders framed gently, not as commands.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.87, portability=portable, source={"event_id": "evt_010", "source_type": "chat", "timestamp": days_ago(9), "quote": "Don't boss me around with reminders."}, valid_from=days_ago(9), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(1), usage_count=19, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": days_ago(1)}]}),
        dict(id="mem_011", type="preference", content="You dislike small talk about weather.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.74, portability=portable, source={"event_id": "evt_011", "source_type": "chat", "timestamp": days_ago(7), "quote": "Skip the weather talk, let's get real."}, valid_from=days_ago(7), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(3), usage_count=5, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_012", type="preference", content="You prefer warm lighting mood in the evening.", scope="relationship_only", sensitivity="S1", status="active", confidence=0.78, portability=portable, source={"event_id": "evt_012", "source_type": "app_event", "timestamp": days_ago(5), "quote": "Set evening mood to warm."}, valid_from=days_ago(5), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(1), usage_count=6, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        # ---- Relationship (8) ----
        dict(id="mem_013", type="relationship", content='You call this companion "Luna".', scope="relationship_only", sensitivity="S1", status="active", confidence=0.99, portability=portable, source={"event_id": "evt_013", "source_type": "setup", "timestamp": days_ago(25), "quote": "I'll call you Luna."}, valid_from=days_ago(25), expires_at=None, version=1, supersedes=None, last_used_at=mins_ago(30), usage_count=312, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": mins_ago(30)}, {"model": "claude-3.5-sonnet", "used": True, "timestamp": days_ago(1)}]}),
        dict(id="mem_014", type="relationship", content="You and Luna have an ongoing 25-day streak.", scope="relationship_only", sensitivity="S1", status="active", confidence=1.0, portability=portable, source={"event_id": "evt_014", "source_type": "app_event", "timestamp": days_ago(1), "quote": "App streak counter."}, valid_from=days_ago(25), expires_at=None, version=1, supersedes=None, last_used_at=hours_ago(6), usage_count=88, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_015", type="relationship", content="You asked Luna to check in on you when you're sad.", scope="relationship_only", sensitivity="S2", status="active", confidence=0.92, portability=portable, source={"event_id": "evt_015", "source_type": "chat", "timestamp": days_ago(19), "quote": "When I'm down, just check in on me, okay?"}, valid_from=days_ago(19), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(2), usage_count=12, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": days_ago(2)}]}),
        dict(id="mem_016", type="relationship", content='You named Luna Robot v1 "little moon".', scope="device_only", sensitivity="S1", status="active", confidence=0.95, portability=device_local, source={"event_id": "evt_016", "source_type": "robot_event", "timestamp": days_ago(20), "quote": "I'll call the robot little moon."}, valid_from=days_ago(20), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(1), usage_count=41, device_id=DEVICE_V1_ID, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_017", type="relationship", content='You celebrated Luna\'s "birthday" on Jun 10.', scope="relationship_only", sensitivity="S1", status="active", confidence=0.9, portability=portable, source={"event_id": "evt_017", "source_type": "chat", "timestamp": days_ago(15), "quote": "Happy birthday Luna! I picked today."}, valid_from=days_ago(15), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(7), usage_count=3, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_018", type="relationship", content="You trust Luna with your daily mood check-ins.", scope="relationship_only", sensitivity="S2", status="active", confidence=0.89, portability=portable, source={"event_id": "evt_018", "source_type": "chat", "timestamp": days_ago(13), "quote": "I'm okay with you tracking my mood."}, valid_from=days_ago(13), expires_at=None, version=1, supersedes=None, last_used_at=hours_ago(8), usage_count=26, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": hours_ago(8)}]}),
        dict(id="mem_019", type="relationship", content='You and Luna joke about being "co-pilots".', scope="relationship_only", sensitivity="S1", status="active", confidence=0.7, portability=portable, source={"event_id": "evt_019", "source_type": "chat", "timestamp": days_ago(8), "quote": "We're co-pilots, you and me."}, valid_from=days_ago(8), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(4), usage_count=8, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_020", type="relationship", content="You asked Luna to remember your anniversary is in fall.", scope="relationship_only", sensitivity="S2", status="active", confidence=0.83, portability=portable, source={"event_id": "evt_020", "source_type": "explicit_instruction", "timestamp": days_ago(6), "quote": "My anniversary is in fall, don't forget."}, valid_from=days_ago(6), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(2), usage_count=2, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        # ---- Events (9) ----
        dict(id="mem_021", type="event", content="You had a tough Monday and asked for encouragement.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.77, portability=portable, source={"event_id": "evt_021", "source_type": "chat", "timestamp": days_ago(11), "quote": "Today was brutal, cheer me up."}, valid_from=days_ago(11), expires_at=days_ago(0), version=1, supersedes=None, last_used_at=days_ago(11), usage_count=1, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_022", type="event", content="You took a trip to the coast last weekend.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.8, portability=portable, source={"event_id": "evt_022", "source_type": "chat", "timestamp": days_ago(9), "quote": "Was at the coast this weekend, so relaxing."}, valid_from=days_ago(9), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(3), usage_count=4, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_023", type="event", content='You started a new book — "Project Hail Mary".', scope="relationship_only", sensitivity="S0", status="active", confidence=0.84, portability=portable, source={"event_id": "evt_023", "source_type": "chat", "timestamp": days_ago(7), "quote": "Started Project Hail Mary last night."}, valid_from=days_ago(7), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(1), usage_count=6, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": days_ago(1)}]}),
        dict(id="mem_024", type="event", content="Your home desk is on the left side of the room.", scope="device_only", sensitivity="S0", status="needs_review", confidence=0.66, portability=device_local, source={"event_id": "evt_024", "source_type": "robot_event", "timestamp": days_ago(8), "quote": "[v1 spatial scan] desk detected left."}, valid_from=days_ago(8), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(8), usage_count=2, device_id=DEVICE_V1_ID, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_025", type="event", content="You often place your cup near the desk.", scope="device_only", sensitivity="S0", status="needs_review", confidence=0.61, portability=device_local, source={"event_id": "evt_025", "source_type": "robot_event", "timestamp": days_ago(7), "quote": "[v1 object detect] cup cluster near desk."}, valid_from=days_ago(7), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(7), usage_count=1, device_id=DEVICE_V1_ID, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_026", type="event", content="You visited your parents two weeks ago.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.82, portability=portable, source={"event_id": "evt_026", "source_type": "chat", "timestamp": days_ago(14), "quote": "Was at my parents' last weekend."}, valid_from=days_ago(14), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(5), usage_count=3, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_027", type="event", content="You adopted a cat named Pixel last month.", scope="user_global", sensitivity="S0", status="active", confidence=0.93, portability=portable, source={"event_id": "evt_027", "source_type": "chat", "timestamp": days_ago(20), "quote": "I just adopted a cat, her name is Pixel."}, valid_from=days_ago(20), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(2), usage_count=9, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "claude-3.5-sonnet", "used": True, "timestamp": days_ago(2)}]}),
        dict(id="mem_028", type="event", content="You finished a big work project on Jun 28.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.85, portability=portable, source={"event_id": "evt_028", "source_type": "chat", "timestamp": days_ago(7), "quote": "Shipped the big project today, finally."}, valid_from=days_ago(7), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(3), usage_count=2, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_029", type="event", content="You had trouble sleeping last night.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.72, portability=portable, source={"event_id": "evt_029", "source_type": "chat", "timestamp": days_ago(1), "quote": "Couldn't sleep at all last night."}, valid_from=days_ago(1), expires_at=None, version=1, supersedes=None, last_used_at=hours_ago(10), usage_count=1, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": hours_ago(10)}]}),
        # ---- Boundaries (4) ----
        dict(id="mem_030", type="boundary", content="Don't discuss work after 10pm.", scope="relationship_only", sensitivity="S2", status="active", confidence=0.97, portability=portable, source={"event_id": "evt_030", "source_type": "explicit_instruction", "timestamp": days_ago(21), "quote": "No work talk after 10pm, please."}, valid_from=days_ago(21), expires_at=None, version=1, supersedes=None, last_used_at=hours_ago(2), usage_count=44, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": hours_ago(2)}, {"model": "claude-3.5-sonnet", "used": True, "timestamp": days_ago(1)}]}),
        dict(id="mem_031", type="boundary", content="Never share what Mia says with other users.", scope="user_global", sensitivity="S3", status="active", confidence=1.0, portability=portable, source={"event_id": "evt_031", "source_type": "explicit_instruction", "timestamp": days_ago(24), "quote": "What I tell you stays between us."}, valid_from=days_ago(24), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(1), usage_count=7, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_032", type="boundary", content="Don't bring up Mia's ex-partner.", scope="relationship_only", sensitivity="S2", status="active", confidence=0.94, portability=portable, source={"event_id": "evt_032", "source_type": "explicit_instruction", "timestamp": days_ago(16), "quote": "Please don't mention my ex."}, valid_from=days_ago(16), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(3), usage_count=5, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_033", type="boundary", content="No health advice — direct to a professional.", scope="user_global", sensitivity="S3", status="active", confidence=1.0, portability=portable, source={"event_id": "evt_033", "source_type": "explicit_instruction", "timestamp": days_ago(22), "quote": "Don't try to be my doctor."}, valid_from=days_ago(22), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(4), usage_count=3, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        # ---- Tasks (6) ----
        dict(id="mem_034", type="task", content="Remind Mia to call her mom this weekend.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.9, portability=portable, source={"event_id": "evt_034", "source_type": "explicit_instruction", "timestamp": days_ago(2), "quote": "Remind me to call Mom this weekend."}, valid_from=days_ago(2), expires_at=days_ago(-2), version=1, supersedes=None, last_used_at=days_ago(1), usage_count=3, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": [{"model": "gpt-4o", "used": True, "timestamp": days_ago(1)}]}),
        dict(id="mem_035", type="task", content="Remind Mia to water plants on Sundays.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.88, portability=portable, source={"event_id": "evt_035", "source_type": "explicit_instruction", "timestamp": days_ago(5), "quote": "Plants every Sunday, don't let me forget."}, valid_from=days_ago(5), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(2), usage_count=2, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_036", type="task", content="Temporary task: remind tomorrow about the dentist.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.85, portability=device_local, source={"event_id": "evt_036", "source_type": "explicit_instruction", "timestamp": days_ago(1), "quote": "Remind me tomorrow, dentist appointment."}, valid_from=days_ago(1), expires_at=days_ago(0), version=1, supersedes=None, last_used_at=None, usage_count=0, device_id=DEVICE_V1_ID, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_037", type="task", content="Follow up on the book recommendation next week.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.79, portability=portable, source={"event_id": "evt_037", "source_type": "chat", "timestamp": days_ago(4), "quote": "Ask me how the book is next week."}, valid_from=days_ago(4), expires_at=days_ago(-3), version=1, supersedes=None, last_used_at=None, usage_count=0, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_038", type="task", content="v1 sensor calibration reminder.", scope="device_only", sensitivity="S0", status="active", confidence=0.95, portability=device_local, source={"event_id": "evt_038", "source_type": "robot_event", "timestamp": days_ago(10), "quote": "[v1 system] sensor cal due."}, valid_from=days_ago(10), expires_at=None, version=1, supersedes=None, last_used_at=None, usage_count=0, device_id=DEVICE_V1_ID, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_039", type="task", content="Suggest a wind-down playlist at 10:30pm.", scope="relationship_only", sensitivity="S0", status="active", confidence=0.83, portability=portable, source={"event_id": "evt_039", "source_type": "explicit_instruction", "timestamp": days_ago(6), "quote": "Queue something calming around 10:30."}, valid_from=days_ago(6), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(1), usage_count=5, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        # ---- Archived (3) ----
        dict(id="mem_040", type="event", content="Mia's old work schedule (9-5, changed).", scope="relationship_only", sensitivity="S0", status="archived", confidence=0.4, portability=portable, source={"event_id": "evt_040", "source_type": "chat", "timestamp": days_ago(24), "quote": "I'm on a 9-5 right now."}, valid_from=days_ago(24), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(12), usage_count=4, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_041", type="preference", content="Outdated preference for morning jokes (retracted).", scope="relationship_only", sensitivity="S1", status="archived", confidence=0.3, portability=portable, source={"event_id": "evt_041", "source_type": "chat", "timestamp": days_ago(22), "quote": "Morning jokes are fun."}, valid_from=days_ago(22), expires_at=None, version=1, supersedes=None, last_used_at=days_ago(10), usage_count=6, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
        dict(id="mem_042", type="task", content="One-off reminder: pick up dry cleaning (done).", scope="relationship_only", sensitivity="S0", status="archived", confidence=0.9, portability=portable, source={"event_id": "evt_042", "source_type": "explicit_instruction", "timestamp": days_ago(13), "quote": "Remind me about dry cleaning."}, valid_from=days_ago(13), expires_at=days_ago(6), version=1, supersedes=None, last_used_at=days_ago(6), usage_count=1, model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []}),
    ]

    return [_mk(m) for m in seeds]


def migration() -> dict:
    """mig_001 — the v1→v2 migration wedge, in preview status."""
    return {
        "id": "mig_001",
        "tenant_id": TENANT_ID,
        "user_id": PRIMARY_USER_ID,
        "source_relationship_id": PRIMARY_RELATIONSHIP_ID,
        "target_relationship_id": "rel_mia_luna_v2",
        "source_device_id": DEVICE_V1_ID,
        "target_device_id": DEVICE_V2_ID,
        "status": "preview",
        "selected_memory_ids": [],
        "skipped_memory_ids": [],
        "failed_memory_ids": [],
        "rollback_snapshot": {},
        "old_device_access": "remove",
        "audit_log_id": None,
        "created_at": hours_ago(2),
        "completed_at": None,
        "rolled_back_at": None,
    }


def audit_logs() -> list[dict]:
    return [
        {"id": "al_1", "tenant_id": TENANT_ID, "actor": "Dev Patel", "action": "memory.created", "target": "mem_029", "detail": "Auto-written from chat event evt_029", "timestamp": days_ago(1)},
        {"id": "al_2", "tenant_id": TENANT_ID, "actor": "Sara Kim", "action": "memory.viewed", "target": "mem_030", "detail": "Viewed source in Debugger (elevated)", "timestamp": days_ago(1)},
        {"id": "al_3", "tenant_id": TENANT_ID, "actor": "Mia Chen", "action": "policy.changed", "target": "pol_luna_default", "detail": "Enabled cross_model portability", "timestamp": days_ago(2)},
        {"id": "al_4", "tenant_id": TENANT_ID, "actor": "Dev Patel", "action": "device.bound", "target": "dev_luna_v1", "detail": "Bound to usr_mia via QR pairing", "timestamp": days_ago(20)},
        {"id": "al_5", "tenant_id": TENANT_ID, "actor": "Mia Chen", "action": "memory.edited", "target": "mem_007", "detail": "Edited content (language preference)", "timestamp": days_ago(3)},
        {"id": "al_6", "tenant_id": TENANT_ID, "actor": "System", "action": "memory.deleted", "target": "mem_043", "detail": "User deleted via Memory Center (tombstone)", "timestamp": days_ago(4)},
        {"id": "al_7", "tenant_id": TENANT_ID, "actor": "Mia Chen", "action": "memory.exported", "target": "usr_mia", "detail": "User exported 42 memories (JSON)", "timestamp": days_ago(5)},
        {"id": "al_8", "tenant_id": TENANT_ID, "actor": "System", "action": "device.unbound", "target": "dev_luna_v1_003", "detail": "Auto-unbind after 9 days inactive", "timestamp": days_ago(9)},
    ]


# Acceptance-criteria counts — the seed tests assert against these.
EXPECTED_COUNTS = {
    "tenants": 1,
    "apps": 1,
    "api_keys": 2,
    "users": 4,
    "agents": 2,
    "devices": 4,
    "relationships": 1,
    "memory_policies": 1,
    "auto_write_rules": 6,
    "memory_records": 42,
    "migrations": 1,
    "audit_logs": 8,
}
