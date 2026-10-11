from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.logging import redact_text


def test_defaults_are_safe_local_values() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
    assert settings.api_port == 8000
    assert settings.database_url.get_secret_value().endswith("/agentdb")
    assert "localhost:5433" in settings.database_url.get_secret_value()
    assert settings.cors_origins == ["http://localhost:3000"]


def test_database_url_is_required() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="")


def test_log_level_is_validated() -> None:
    settings = Settings(_env_file=None, log_level="debug")
    assert settings.log_level == "DEBUG"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level="loud")


def test_secret_is_not_exposed_in_summary_or_repr() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://postgres:supersecret@localhost:5433/agentdb",
    )
    summary = settings.safe_summary()
    assert "supersecret" not in str(summary)
    assert "supersecret" not in repr(settings)
    assert "supersecret" not in str(settings.model_dump())


def test_log_redaction_masks_secret_tokens() -> None:
    message = "connect api_key=abcd1234 password=hunter2 host=localhost"
    redacted = redact_text(message)
    assert "abcd1234" not in redacted
    assert "hunter2" not in redacted
    assert "***" in redacted
