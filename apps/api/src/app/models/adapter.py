from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator


class ModelConfig(BaseModel):
    provider: str = Field(default="openai_compatible")
    base_url: str | None = Field(default=None)
    api_key: SecretStr | None = Field(default=None)
    model: str = Field(default="gpt oss 120b")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=2, ge=0, le=10)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    @field_validator("base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        return v.rstrip("/")

    @classmethod
    def from_env(cls) -> ModelConfig:
        endpoint = os.getenv("CRAFTX_ENDPOINT")
        base_url = os.getenv("LLM_BASE_URL") or (
            endpoint.rsplit("/chat/completions", 1)[0] if endpoint else None
        )
        return cls(
            provider=os.getenv("LLM_PROVIDER", "openai_compatible"),
            base_url=base_url,
            api_key=SecretStr(os.getenv("LLM_API_KEY", "")) if os.getenv("LLM_API_KEY") else None,
            model=os.getenv("LLM_MODEL", os.getenv("CRAFTX_MODEL", "gpt oss 120b")),
            timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        )  # type: ignore[return]

    def safe_summary(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "temperature": self.temperature,
            "api_key_configured": self.api_key is not None,
        }


class ModelMessage(BaseModel):
    role: str = Field(pattern=r"^(system|user|assistant|tool)$")
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: dict[str, Any]


class ModelResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: dict[str, int] | None = None
    finish_reason: str | None = None


class ModelAdapter(ABC):
    @abstractmethod
    async def chat(
        self, messages: list[ModelMessage], tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        pass

    @abstractmethod
    def validate_config(self) -> None:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass


class ModelAdapterError(Exception):
    def __init__(self, message: str, category: str = "model_error", retryable: bool = False):
        super().__init__(message)
        self.category = category
        self.retryable = retryable
