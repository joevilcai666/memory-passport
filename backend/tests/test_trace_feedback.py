"""Persistent retrieval-feedback API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.session import session_scope
from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.retrieval_trace import RetrievalTrace
from app.models.tenant import ApiKey, App, Tenant


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture()
def feedback_rows(sqlite_db):
    key_a = "mp_sandbox_feedback_feedback_feedback_a"
    key_b = "mp_sandbox_feedback_feedback_feedback_b"
    with session_scope() as db:
        for suffix, key in (("a", key_a), ("b", key_b)):
            tenant_id = f"ten_feedback_{suffix}"
            app_id = f"app_feedback_{suffix}"
            db.add(
                Tenant(
                    id=tenant_id,
                    name=f"Feedback {suffix}",
                    plan="Sandbox",
                    created_at=_now(),
                )
            )
            db.add(
                App(
                    id=app_id,
                    tenant_id=tenant_id,
                    name=app_id,
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
                    id=f"key_feedback_{suffix}",
                    app_id=app_id,
                    label="Sandbox",
                    environment="sandbox",
                    key=key,
                    created_at=_now(),
                    last_used_at=_now(),
                )
            )
            db.add(
                RetrievalTrace(
                    id=f"trc_feedback_{suffix}",
                    tenant_id=tenant_id,
                    query="tea",
                    caller={"user_id": f"usr_{suffix}"},
                    hms_results={"results": []},
                    projected={"results": [{"id": f"mem_{suffix}_1"}, {"id": f"mem_{suffix}_2"}]},
                    retrieval_events={"events": {}},
                    feedback=None,
                    created_at=_now(),
                )
            )
    return {"key_a": key_a, "key_b": key_b}


@pytest.mark.parametrize(
    "category",
    ["useful", "not_useful", "wrong_memory", "should_not_have_used"],
)
def test_feedback_accepts_supported_categories_and_returns_persisted_trace(
    feedback_rows, app_client, category
):
    response = app_client.post(
        "/v1/debug/traces/trc_feedback_a/feedback",
        headers=_auth(feedback_rows["key_a"]),
        json={"memory_id": "mem_a_1", "category": category},
    )

    assert response.status_code == 200, response.text
    feedback = response.json()["feedback"]
    assert feedback["memory_id"] == "mem_a_1"
    assert feedback["category"] == category
    assert feedback["actor"] == "api:key_feedback_a"
    assert feedback["recorded_at"]


def test_feedback_upserts_and_trace_get_returns_latest_value(feedback_rows, app_client):
    headers = _auth(feedback_rows["key_a"])
    first = app_client.post(
        "/v1/debug/traces/trc_feedback_a/feedback",
        headers=headers,
        json={"memory_id": "mem_a_1", "category": "not_useful"},
    )
    assert first.status_code == 200, first.text

    second = app_client.post(
        "/v1/debug/traces/trc_feedback_a/feedback",
        headers=headers,
        json={"memory_id": "mem_a_2", "category": "wrong_memory"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["feedback"]["memory_id"] == "mem_a_2"

    fetched = app_client.get(
        "/v1/debug/traces/trc_feedback_a",
        headers=headers,
    )
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["feedback"]["category"] == "wrong_memory"

    with session_scope() as db:
        trace = db.get(RetrievalTrace, "trc_feedback_a")
        assert trace.feedback["memory_id"] == "mem_a_2"
        assert (
            db.query(AuditLog)
            .filter(AuditLog.action == AuditAction.RETRIEVAL_FEEDBACK_RECORDED)
            .count()
            == 2
        )


def test_feedback_rejects_memory_not_projected_in_trace(feedback_rows, app_client):
    response = app_client.post(
        "/v1/debug/traces/trc_feedback_a/feedback",
        headers=_auth(feedback_rows["key_a"]),
        json={"memory_id": "mem_not_projected", "category": "useful"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "invalid_feedback_target"


def test_feedback_is_tenant_scoped(feedback_rows, app_client):
    response = app_client.post(
        "/v1/debug/traces/trc_feedback_b/feedback",
        headers=_auth(feedback_rows["key_a"]),
        json={"memory_id": "mem_b_1", "category": "useful"},
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"]["code"] == "not_found"
