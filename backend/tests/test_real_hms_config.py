"""Real-HMS mode fails fast on missing or placeholder credentials."""

from __future__ import annotations

import pytest


def test_real_hms_mode_rejects_placeholder_credentials(monkeypatch) -> None:
    monkeypatch.setenv("MP_MEMORY_ENGINE_MODE", "real")
    monkeypatch.setenv("HMS_API_LLM_API_KEY", "openai_key_change_me")
    monkeypatch.setenv("HMS_API_RETAIN_LLM_API_KEY", "retain_key_change_me")
    monkeypatch.setenv("HMS_API_EMBEDDINGS_OPENAI_API_KEY", "embedding_key_change_me")

    from app.config import Settings, validate_real_hms_configuration

    with pytest.raises(RuntimeError, match="real HMS mode requires non-placeholder"):
        validate_real_hms_configuration(Settings())


def test_real_hms_mode_accepts_non_placeholder_credentials(monkeypatch) -> None:
    monkeypatch.setenv("MP_MEMORY_ENGINE_MODE", "real")
    monkeypatch.setenv("HMS_API_LLM_API_KEY", "llm-secret")
    monkeypatch.setenv("HMS_API_RETAIN_LLM_API_KEY", "retain-secret")
    monkeypatch.setenv("HMS_API_EMBEDDINGS_OPENAI_API_KEY", "embedding-secret")

    from app.config import Settings, validate_real_hms_configuration

    validate_real_hms_configuration(Settings())
