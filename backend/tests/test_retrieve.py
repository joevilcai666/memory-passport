"""Integration tests for POST /v1/memories/retrieve + GET /v1/debug/traces (Slice 4).

Strategy: ingest memories via the Slice 3 ingest endpoint (mocked HMS), then
retrieve (also mocked HMS recall) and assert scope filtering, masking,
retrieval_history append, max-per-response cap, and trace round-trip.

The retrieve pipeline joins HMS recall results to MP records via the mapping
table, so the test mocks HMS recall to return the same hms_unit_ids the ingest
flow created. This faithfully exercises the MP↔HMS mapping + the scope matrix
without needing a live HMS.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import respx

from app.db.session import session_scope
from app.models.enums import (
    AuditAction,
    MemoryScope,
    MemorySensitivity,
    MemoryStatus,
    MemoryType,
)
from app.models.identity import Agent, Device, Relationship, User
from app.models.memory import MemoryPolicy, MemoryRecord
from app.models.memory_mapping import MemoryRecordHmsUnit
from app.models.retrieval_trace import RetrievalTrace
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def auth_headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture()
def seeded_for_retrieve(sqlite_db):
    """Seed tenant/app/key + user/agent-with-policy/relationship for retrieve.

    The agent's policy sets max_memories_per_response=3 and
    include_sensitive_in_prompt=False (so S2/S3 content is masked by default).
    """
    tenant_id = "ten_retr"
    app_id = "app_retr"
    agent_id = "agt_retr"
    policy_id = "pol_retr"
    user_id = "usr_retr"
    rel_id = "rel_retr"
    key = "mp_sandbox_retrieve_retrieve_retrieve_re"

    with session_scope() as db:
        db.add(Tenant(id=tenant_id, name="Retrieve Co.", plan="Sandbox", created_at=_now()))
        db.add(
            App(
                id=app_id,
                tenant_id=tenant_id,
                name="Retrieve",
                product_type="software",
                environment="sandbox",
                data_region="us-east-1",
                show_powered_by=False,
                status="active",
                created_at=_now(),
            )
        )
        db.add(
            ApiKey(
                id="key_retr_1",
                app_id=app_id,
                label="Sandbox",
                environment="sandbox",
                key=key,
                created_at=_now(),
                last_used_at=_now(),
            )
        )
        db.add(
            User(
                id=user_id,
                tenant_id=tenant_id,
                external_user_id="ext_retr",
                passport_id="pp_retr_001",
                age_group="adult",
                region="US",
                memory_enabled=True,
                created_at=_now(),
                display_name="Retrieve Tester",
                avatar_color="#6366f1",
            )
        )
        db.add(
            Agent(
                id=agent_id,
                app_id=app_id,
                name="Retrieve Agent",
                type="companion",
                persona_version="v1",
                memory_policy_id=None,
                allowed_memory_types=["preference", "relationship", "event"],
                created_at=_now(),
                emoji="🔍",
            )
        )
        db.flush()
        db.add(
            MemoryPolicy(
                id=policy_id,
                app_id=app_id,
                agent_id=agent_id,
                portability={
                    "layer": "portable",
                    "cross_device": True,
                    "cross_role": True,
                    "cross_model": True,
                    "cross_brand_app": False,
                },
                retrieval={
                    "max_memories_per_response": 3,
                    "include_sensitive_in_prompt": False,
                },
            )
        )
        db.flush()
        db.query(Agent).filter(Agent.id == agent_id).update({"memory_policy_id": policy_id})
        db.add(
            Relationship(
                id=rel_id,
                tenant_id=tenant_id,
                user_id=user_id,
                agent_id=agent_id,
                device_id=None,
                relationship_type="companion",
                memory_enabled=True,
                created_at=_now(),
            )
        )

    return {
        "key": key,
        "tenant_id": tenant_id,
        "app_id": app_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "rel_id": rel_id,
        "key_id": "key_retr_1",
    }


def _make_record(
    *,
    mp_id: str,
    tenant_id: str,
    app_id: str,
    user_id: str,
    agent_id: str,
    rel_id: str,
    hms_unit_id: str,
    scope: MemoryScope,
    sensitivity: MemorySensitivity = MemorySensitivity.S1,
    status: MemoryStatus = MemoryStatus.ACTIVE,
    content: str = "a memory",
    device_id: str | None = None,
) -> tuple[MemoryRecord, MemoryRecordHmsUnit]:
    """Build a MemoryRecord + its mapping row in one go (helper for tests)."""
    now = _now()
    rec = MemoryRecord(
        id=mp_id,
        tenant_id=tenant_id,
        app_id=app_id,
        passport_id="pp_retr_001",
        user_id=user_id,
        relationship_id=rel_id,
        agent_id=agent_id,
        device_id=device_id,
        type=MemoryType.PREFERENCE,
        content=content,
        scope=scope,
        sensitivity=sensitivity,
        status=status,
        confidence=0.9,
        portability={
            "layer": "portable",
            "cross_device": True,
            "cross_role": True,
            "cross_model": True,
            "cross_brand_app": False,
        },
        source={
            "event_id": "evt_seed",
            "source_type": "chat",
            "timestamp": now.isoformat(),
            "quote": content,
        },
        valid_from=now,
        expires_at=None,
        version=1,
        supersedes=None,
        last_used_at=None,
        usage_count=0,
        model_provenance={"created_by_model": "gpt-4o", "retrieval_history": []},
    )
    mapping = MemoryRecordHmsUnit(
        mp_memory_id=mp_id,
        tenant_id=tenant_id,
        hms_unit_id=hms_unit_id,
        hms_bank_id=user_id,
        hms_document_id="evt_seed",
        created_at=now,
    )
    return rec, mapping


def _seed_records(s, records):
    """Persist a batch of (record, mapping) tuples."""
    with session_scope() as db:
        for rec, mapping in records:
            db.add(rec)
            db.flush()
            db.add(mapping)


def _mock_recall(returning_unit_ids: list[str]):
    """Build a respx side-effect that returns the given hms_unit_ids ranked."""

    def handler(request):
        results = [
            {"id": uid, "text": f"fact {uid}", "type": "world"} for uid in returning_unit_ids
        ]
        return respx.MockResponse(200, json={"results": results})

    return handler


def test_tombstoned_memory_is_excluded_from_subsequent_retrieve(
    seeded_for_retrieve, app_client
):
    """Slice 5 DELETE removes the join mapping before the next HMS recall."""
    s = seeded_for_retrieve
    record, mapping = _make_record(
        mp_id="mem_delete_then_retrieve",
        tenant_id=s["tenant_id"],
        app_id=s["app_id"],
        user_id=s["user_id"],
        agent_id=s["agent_id"],
        rel_id=s["rel_id"],
        hms_unit_id="hms_delete_then_retrieve",
        scope=MemoryScope.RELATIONSHIP_ONLY,
    )
    _seed_records(s, [(record, mapping)])

    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.delete(url__regex=r"/v1/default/banks/usr_retr/documents/.*").respond(
            200, json={"deleted": True}
        )
        mock.post(url__regex=r"/v1/default/banks/usr_retr/memories/recall$").mock(
            side_effect=_mock_recall(["hms_delete_then_retrieve"])
        )
        deleted = app_client.delete(
            "/v1/memories/mem_delete_then_retrieve",
            headers=auth_headers(s["key"]),
        )
        recalled = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "anything",
                "model": "test-model",
            },
        )

    assert deleted.status_code == 200
    assert recalled.status_code == 200
    assert recalled.json()["results"] == []


# ---------------------------------------------------------------------------
# Scope filtering matrix
# ---------------------------------------------------------------------------


def test_retrieve_filters_blocked_and_out_of_scope(seeded_for_retrieve, app_client):
    """blocked + out-of-scope private/agent_only/device_only are filtered."""
    s = seeded_for_retrieve
    _seed_records(s, [
        _make_record(mp_id="mem_global", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_global", scope=MemoryScope.USER_GLOBAL,
                     content="global memory"),
        _make_record(mp_id="mem_blocked", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_blocked", scope=MemoryScope.BLOCKED,
                     content="blocked memory"),
        _make_record(mp_id="mem_other_agent", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id="agt_someone_else", rel_id=s["rel_id"],
                     hms_unit_id="hms_agent_only", scope=MemoryScope.AGENT_ONLY,
                     content="agent-only on another agent"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(
                ["hms_global", "hms_blocked", "hms_agent_only"]
            )
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "anything",
                "model": "gpt-4o",
            },
        )
    assert resp.status_code == 200, resp.text
    ids = [r["id"] for r in resp.json()["results"]]
    assert ids == ["mem_global"]  # blocked + other-agent's agent_only filtered


def test_retrieve_device_only_filtered_for_non_device_caller(seeded_for_retrieve, app_client):
    """A non-device caller doesn't get device_only memories."""
    s = seeded_for_retrieve
    _seed_records(s, [
        _make_record(mp_id="mem_dev", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_dev", scope=MemoryScope.DEVICE_ONLY,
                     content="device-only memory", device_id="dev_x"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_dev"])
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
                # no device_id — caller is not a device
            },
        )
    assert resp.status_code == 200
    assert resp.json()["results"] == []  # device_only filtered out


# ---------------------------------------------------------------------------
# Wiped device loses device_only access (coordination with Slice 7)
# ---------------------------------------------------------------------------


def test_retrieve_device_only_filtered_when_device_wiped(seeded_for_retrieve, app_client):
    """A wiped device must NOT read device_only memories (PRD §9.1 + Slice 7)."""
    s = seeded_for_retrieve
    # Seed a bound-then-wiped device + a device_only memory on it.
    with session_scope() as db:
        db.add(
            Device(
                id="dev_wiped",
                tenant_id=s["tenant_id"],
                model="R1",
                generation="v1",
                serial_number_hash="abc",
                status="wiped",  # the Slice 7 outcome
                bound_user_id=None,
                last_seen_at=_now(),
            )
        )
    _seed_records(s, [
        _make_record(mp_id="mem_dev_wiped", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_dev_wiped", scope=MemoryScope.DEVICE_ONLY,
                     content="on wiped device", device_id="dev_wiped"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_dev_wiped"])
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
                "device_id": "dev_wiped",  # caller identifies as the wiped device
            },
        )
    assert resp.status_code == 200
    assert resp.json()["results"] == []  # wiped device -> device_only filtered


def test_retrieve_device_only_returned_for_bound_device(seeded_for_retrieve, app_client):
    """A bound device CAN read its own device_only memories."""
    s = seeded_for_retrieve
    with session_scope() as db:
        db.add(
            Device(
                id="dev_bound",
                tenant_id=s["tenant_id"],
                model="R1",
                generation="v1",
                serial_number_hash="abc",
                status="bound",
                bound_user_id=s["user_id"],
                last_seen_at=_now(),
            )
        )
    _seed_records(s, [
        _make_record(mp_id="mem_dev_bound", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_dev_bound", scope=MemoryScope.DEVICE_ONLY,
                     content="on bound device", device_id="dev_bound"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_dev_bound"])
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
                "device_id": "dev_bound",
            },
        )
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()["results"]]
    assert ids == ["mem_dev_bound"]


# ---------------------------------------------------------------------------
# Sensitivity masking
# ---------------------------------------------------------------------------


def test_retrieve_masks_s2_s3_when_toggle_off(seeded_for_retrieve, app_client):
    """S2/S3 content is masked when include_sensitive_in_prompt is false."""
    s = seeded_for_retrieve  # policy has include_sensitive_in_prompt=False
    _seed_records(s, [
        _make_record(mp_id="mem_s0", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_s0", scope=MemoryScope.USER_GLOBAL,
                     sensitivity=MemorySensitivity.S0, content="public fact"),
        _make_record(mp_id="mem_s2", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_s2", scope=MemoryScope.USER_GLOBAL,
                     sensitivity=MemorySensitivity.S2, content="sensitive fact"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_s0", "hms_s2"])
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
            },
        )
    assert resp.status_code == 200
    by_id = {r["id"]: r["content"] for r in resp.json()["results"]}
    assert by_id["mem_s0"] == "public fact"  # S0 untouched
    assert by_id["mem_s2"] == "[redacted]"  # S2 masked


def test_retrieve_returns_full_content_when_toggle_on(seeded_for_retrieve, app_client):
    """When include_sensitive_in_prompt is true, S2 content is returned in full."""
    s = seeded_for_retrieve
    # Flip the policy toggle ON.
    with session_scope() as db:
        pol = db.query(MemoryPolicy).filter(MemoryPolicy.id == "pol_retr").one()
        pol.retrieval = {**pol.retrieval, "include_sensitive_in_prompt": True}
    _seed_records(s, [
        _make_record(mp_id="mem_s2_on", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_s2_on", scope=MemoryScope.USER_GLOBAL,
                     sensitivity=MemorySensitivity.S2, content="sensitive fact"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_s2_on"])
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["content"] == "sensitive fact"


# ---------------------------------------------------------------------------
# Cap + retrieval_history append + usage_count
# ---------------------------------------------------------------------------


def test_retrieve_caps_at_max_per_response(seeded_for_retrieve, app_client):
    """Retrieve returns at most policy.retrieval.max_memories_per_response (3)."""
    s = seeded_for_retrieve
    _seed_records(s, [
        _make_record(mp_id=f"mem_cap_{i}", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id=f"hms_cap_{i}", scope=MemoryScope.USER_GLOBAL,
                     content=f"fact {i}")
        for i in range(5)
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall([f"hms_cap_{i}" for i in range(5)])
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
            },
        )
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 3  # capped at max_per_response=3


def test_retrieve_appends_retrieval_event_and_increments_usage(seeded_for_retrieve, app_client):
    """Each returned memory gets a RetrievalEvent + usage_count bump in the DB."""
    s = seeded_for_retrieve
    _seed_records(s, [
        _make_record(mp_id="mem_used", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_used", scope=MemoryScope.USER_GLOBAL,
                     content="will be retrieved"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_used"])
        )
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
                "model": "claude-3.5-sonnet",
            },
        )
    assert resp.status_code == 200
    with session_scope() as db:
        rec = db.query(MemoryRecord).filter(MemoryRecord.id == "mem_used").one()
        assert rec.usage_count == 1
        assert rec.last_used_at is not None
        history = rec.model_provenance["retrieval_history"]
        assert len(history) == 1
        assert history[0]["model"] == "claude-3.5-sonnet"
        assert history[0]["used"] is True


# ---------------------------------------------------------------------------
# Trace round-trip
# ---------------------------------------------------------------------------


def test_retrieve_returns_trace_id_and_debug_endpoint_round_trips(
    seeded_for_retrieve, app_client
):
    """trace_id is returned; GET /v1/debug/traces/{trace_id} returns the chain."""
    s = seeded_for_retrieve
    _seed_records(s, [
        _make_record(mp_id="mem_trace", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_trace", scope=MemoryScope.USER_GLOBAL,
                     content="traceable"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_trace"])
        )
        retrieve_resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "trace me",
                "model": "gpt-4o",
            },
        )
    assert retrieve_resp.status_code == 200
    trace_id = retrieve_resp.json()["trace_id"]

    # Fetch the trace via the debug endpoint (no HMS call needed).
    debug_resp = app_client.get(
        f"/v1/debug/traces/{trace_id}",
        headers=auth_headers(s["key"]),
    )
    assert debug_resp.status_code == 200, debug_resp.text
    trace = debug_resp.json()
    assert trace["id"] == trace_id
    assert trace["query"] == "trace me"
    assert trace["caller"]["user_id"] == s["user_id"]
    assert trace["caller"]["model"] == "gpt-4o"
    # The projected results are persisted on the trace.
    assert trace["projected"]["results"][0]["id"] == "mem_trace"
    # And the raw HMS results.
    assert trace["hms_results"]["results"][0]["id"] == "hms_trace"


def test_debug_trace_cross_tenant_returns_404(seeded_for_retrieve, app_client, sqlite_db):
    """A trace from another tenant isn't visible -> 404."""
    # Seed a second tenant + a trace under it.
    with session_scope() as db:
        db.add(Tenant(id="ten_other", name="Other", plan="Sandbox", created_at=_now()))
        db.add(
            RetrievalTrace(
                id="trc_other",
                tenant_id="ten_other",
                query="secret",
                caller={"user_id": "usr_other"},
                hms_results={"results": []},
                projected={"results": []},
                retrieval_events={"events": {}},
                created_at=_now(),
            )
        )
    resp = app_client.get(
        "/v1/debug/traces/trc_other",
        headers=auth_headers(seeded_for_retrieve["key"]),  # tenant_retr's key
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Audit + auth
# ---------------------------------------------------------------------------


def test_retrieve_writes_audit_row(seeded_for_retrieve, app_client):
    s = seeded_for_retrieve
    _seed_records(s, [
        _make_record(mp_id="mem_audit", tenant_id=s["tenant_id"], app_id=s["app_id"],
                     user_id=s["user_id"], agent_id=s["agent_id"], rel_id=s["rel_id"],
                     hms_unit_id="hms_audit", scope=MemoryScope.USER_GLOBAL,
                     content="audited"),
    ])
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").mock(
            side_effect=_mock_recall(["hms_audit"])
        )
        retrieve_resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
            },
        )
    assert retrieve_resp.status_code == 200
    with session_scope() as db:
        from app.models.audit import AuditLog

        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == s["tenant_id"],
                AuditLog.action == AuditAction.RETRIEVAL_PERFORMED,
            )
            .one()
        )
    assert audit.actor == f"api:{s['key_id']}"


def test_retrieve_requires_auth(app_client):
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        resp = app_client.post(
            "/v1/memories/retrieve",
            json={"user_id": "x", "agent_id": "y", "relationship_id": "z", "query": "q"},
        )
    assert resp.status_code == 401


def test_retrieve_hms_failure_returns_502(seeded_for_retrieve, app_client):
    s = seeded_for_retrieve
    with respx.mock(base_url="http://hms-api.test", assert_all_called=False) as mock:
        mock.get("/health").respond(200, json={"status": "healthy"})
        mock.post(url__regex=r"/v1/default/banks/[^/]+/memories/recall$").respond(500)
        resp = app_client.post(
            "/v1/memories/retrieve",
            headers=auth_headers(s["key"]),
            json={
                "user_id": s["user_id"],
                "agent_id": s["agent_id"],
                "relationship_id": s["rel_id"],
                "query": "x",
            },
        )
    assert resp.status_code == 502
    assert resp.json()["detail"]["code"] == "hms_recall_failed"
