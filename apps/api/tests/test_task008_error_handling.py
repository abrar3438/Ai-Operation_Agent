from __future__ import annotations

import asyncio

import httpx
import pytest

from app.models.adapter import ModelAdapterError, ModelConfig
from app.models.contracts import ErrorCategory, ToolCallStatus
from app.models.openai_adapter import OpenAICompatibleAdapter
from app.tools.executor import ToolExecutor
from tests.conftest import make_sqlite_session_factory


def test_model_adapter_transient_retry_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _test():
        config = ModelConfig(
            provider="openai_compatible",
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="gpt oss 120b",
            max_retries=2,
            timeout_seconds=5,
        )
        adapter = OpenAICompatibleAdapter(config)

        calls = 0

        async def mock_post(self, url, **kwargs):
            nonlocal calls
            calls += 1
            if calls < 2:
                resp = httpx.Response(502, json={"error": "bad gateway"})
            else:
                resp = httpx.Response(
                    200,
                    json={
                        "choices": [
                            {"message": {"content": "success after retry"}, "finish_reason": "stop"}
                        ]
                    },
                )
            resp.request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        from app.models.adapter import ModelMessage

        res = await adapter.chat([ModelMessage(role="user", content="hello")])
        assert res.content == "success after retry"
        assert calls == 2

    asyncio.run(_test())


def test_model_adapter_permanent_error_no_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _test():
        config = ModelConfig(
            provider="openai_compatible",
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="gpt oss 120b",
            max_retries=2,
            timeout_seconds=5,
        )
        adapter = OpenAICompatibleAdapter(config)

        calls = 0

        async def mock_post(self, url, **kwargs):
            nonlocal calls
            calls += 1
            resp = httpx.Response(400, json={"error": "bad request"})
            resp.request = httpx.Request("POST", url)
            return resp

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        from app.models.adapter import ModelMessage

        with pytest.raises(ModelAdapterError) as excinfo:
            await adapter.chat([ModelMessage(role="user", content="hello")])

        assert excinfo.value.retryable is False
        assert excinfo.value.category == "validation_error"
        assert calls == 1

    asyncio.run(_test())


def test_tool_executor_validation_and_not_found() -> None:
    factory = make_sqlite_session_factory()
    executor = ToolExecutor(factory)

    # Not found case
    res = executor.execute_get_customer("CUST-9999")
    assert res.status == ToolCallStatus.ERROR
    assert res.error_category == ErrorCategory.NOT_FOUND
