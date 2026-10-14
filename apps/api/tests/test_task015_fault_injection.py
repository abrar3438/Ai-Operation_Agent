from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import httpx
import pytest
from redis.exceptions import RedisError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.agent.graph import build_graph  # noqa: E402
from app.agent.state import initial_state  # noqa: E402
from app.cache.service import CacheService  # noqa: E402
from app.models.adapter import ModelAdapterError, ModelConfig  # noqa: E402
from app.models.openai_adapter import OpenAICompatibleAdapter  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402
from app.tools.registry import (  # noqa: E402
    GetCustomerArgs,
    ToolDefinition,
    ToolRegistry,
)
from tests.conftest import make_seeded_sqlite_session_factory  # noqa: E402


@pytest.mark.asyncio
async def test_fault_injection_model_retry_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    config = ModelConfig(
        provider="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        model="gpt oss 120b",
        max_retries=1,
        timeout_seconds=5,
    )
    adapter = OpenAICompatibleAdapter(config)

    async def mock_post(self: Any, url: str, **kwargs: Any) -> httpx.Response:
        resp = httpx.Response(503, json={"error": "service unavailable"})
        resp.request = httpx.Request("POST", url)
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    from app.models.adapter import ModelMessage

    with pytest.raises(ModelAdapterError) as excinfo:
        await adapter.chat([ModelMessage(role="user", content="hello")])

    assert excinfo.value.retryable is True
    assert excinfo.value.category == "provider_error"


def test_fault_injection_graph_step_budget_limit() -> None:
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="get_customer", description="x", input_schema=GetCustomerArgs),
        executor.execute_get_customer,  # type: ignore[arg-type]
    )

    from app.models.fake_adapter import FakeModelAdapter, ModelResponse

    adapter = FakeModelAdapter(responses=[ModelResponse(content="loop answer")])
    graph = build_graph(adapter, executor, registry)

    state = initial_state(user_request="Infinite loop test", max_steps=1)
    state.step_count = 10  # Exceed max steps
    result = asyncio.run(graph.ainvoke(state.model_dump()))

    assert result.get("terminal_status") == "failed"
    assert result.get("error", {}).get("category") == "max_steps_exceeded"


def test_redis_outage_does_not_block_db_read() -> None:
    factory = make_seeded_sqlite_session_factory()

    class BrokenRedis:
        def get(self, *args: Any, **kwargs: Any) -> str | None:
            raise RedisError("Redis down")

        def setex(self, *args: Any, **kwargs: Any) -> bool:
            raise RedisError("Redis down")

        def ping(self) -> bool:
            raise RedisError("Redis down")

    cache = CacheService(redis_client=BrokenRedis())  # type: ignore[arg-type]
    executor = ToolExecutor(factory, cache_service=cache)

    res = executor.execute_get_customer("CUST-1001")
    assert res.status.value == "ok"
    assert res.result["customer_id"] == "CUST-1001"
