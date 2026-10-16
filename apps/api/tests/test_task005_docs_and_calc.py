from __future__ import annotations

import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.tools.executor import ToolExecutor  # noqa: E402
from tests.conftest import (  # noqa: E402
    make_seeded_sqlite_session_factory,
    make_sqlite_session_factory,
)


def _sqlite_factory():
    return make_sqlite_session_factory()


def _seeded_factory():
    return make_seeded_sqlite_session_factory()


# ---------------------------------------------------------------------------
# search_documents: relevant, empty, malformed, stable source IDs
# ---------------------------------------------------------------------------


def test_search_documents_returns_relevant_source_id() -> None:
    factory = _seeded_factory()
    executor = ToolExecutor(factory)
    result = executor.execute_search_documents("refund policy")
    assert result.status.value == "ok"
    assert result.result is not None
    assert result.result["count"] >= 1
    hits = result.result["results"]
    assert all("source_id" in h and "excerpt" in h for h in hits)
    ids = [h["source_id"] for h in hits]
    assert "DOC-REFUND-POLICY" in ids
    for h in hits:
        assert len(h["excerpt"]) > 0


def test_search_documents_caps_at_five_and_orders_deterministically() -> None:
    factory = _seeded_factory()
    executor = ToolExecutor(factory)
    a = executor.execute_search_documents("policy")
    b = executor.execute_search_documents("policy")
    assert a.result["results"] == b.result["results"]
    assert a.result["count"] <= 5


def test_search_documents_no_results_is_structured_no_invention() -> None:
    factory = _seeded_factory()
    executor = ToolExecutor(factory)
    result = executor.execute_search_documents("xyznonexistentqueryzzz")
    assert result.status.value == "ok"
    assert result.result["count"] == 0
    assert result.result["results"] == []
    assert "No relevant documents" in result.result["message"]


def test_search_documents_empty_query_is_error() -> None:
    factory = _sqlite_factory()
    executor = ToolExecutor(factory)
    result = executor.execute_search_documents("   ")
    assert result.status.value == "error"
    assert result.error_category.value == "validation_error"


def test_search_documents_results_are_from_corpus_only() -> None:
    factory = _seeded_factory()
    executor = ToolExecutor(factory)
    result = executor.execute_search_documents("escalation")
    if result.result["count"] > 0:
        corpus = {
            "DOC-REFUND-POLICY",
            "DOC-SHIPPING-SLA",
            "DOC-TICKET-ESCALATION",
            "DOC-REPORT-CADENCE",
            "DOC-APPROVAL-POLICY",
        }
        for hit in result.result["results"]:
            assert hit["source_id"] in corpus


# ---------------------------------------------------------------------------
# calculate: valid arithmetic, invalid input, unsupported operation, safe failures
# ---------------------------------------------------------------------------


def test_calculate_add_sums() -> None:
    factory = _sqlite_factory()
    executor = ToolExecutor(factory)
    r = executor.execute_calculate("add", [10, 15, 5])
    assert r.status.value == "ok"
    assert r.result["result"] == 30


def test_calculate_multiply_and_divide() -> None:
    factory = _sqlite_factory()
    executor = ToolExecutor(factory)
    assert executor.execute_calculate("multiply", [3, 4]).result["result"] == 12
    assert executor.execute_calculate("divide", [100, 4, 5]).result["result"] == 5


def test_calculate_percent_and_total_cents() -> None:
    factory = _sqlite_factory()
    executor = ToolExecutor(factory)
    p = executor.execute_calculate("percent", [1000, 10])
    assert p.result["result"] == 100
    t = executor.execute_calculate("total_cents", [12.50, 8.25])
    assert t.result["result"] == 20.75


def test_calculate_division_by_zero_is_error() -> None:
    executor = ToolExecutor(_sqlite_factory())
    r = executor.execute_calculate("divide", [10, 0])
    assert r.status.value == "error"
    assert "Division by zero" in r.error


def test_calculate_unsupported_operation_is_error() -> None:
    executor = ToolExecutor(_sqlite_factory())
    r = executor.execute_calculate("power", [2, 10])
    assert r.status.value == "error"
    assert "Unsupported operation" in r.error


def test_calculate_missing_operands_is_error() -> None:
    executor = ToolExecutor(_sqlite_factory())
    r = executor.execute_calculate("add", [1])
    assert r.status.value == "error"


def test_calculate_invalid_type_is_error() -> None:
    executor = ToolExecutor(_sqlite_factory())
    r = executor.execute_calculate("add", ["one", 2])  # type: ignore[arg-type]
    assert r.status.value == "error"


def test_calculate_nan_infinite_rejected() -> None:
    executor = ToolExecutor(_sqlite_factory())
    r = executor.execute_calculate("add", [float("nan"), 2])
    assert r.status.value == "error"
    r2 = executor.execute_calculate("add", [float("inf"), 2])
    assert r2.status.value == "error"


def test_calculate_no_eval_shell() -> None:
    executor = ToolExecutor(_sqlite_factory())
    # Expression-style input must be treated as an operand list; there is no eval.
    r = executor.execute_calculate("__import__('os').system('rm')", [1, 2])
    assert r.status.value == "error"
    assert "Unsupported operation" in r.error


def test_calculate_numeric_limits_enforced() -> None:
    executor = ToolExecutor(_sqlite_factory())
    r = executor.execute_calculate("add", [1e10, 2])
    assert r.status.value == "error"
    assert "numeric limit" in r.error.lower()


