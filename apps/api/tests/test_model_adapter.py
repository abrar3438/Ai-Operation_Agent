from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.adapter import ModelAdapterError, ModelConfig
from app.models.contracts import AgentRequest, ErrorCategory, RunStatus, ToolCallRequest


def test_model_config_safe_summary_excludes_api_key() -> None:
    config = ModelConfig(
        provider="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="sk-secret-key",
        model="gpt-4o-mini",
        timeout_seconds=30,
        max_retries=2,
        temperature=0.0,
    )
    summary = config.safe_summary()
    assert "sk-secret-key" not in str(summary)
    assert summary["api_key_configured"] is True


def test_model_config_from_env_uses_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    config = ModelConfig.from_env()
    assert config.provider == "openai_compatible"
    assert config.api_key is None
    assert config.base_url is None


def test_model_config_normalizes_base_url() -> None:
    config = ModelConfig(base_url="https://api.example.com/v1/")
    assert config.base_url == "https://api.example.com/v1"


def test_model_config_rejects_invalid_timeout() -> None:
    with pytest.raises(ValidationError):
        ModelConfig(timeout_seconds=0)


def test_model_adapter_error_categories() -> None:
    err = ModelAdapterError("test", category="config_error", retryable=False)
    assert err.category == "config_error"
    assert err.retryable is False


def test_agent_request_rejects_empty_user_request() -> None:
    with pytest.raises(ValidationError):
        AgentRequest(user_request="")


def test_agent_request_rejects_oversized_user_request() -> None:
    with pytest.raises(ValidationError):
        AgentRequest(user_request="x" * 8001)


def test_tool_call_request_rejects_unknown_tool() -> None:
    with pytest.raises(ValidationError):
        ToolCallRequest(tool_name="run_shell", arguments={}, idempotency_key="test-key-12345")


def test_tool_call_request_rejects_short_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        ToolCallRequest(tool_name="get_customer", arguments={}, idempotency_key="short")


def test_error_category_enum_values() -> None:
    assert ErrorCategory.VALIDATION_ERROR == "validation_error"
    assert ErrorCategory.NOT_FOUND == "not_found"
    assert ErrorCategory.TIMEOUT == "timeout"


def test_run_status_enum_values() -> None:
    assert RunStatus.QUEUED == "queued"
    assert RunStatus.SUCCEEDED == "succeeded"
    assert RunStatus.FAILED == "failed"
