from __future__ import annotations

import re
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRET_PATTERN = re.compile(r"(api[_-]?key|password|secret|token|auth)", re.IGNORECASE)


def redact_value(value: str) -> str:
    if _SECRET_PATTERN.search(value):
        return "***"
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development")
    app_name: str = Field(default="AI Operations Agent")
    log_level: str = Field(default="INFO")
    api_host: str = Field(default="0.0.0.0")  # noqa: S104 - container bind address, not a public default
    api_port: int = Field(default=8000, ge=1, le=65535)

    database_url: SecretStr = Field(
        default=SecretStr("postgresql+psycopg://postgres:postgres@localhost:5433/agentdb")
    )
    redis_url: str = Field(default="redis://redis:6379/0")
    redis_enabled: bool = Field(default=True)

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    agent_max_steps: int = Field(default=12, ge=1, le=50)
    agent_max_tool_calls: int = Field(default=8, ge=1, le=50)
    agent_max_input_chars: int = Field(default=8000, ge=100, le=32000)
    agent_max_output_chars: int = Field(default=12000, ge=100, le=64000)
    agent_max_tool_results: int = Field(default=20, ge=1, le=100)
    agent_max_message_chars: int = Field(default=2000, ge=100, le=16000)
    tool_timeout_seconds: float = Field(default=10.0, ge=0.1, le=120.0)
    tool_max_retries: int = Field(default=2, ge=0, le=5)

    @field_validator("database_url", mode="before")
    @classmethod
    def require_database_url(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("DATABASE_URL is required")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Unsupported LOG_LEVEL: {value!r}")
        return level

    def safe_summary(self) -> dict[str, object]:
        return {
            "app_env": self.app_env,
            "app_name": self.app_name,
            "log_level": self.log_level,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "redis_url_configured": bool(self.redis_url),
            "database_url_configured": True,
            "cors_origins": self.cors_origins,
            "agent_max_steps": self.agent_max_steps,
            "agent_max_tool_calls": self.agent_max_tool_calls,
            "agent_max_input_chars": self.agent_max_input_chars,
            "agent_max_output_chars": self.agent_max_output_chars,
            "agent_max_tool_results": self.agent_max_tool_results,
            "agent_max_message_chars": self.agent_max_message_chars,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
