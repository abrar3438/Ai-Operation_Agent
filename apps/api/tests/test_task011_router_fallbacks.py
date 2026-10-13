from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from app.agent.graph import build_graph  # noqa: E402
from app.agent.state import initial_state  # noqa: E402
from app.models.adapter import ModelResponse, ToolCall  # noqa: E402
from app.models.fake_adapter import FakeModelAdapter  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402
from app.tools.registry import (  # noqa: E402
    CalculateArgs,
    GetCustomerArgs,
    GetOrderArgs,
    SearchDocumentsArgs,
    ToolDefinition,
    ToolRegistry,
)
from tests.conftest import make_seeded_sqlite_session_factory  # noqa: E402


@pytest.fixture
def router_setup():
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_customer",
            description="Get customer by ID",
            input_schema=GetCustomerArgs,
        ),
        executor.execute_get_customer,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="get_order",
            description="Get order by ID",
            input_schema=GetOrderArgs,
        ),
        executor.execute_get_order,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="search_documents",
            description="Search internal docs",
            input_schema=SearchDocumentsArgs,
        ),
        executor.execute_search_documents,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="calculate",
            description="Perform calculation",
            input_schema=CalculateArgs,
        ),
        executor.execute_calculate,  # type: ignore[arg-type]
    )
    return registry, executor


def test_router_blocks_unknown_tool(router_setup) -> None:
    registry, executor = router_setup
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="t1",
                        type="function",
                        function={"name": "drop_database", "arguments": "{}"},
                    )
                ],
            ),
            ModelResponse(content="Handled unknown tool safely."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = initial_state(user_request="Drop the production database")
    result = asyncio.run(graph.ainvoke(state.model_dump()))

    tool_results = result.get("tool_results", [])
    assert any(r.get("error_category") == "validation_error" for r in tool_results)


def test_router_handles_missing_input_with_clarification(router_setup) -> None:
    registry, executor = router_setup
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content="Could you please provide the customer ID you would like to look up?"
            ),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = initial_state(user_request="Lookup customer info")
    result = asyncio.run(graph.ainvoke(state.model_dump()))

    assert result.get("terminal_status") == "succeeded"
    assert "provide the customer ID" in result.get("final_answer", "")


def test_router_never_converts_tool_failure_to_success(router_setup) -> None:
    registry, executor = router_setup
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="t2",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-9999"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="The customer was successfully retrieved."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = initial_state(user_request="Get customer CUST-9999")
    result = asyncio.run(graph.ainvoke(state.model_dump()))

    tool_results = result.get("tool_results", [])
    assert any(r.get("status") == "error" for r in tool_results)
    assert result.get("terminal_status") == "failed"
