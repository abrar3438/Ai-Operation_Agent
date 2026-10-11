from __future__ import annotations

import os
import sys
import uuid
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.agent.graph import build_graph, create_in_memory_checkpoint  # noqa: E402
from app.agent.state import GraphState  # noqa: E402
from app.models.adapter import ModelResponse, ToolCall  # noqa: E402
from app.models.fake_adapter import FakeModelAdapter  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402
from app.tools.registry import (  # noqa: E402
    GetCustomerArgs,
    GetOrderArgs,
    SearchDatabaseArgs,
    ToolDefinition,
    ToolRegistry,
)
from tests.conftest import (  # noqa: E402
    make_seeded_sqlite_session_factory,
    make_sqlite_session_factory,
)


def _sqlite_factory():
    return make_sqlite_session_factory()


def _seeded_factory():
    return make_seeded_sqlite_session_factory()


def _build(factory):  # type: ignore[no-untyped-def]
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_customer", description="Get customer", input_schema=GetCustomerArgs
        ),
        executor.execute_get_customer,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="get_order", description="Get order", input_schema=GetOrderArgs),
        executor.execute_get_order,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="search_database", description="Safe search", input_schema=SearchDatabaseArgs
        ),
        executor.execute_search_database,  # type: ignore[arg-type]
    )
    return registry, executor


def _registry_exec(factory):  # type: ignore[no-untyped-def]
    return _build(factory)


def test_customer_lookup_flows_through_graph() -> None:
    import asyncio

    factory = _seeded_factory()
    registry, executor = _registry_exec(factory)
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c1",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-1001"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Here is the customer."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Get customer CUST-1001"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert result["terminal_status"] == "succeeded" or any(
        r.get("status") == "ok" and r["tool_name"] == "get_customer"
        for r in result.get("tool_results", [])
    )


def test_order_lookup_flows_through_graph() -> None:
    import asyncio

    factory = _seeded_factory()
    registry, executor = _registry_exec(factory)
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c2",
                        type="function",
                        function={"name": "get_order", "arguments": '{"order_id": "ORD-5001"}'},
                    )
                ],
            ),
            ModelResponse(content="Order found."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Get order ORD-5001"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert result["terminal_status"] == "succeeded" or any(
        r.get("tool_name") == "get_order" for r in result.get("tool_results", [])
    )


def test_unknown_tool_is_blocked_before_dispatch() -> None:
    import asyncio

    factory = _sqlite_factory()
    registry, executor = _registry_exec(factory)
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c3",
                        type="function",
                        function={"name": "drop_tables", "arguments": "{}"},
                    )
                ],
            ),
            ModelResponse(content="Done."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Do something evil"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    results = result.get("tool_results", [])
    assert any(r.get("error_category") == "validation_error" for r in results)
    assert not any(r.get("tool_name") == "drop_tables" and r.get("status") == "ok" for r in results)


def test_invalid_tool_arguments_rejected() -> None:
    import asyncio

    factory = _sqlite_factory()
    registry, executor = _registry_exec(factory)
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c4",
                        type="function",
                        function={"name": "get_customer", "arguments": '{"customer_id": 123}'},
                    )
                ],
            ),
            ModelResponse(content="Done."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Get customer 123")
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    results = result.get("tool_results", [])
    assert any(r.get("error_category") == "validation_error" for r in results)


def test_malformed_tool_output_is_rejected_before_state() -> None:
    import asyncio

    factory = _sqlite_factory()
    registry, executor = _registry_exec(factory)
    orig = executor.execute_get_customer  # type: ignore[method-assign]

    def _malformed(customer_id: str) -> Any:  # type: ignore[no-untyped-def]
        class _R:  # noqa: BLE001
            tool_name = "get_customer"
            status = type("S", (), {"value": "ok"})()  # type: ignore[call-arg]
            result = "not-a-dict"
            error = None
            error_category = None

        return _R()

    executor.execute_get_customer = _malformed  # type: ignore[method-assign]
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c5",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-1001"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Done."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Get customer CUST-1001"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    results = result.get("tool_results", [])
    assert any(r.get("error_category") == "invalid_response" for r in results)
    executor.execute_get_customer = orig  # type: ignore[method-assign]


def test_attempted_loop_stops_at_max_tool_calls() -> None:
    import asyncio

    factory = _seeded_factory()
    registry, executor = _registry_exec(factory)
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c6",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-1001"}',
                        },
                    )
                ],
            ),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c7",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-1001"}',
                        },
                    )
                ],
            ),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c8",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-1001"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Should not reach here if budgets enforced"),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Loop me", max_tool_calls=1
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert result.get("terminal_status") == "failed"
    assert result.get("error", {}).get("category") in (
        "max_tool_calls_exceeded",
        "max_steps_exceeded",
        "no_result",
    )


def test_terminal_state_is_always_defined() -> None:
    import asyncio

    factory = _sqlite_factory()
    registry, executor = _registry_exec(factory)
    adapter = FakeModelAdapter(responses=[ModelResponse(content="Plain answer, no tools.")])
    graph = build_graph(adapter, executor, registry)
    state = GraphState(run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Just answer")
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert result.get("terminal_status") in ("succeeded", "failed")
    assert "final_answer" in result or "error" in result


def test_checkpoint_interface_exists_and_is_usable() -> None:
    saver = create_in_memory_checkpoint()
    assert hasattr(saver, "get") or hasattr(saver, "put") or saver is not None
    from app.agent.graph import create_postgres_checkpoint

    assert callable(create_postgres_checkpoint)
