"""Application configuration loaded from environment variables.

All settings have safe dev defaults so `docker-compose up` works out of the
box against the seeded stack. Override via the `.env` file at the repo root.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the Memory Passport backend.

    See `backend/README.md` and `.env.example` (repo root) for the full list.
    """

    model_config = SettingsConfigDict(
        env_prefix="MP_",
        # Allow HMS_API_URL / HMS_API_KEY / DATABASE_URL through without the MP_ prefix
        # — they're shared conventions and the compose file injects them bare.
        extra="ignore",
    )

    # ---- Database ----------------------------------------------------------
    # e.g. postgresql+psycopg://mp:...@postgres:5432/memory_passport
    database_url: str = Field(
        default="postgresql+psycopg://mp:mp_dev_password_change_me@localhost:5432/memory_passport",
        validation_alias="DATABASE_URL",
    )

    # ---- HMS upstream ------------------------------------------------------
    # MP calls hms-api directly over the compose network with this bearer token.
    hms_api_url: str = Field(default="http://localhost:18080", validation_alias="HMS_API_URL")
    hms_api_key: str = Field(default="hms_tenant_luna_change_me", validation_alias="HMS_API_KEY")
    memory_engine_mode: Literal["demo", "real"] = "demo"

    # Real-HMS mode validates these before the server starts.  They are passed
    # through to the HMS containers by Compose and never exposed by MP APIs.
    hms_llm_api_key: str = Field(
        default="openai_key_change_me",
        validation_alias="HMS_API_LLM_API_KEY",
    )
    hms_retain_llm_api_key: str = Field(
        default="openai_key_change_me",
        validation_alias="HMS_API_RETAIN_LLM_API_KEY",
    )
    hms_embeddings_api_key: str = Field(
        default="openai_key_change_me",
        validation_alias="HMS_API_EMBEDDINGS_OPENAI_API_KEY",
    )

    # ---- Server -----------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # ---- Migrations -------------------------------------------------------
    # When True the app lifespan runs `alembic upgrade head` on startup, so a
    # fresh `docker-compose up` is immediately usable. Tests turn this off.
    run_migrations_on_startup: bool = True

    # ---- Seed -------------------------------------------------------------
    # Seeded sandbox API key — must match src/lib/mock-data.ts so the
    # "valid sandbox key authenticates" acceptance test holds.
    seed_api_key: str = "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd"

    # ---- Model-neutral exports -------------------------------------------
    export_dir: str = "/tmp/memory-passport-exports"
    export_token_ttl_seconds: int = 900

    @property
    def async_database_url(self) -> str:
        """DATABASE_URL rewritten for SQLAlchemy's async driver.

        Tests use sqlite (no rewrite needed); production uses psycopg's
        synchronous driver (``postgresql+psycopg://``) which SQLAlchemy 2
        accepts on the sync engine, so this returns the URL unchanged for non-
        async use. Kept here for the later slice that moves to async sessions.
        """
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


def validate_real_hms_configuration(settings: Settings) -> None:
    """Fail fast when real HMS mode still contains example credentials."""
    if settings.memory_engine_mode != "real":
        return
    credentials = (
        settings.hms_llm_api_key,
        settings.hms_retain_llm_api_key,
        settings.hms_embeddings_api_key,
    )
    if any(not value or value.endswith("_change_me") for value in credentials):
        raise RuntimeError(
            "real HMS mode requires non-placeholder LLM, retain-LLM, and "
            "embedding credentials; see docs/real-hms.md"
        )
