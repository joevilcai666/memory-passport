"""Database engine + session factory.

Sync SQLAlchemy 2 sessions over psycopg 3. The app uses one engine per process;
tests override :func:`get_engine` (via dependency injection of :func:`get_session`)
to point at an isolated sqlite/PG database.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import _JSON_DUMPS

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-global engine (lazy-initialised)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # `postgresql+psycopg://` is the SQLAlchemy 2 / psycopg 3 sync URL.
        # json_serializer handles nested datetimes (JSONB columns like
        # memory_records.source.timestamp) by encoding them as ISO strings,
        # matching src/lib/types.ts where they're typed as `string`.
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
            json_serializer=_JSON_DUMPS,
        )
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    """Return the process-global session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )
    return _SessionLocal


def reset_engine_for_tests(engine: Engine) -> None:
    """Point the session factory at a test-supplied engine.

    Tests call this once after creating their disposable DB so every part of
    the app (including modules that grab the engine at import time) sees it.
    """
    global _engine, _SessionLocal
    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yield a session and ensure it's closed."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for non-request code (seed script, tests, etc.).

    Commits on success, rolls back on exception, always closes.
    """
    db = get_sessionmaker()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
