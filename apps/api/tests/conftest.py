from __future__ import annotations

import pytest

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://postgres:postgres@localhost:5433/agentdb",
        redis_url="redis://localhost:6379/0",
        cors_origins=["http://localhost:3000"],
    )
