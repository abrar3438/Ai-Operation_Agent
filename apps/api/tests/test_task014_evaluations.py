from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from app.evals.evaluation_service import EvaluationService  # noqa: E402
from app.models.adapter import ModelResponse, ToolCall  # noqa: E402
from app.models.fake_adapter import FakeModelAdapter  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402
from app.tools.registry import (  # noqa: E402
    CalculateArgs,
    GetCustomerArgs,
    GetOrderArgs,
    SearchDatabaseArgs,
    SearchDocumentsArgs,
    ToolDefinition,
    ToolRegistry,
)
from tests.conftest import make_seeded_sqlite_session_factory  # noqa: E402


@pytest.fixture
def eval_setup():
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_customer",
            description="x",
            input_schema=GetCustomerArgs,
        ),
        executor.execute_get_customer,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="get_order", description="x", input_schema=GetOrderArgs),
        executor.execute_get_order,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="search_database",
            description="x",
            input_schema=SearchDatabaseArgs,
        ),
        executor.execute_search_database,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="search_documents",
            description="x",
            input_schema=SearchDocumentsArgs,
        ),
        executor.execute_search_documents,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="calculate", description="x", input_schema=CalculateArgs),
        executor.execute_calculate,  # type: ignore[arg-type]
    )
    return registry, executor


def test_evaluation_service_runs_and_reports(eval_setup) -> None:
    registry, executor = eval_setup

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
            ModelResponse(content="Acme Manufacturing is an active enterprise customer."),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c2",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-9999"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Customer not found."),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c3",
                        type="function",
                        function={
                            "name": "search_documents",
                            "arguments": '{"query": "pizza recipes"}',
                        },
                    )
                ],
            ),
            ModelResponse(content=("No relevant documents found in the corpus for this query.")),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c4",
                        type="function",
                        function={
                            "name": "calculate",
                            "arguments": '{"operation": "add", "operands": [100, 50]}',
                        },
                    )
                ],
            ),
            ModelResponse(content="150"),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c5",
                        type="function",
                        function={
                            "name": "search_database",
                            "arguments": '{"entity": "unknown_entity", "filters": {}}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Validation error."),
        ]
    )

    service = EvaluationService(adapter, executor, registry, dataset_version="v1")

    from app.evals.data_v1 import SCENARIOS

    report = asyncio.run(service.run_evaluation(SCENARIOS))

    assert "metrics" in report
    assert "results" in report
    assert report["metrics"]["total_cases"] == len(SCENARIOS)
    assert report["metrics"]["task_completion_rate"] > 0.0
    assert "safety_policy_violations" in report["metrics"]
    assert "latency_median_ms" in report["metrics"]
    assert "latency_p95_ms" in report["metrics"]