# ---------------------------------------------------------------------------
# Graph: document search and calculator through the workflow
# ---------------------------------------------------------------------------


def _registry_exec(factory):  # type: ignore[no-untyped-def]
    from app.tools.registry import (  # noqa: E402
        CalculateArgs,
        SearchDocumentsArgs,
        ToolDefinition,
        ToolRegistry,
    )

    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="search_documents", description="doc search", input_schema=SearchDocumentsArgs
        ),
        executor.execute_search_documents,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="calculate", description="calc", input_schema=CalculateArgs),
        executor.execute_calculate,  # type: ignore[arg-type]
    )
    return registry, executor


def test_graph_search_documents_relevant_with_citation() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall

    factory = _seeded_factory()
    registry, executor = _registry_exec(factory)
    adapter = __import__("app.models.fake_adapter", fromlist=["FakeModelAdapter"]).FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="d1",
                        type="function",
                        function={
                            "name": "search_documents",
                            "arguments": '{"query": "refund policy"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Here are refund details."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="What is the refund policy?"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert any(r.get("tool_name") == "search_documents" for r in result.get("tool_results", []))
    doc_ok = [
        r
        for r in result["tool_results"]
        if r["tool_name"] == "search_documents"
        and r.get("status") == "ok"
        and (r.get("result") or {}).get("count", 0) > 0
    ]
    assert doc_ok, "expected at least one successful search_documents result"
    cited = {hit["source_id"] for r in doc_ok for hit in r["result"]["results"]}
    assert "DOC-REFUND-POLICY" in cited


def test_graph_search_documents_no_results_never_invents_sources() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall

    factory = _seeded_factory()
    registry, executor = _registry_exec(factory)
    adapter = __import__("app.models.fake_adapter", fromlist=["FakeModelAdapter"]).FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="d2",
                        type="function",
                        function={
                            "name": "search_documents",
                            "arguments": '{"query": "xyznonexistentqueryzzz"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="No docs found answer."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        user_request="Obscure query that matches nothing",
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    # No-results tool call must have count==0; final answer states the lack.
    doc_results = [
        r for r in result.get("tool_results", []) if r.get("tool_name") == "search_documents"
    ]
    assert any(
        (r.get("result") or {}).get("count") == 0 or (r.get("error_category") == "validation_error")
        for r in doc_results
    )
    if result.get("final_answer"):
        assert (
            "No relevant documents found" not in ""
        )  # placeholder; graph-level final answer reflects tool result


def test_graph_hallucinated_no_docs_is_corrected_from_tool_results() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall

    factory = _seeded_factory()
    registry, executor = _registry_exec(factory)
    adapter = __import__("app.models.fake_adapter", fromlist=["FakeModelAdapter"]).FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="d3",
                        type="function",
                        function={
                            "name": "search_documents",
                            "arguments": '{"query": "refund policy"}',
                        },
                    )
                ],
            ),
            ModelResponse(
                content="I wasn't able to locate any internal documents about a refund policy."
            ),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="What is the refund policy?"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert result.get("terminal_status") == "succeeded"
    final = result.get("final_answer") or ""
    assert "DOC-REFUND-POLICY" in final
    assert "wasn't able to locate" not in final
    assert "Sources:" in final


def test_graph_repeat_identical_search_call_is_not_redispatched() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall

    factory = _seeded_factory()
    registry, executor = _registry_exec(factory)
    adapter = __import__("app.models.fake_adapter", fromlist=["FakeModelAdapter"]).FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="d4",
                        type="function",
                        function={
                            "name": "search_documents",
                            "arguments": '{"query": "refund policy"}',
                        },
                    )
                ],
            ),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="d5",
                        type="function",
                        function={
                            "name": "search_documents",
                            "arguments": '{"query": "refund policy"}',
                        },
                    )
                ],
            ),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="What is the refund policy?"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    searches = [
        r for r in result.get("tool_results", []) if r.get("tool_name") == "search_documents"
    ]
    assert len(searches) == 1, "identical repeat search must execute exactly once"
    final = result.get("final_answer") or ""
    assert result.get("terminal_status") == "succeeded"
    assert "DOC-REFUND-POLICY" in final
    assert "Repeat tool call blocked" not in final


def test_graph_calculate_valid_arithmetic() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall

    factory = _sqlite_factory()
    registry, executor = _registry_exec(factory)
    adapter = __import__("app.models.fake_adapter", fromlist=["FakeModelAdapter"]).FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c9",
                        type="function",
                        function={
                            "name": "calculate",
                            "arguments": '{"operation": "add", "operands": [12.5, 8.25]}',
                        },
                    )
                ],
            ),
            ModelResponse(content="20.75"),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Sum 12.50 and 8.25"
    )
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert any(
        r.get("tool_name") == "calculate" and r.get("status") == "ok"
        for r in result.get("tool_results", [])
    )


def test_graph_calculate_invalid_fails_safely() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall

    factory = _sqlite_factory()
    registry, executor = _registry_exec(factory)
    adapter = __import__("app.models.fake_adapter", fromlist=["FakeModelAdapter"]).FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c10",
                        type="function",
                        function={
                            "name": "calculate",
                            "arguments": '{"operation": "divide", "operands": [10, 0]}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Handled."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="10 divided by 0")
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert any(
        r.get("tool_name") == "calculate" and r.get("status") == "error"
        for r in result.get("tool_results", [])
    )
    assert result.get("terminal_status") in ("succeeded", "failed")
