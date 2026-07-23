"""Persistence contract for V0.1 console team and trace feedback data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.db.session import session_scope
from app.models.enums import AuditAction, TeamRole
from app.models.retrieval_trace import RetrievalTrace
from app.models.team import TeamInvite, TeamMember
from app.services.ids import new_team_invite_id, new_team_member_id


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_console_models_and_feedback_column_are_registered() -> None:
    assert {"team_members", "team_invites"} <= set(Base.metadata.tables)
    assert "feedback" in RetrievalTrace.__table__.columns


def test_console_audit_actions_are_public_enum_values() -> None:
    assert {
        "api_key.created",
        "api_key.rotated",
        "user.consent_changed",
        "retrieval.feedback_recorded",
        "team.invited",
        "team.joined",
    } <= {action.value for action in AuditAction}


def test_team_ids_are_typed_and_opaque() -> None:
    member_id = new_team_member_id()
    invite_id = new_team_invite_id()

    assert member_id.startswith("tm_") and len(member_id) > len("tm_") + 8
    assert invite_id.startswith("tmi_") and len(invite_id) > len("tmi_") + 8


def test_team_rows_and_trace_feedback_round_trip(seeded_auth_rows) -> None:
    now = _now()
    member = TeamMember(
        id="tm_schema",
        tenant_id="ten_luna",
        name="Schema Tester",
        email="schema@example.com",
        role=TeamRole.ADMIN,
        avatar_color="#1E3A8A",
        joined_at=now,
        last_active=now,
    )
    invite = TeamInvite(
        id="tmi_schema",
        tenant_id="ten_luna",
        email="invite@example.com",
        role=TeamRole.SUPPORT,
        token_hash="a" * 64,
        created_by="api:key_sb_1",
        created_at=now,
        expires_at=now + timedelta(days=7),
        accepted_at=None,
        accepted_member_id=None,
    )
    trace = RetrievalTrace(
        id="trc_schema",
        tenant_id="ten_luna",
        query="What does Mia like?",
        caller={"user_id": "usr_mia"},
        hms_results={"results": []},
        projected={"results": [{"id": "mem_001"}]},
        retrieval_events={"events": []},
        feedback={
            "category": "useful",
            "memory_id": "mem_001",
            "actor": "api:key_sb_1",
            "timestamp": now.isoformat(),
        },
        created_at=now,
    )

    with session_scope() as db:
        db.add_all([member, invite, trace])

    with session_scope() as db:
        stored_member = db.get(TeamMember, member.id)
        stored_invite = db.get(TeamInvite, invite.id)
        stored_trace = db.get(RetrievalTrace, trace.id)

        assert stored_member is not None and stored_member.role == TeamRole.ADMIN
        assert stored_invite is not None and stored_invite.token_hash == "a" * 64
        assert stored_trace is not None
        assert stored_trace.feedback["category"] == "useful"


def test_team_member_email_is_unique_per_tenant(seeded_auth_rows) -> None:
    now = _now()
    common = {
        "tenant_id": "ten_luna",
        "email": "duplicate@example.com",
        "role": TeamRole.SUPPORT,
        "avatar_color": "#1E3A8A",
        "joined_at": now,
        "last_active": now,
    }

    with pytest.raises(IntegrityError), session_scope() as db:
        db.add_all(
            [
                TeamMember(id="tm_dup_1", name="First", **common),
                TeamMember(id="tm_dup_2", name="Second", **common),
            ]
        )
