"""Credential-free, deterministic subset of the pinned HMS HTTP API.

This service exists only for local evaluation.  It deliberately preserves the
network boundary and response fields consumed by Memory Passport while
replacing model extraction and vector search with reproducible storage and
token-overlap ranking.  The real Compose overlay runs the vendored HMS API and
worker instead.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.engine import RowMapping

_metadata = MetaData()

_banks = Table(
    "demo_hms_banks",
    _metadata,
    Column("id", String(255), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

_memory_units = Table(
    "demo_hms_memory_units",
    _metadata,
    Column("id", String(64), primary_key=True),
    Column(
        "bank_id",
        String(255),
        ForeignKey("demo_hms_banks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("text", Text, nullable=False),
    Column("fact_type", String(32), nullable=False, default="world"),
    Column("context", Text, nullable=True),
    Column("document_id", String(255), nullable=False, index=True),
    Column("item_metadata", JSON, nullable=False, default=dict),
    Column("tags", JSON, nullable=False, default=list),
    Column("mentioned_at", String(64), nullable=True),
    Column("proof_count", Integer, nullable=False, default=1),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


class RetainItem(BaseModel):
    """The retain fields Memory Passport sends to HMS."""

    content: str = Field(min_length=1)
    context: str | None = None
    timestamp: str | None = None
    document_id: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetainRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[RetainItem] = Field(min_length=1)
    async_: bool = Field(default=False, alias="async")


class RecallRequest(BaseModel):
    query: str
    types: list[str] | None = None
    budget: str = "mid"
    trace: bool = False
    tags: list[str] | None = None
    tags_match: Literal["any", "all", "any_strict", "all_strict"] = "any"


class UpdateDocumentRequest(BaseModel):
    tags: list[str]


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE))


def _unit_id(bank_id: str, item: RetainItem) -> str:
    identity = f"{bank_id}:{item.document_id}:{item.content}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, identity))


def _serialize_unit(row: RowMapping) -> dict[str, Any]:
    return {
        "id": row["id"],
        "text": row["text"],
        "type": row["fact_type"],
        "context": row["context"],
        "document_id": row["document_id"],
        "metadata": row["item_metadata"] or {},
        "tags": row["tags"] or [],
        "mentioned_at": row["mentioned_at"],
        "proof_count": row["proof_count"],
    }


def _matches_tags(
    row_tags: list[str],
    requested: list[str] | None,
    mode: str,
) -> bool:
    if requested is None:
        return True
    requested_set = set(requested)
    row_set = set(row_tags)
    strict = mode.endswith("_strict")
    if not row_set:
        return not strict
    if mode.startswith("all"):
        return requested_set.issubset(row_set)
    return bool(requested_set.intersection(row_set))


def create_demo_hms_app(database_url: str | None = None) -> FastAPI:
    """Create the deterministic HMS-compatible application."""

    resolved_url = database_url or os.getenv(
        "DEMO_HMS_DATABASE_URL",
        "sqlite:////tmp/memory-passport-demo-hms.sqlite3",
    )
    engine = create_engine(resolved_url, future=True, pool_pre_ping=True)
    _metadata.create_all(engine)

    app = FastAPI(
        title="Memory Passport deterministic HMS",
        description="Credential-free local evaluation service; not semantic HMS parity.",
        version="0.1.0",
    )
    app.state.engine = engine

    def require_auth(
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        expected = os.getenv("HMS_API_TENANT_API_KEY", "hms_tenant_luna_change_me")
        if authorization != f"Bearer {expected}":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid HMS API key",
            )

    auth = [Depends(require_auth)]

    @app.get("/health")
    def health() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(select(1))
        return {"status": "healthy", "mode": "demo"}

    @app.put("/v1/default/banks/{bank_id}", dependencies=auth)
    def put_bank(bank_id: str) -> dict[str, Any]:
        with engine.begin() as connection:
            exists = connection.scalar(select(_banks.c.id).where(_banks.c.id == bank_id))
            if exists is None:
                connection.execute(insert(_banks).values(id=bank_id, created_at=_now()))
        return {"bank_id": bank_id, "created": exists is None, "mode": "demo"}

    @app.get("/v1/default/banks", dependencies=auth)
    def list_banks() -> dict[str, list[dict[str, str]]]:
        with engine.connect() as connection:
            ids = connection.scalars(select(_banks.c.id).order_by(_banks.c.id)).all()
        return {"banks": [{"id": bank_id, "bank_id": bank_id} for bank_id in ids]}

    @app.delete("/v1/default/banks/{bank_id}", dependencies=auth)
    def delete_bank(bank_id: str) -> dict[str, Any]:
        with engine.begin() as connection:
            memory_count = connection.scalar(
                select(func.count()).select_from(_memory_units).where(
                    _memory_units.c.bank_id == bank_id
                )
            )
            connection.execute(
                delete(_memory_units).where(_memory_units.c.bank_id == bank_id)
            )
            result = connection.execute(delete(_banks).where(_banks.c.id == bank_id))
        return {
            "success": True,
            "deleted_count": int(memory_count or 0),
            "bank_deleted": result.rowcount > 0,
        }

    @app.post("/v1/default/banks/{bank_id}/memories", dependencies=auth)
    def retain(bank_id: str, body: RetainRequest) -> dict[str, Any]:
        with engine.begin() as connection:
            bank_exists = connection.scalar(
                select(_banks.c.id).where(_banks.c.id == bank_id)
            )
            if bank_exists is None:
                connection.execute(insert(_banks).values(id=bank_id, created_at=_now()))
            for item in body.items:
                unit_id = _unit_id(bank_id, item)
                exists = connection.scalar(
                    select(_memory_units.c.id).where(_memory_units.c.id == unit_id)
                )
                if exists is None:
                    connection.execute(
                        insert(_memory_units).values(
                            id=unit_id,
                            bank_id=bank_id,
                            text=item.content,
                            fact_type="world",
                            context=item.context,
                            document_id=item.document_id,
                            item_metadata=item.metadata,
                            tags=item.tags,
                            mentioned_at=item.timestamp,
                            proof_count=1,
                            created_at=_now(),
                        )
                    )
        return {
            "success": True,
            "items_count": len(body.items),
            "async": body.async_,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "mode": "demo",
        }

    @app.get("/v1/default/banks/{bank_id}/memories/list", dependencies=auth)
    def list_memories(
        bank_id: str,
        q: str | None = None,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        filters = [_memory_units.c.bank_id == bank_id]
        if q:
            filters.append(_memory_units.c.text.ilike(f"%{q}%"))
        with engine.connect() as connection:
            total = connection.scalar(
                select(func.count()).select_from(_memory_units).where(*filters)
            )
            rows = connection.execute(
                select(_memory_units)
                .where(*filters)
                .order_by(_memory_units.c.created_at, _memory_units.c.id)
                .limit(limit)
                .offset(offset)
            ).mappings()
            items = [_serialize_unit(row) for row in rows]
        return {"items": items, "total": int(total or 0), "limit": limit, "offset": offset}

    @app.post("/v1/default/banks/{bank_id}/memories/recall", dependencies=auth)
    def recall(bank_id: str, body: RecallRequest) -> dict[str, Any]:
        query_tokens = _tokens(body.query)
        with engine.connect() as connection:
            rows = connection.execute(
                select(_memory_units).where(_memory_units.c.bank_id == bank_id)
            ).mappings()
            ranked: list[tuple[int, str, dict[str, Any]]] = []
            for row in rows:
                serialized = _serialize_unit(row)
                if not _matches_tags(serialized["tags"], body.tags, body.tags_match):
                    continue
                score = len(query_tokens.intersection(_tokens(serialized["text"])))
                if query_tokens and score == 0:
                    continue
                ranked.append((score, serialized["id"], serialized))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        response: dict[str, Any] = {"results": [item[2] for item in ranked]}
        if body.trace:
            response["trace"] = {
                "query": body.query,
                "num_results": len(ranked),
                "mode": "demo",
            }
        return response

    @app.patch("/v1/default/banks/{bank_id}/documents/{document_id:path}", dependencies=auth)
    def update_document(
        bank_id: str,
        document_id: str,
        body: UpdateDocumentRequest,
    ) -> dict[str, Any]:
        with engine.begin() as connection:
            rows = connection.execute(
                select(_memory_units.c.id).where(
                    _memory_units.c.bank_id == bank_id,
                    _memory_units.c.document_id == document_id,
                )
            ).all()
            if not rows:
                raise HTTPException(status_code=404, detail="Document not found")
            from sqlalchemy import update

            connection.execute(
                update(_memory_units)
                .where(
                    _memory_units.c.bank_id == bank_id,
                    _memory_units.c.document_id == document_id,
                )
                .values(tags=body.tags)
            )
        return {"success": True}

    @app.delete("/v1/default/banks/{bank_id}/documents/{document_id:path}", dependencies=auth)
    def delete_document(bank_id: str, document_id: str) -> dict[str, Any]:
        with engine.begin() as connection:
            result = connection.execute(
                delete(_memory_units).where(
                    _memory_units.c.bank_id == bank_id,
                    _memory_units.c.document_id == document_id,
                )
            )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "success": True,
            "document_id": document_id,
            "memory_units_deleted": result.rowcount,
        }

    return app


app = create_demo_hms_app()


__all__ = ["app", "create_demo_hms_app"]
