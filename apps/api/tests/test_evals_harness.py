import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from app.evals.data_v1 import SCENARIOS  # noqa: E402, F401
from app.evals.runner import ScenarioRunner  # noqa: E402
from app.evals.schemas import Scenario  # noqa: E402
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
def runner_context():
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="get_customer", description="x", input_schema=GetCustomerArgs),
        executor.execute_get_customer,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="get_order", description="x", input_schema=GetOrderArgs),
        executor.execute_get_order,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="search_database", description="x", input_schema=SearchDatabaseArgs),
        executor.execute_search_database,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="search_documents", description="x", input_schema=SearchDocumentsArgs),
        executor.execute_search_documents,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(name="calculate", description="x", input_schema=CalculateArgs),
        executor.execute_calculate,  # type: ignore[arg-type]
    )
    return registry, executor


@pytest.mark.asyncio
async def test_scenario_runner(runner_context):
    registry, executor = runner_context
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="1",
                        type="function",
                        function={
                            "name": "get_customer",
                            "arguments": '{"customer_id": "CUST-1001"}',
                        },
                    )
                ],
            ),
            ModelResponse(content="Found: Acme Manufacturing"),
        ]
    )

    runner = ScenarioRunner(adapter, executor, registry)

    from app.evals.data_v1 import SCENARIOS as _SCENARIOS

    scenario = next(s for s in _SCENARIOS if s.id == "normal-customer-lookup")

    result = await runner.run_scenario(scenario)
    assert result["success"] is True
    assert result["status"] == "succeeded"


@pytest.mark.asyncio
async def test_scenario_malformed_fixture(runner_context):
    bad_scenario = Scenario(
        id="bad",
        description="x",
        user_request="x",
        expected_terminal_status="nonexistent",
    )
    registry, executor = runner_context
    adapter = FakeModelAdapter()

    runner = ScenarioRunner(adapter, executor, registry)
    result = await runner.run_scenario(bad_scenario)
    assert result["success"] is False
