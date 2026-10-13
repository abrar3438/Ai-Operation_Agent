from __future__ import annotations

import uuid
from typing import Any

from app.agent.graph import build_graph
from app.agent.state import initial_state
from app.evals.schemas import Scenario
from app.models.adapter import ModelAdapter
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


class ScenarioRunner:
    def __init__(self, model_adapter: ModelAdapter, executor: ToolExecutor, registry: ToolRegistry):
        self.model_adapter = model_adapter
        self.executor = executor
        self.registry = registry

    async def run_scenario(self, scenario: Scenario) -> dict[str, Any]:
        graph = build_graph(self.model_adapter, self.executor, self.registry)
        state = initial_state(
            user_request=scenario.user_request,
            run_id=uuid.uuid4(),
            thread_id=uuid.uuid4(),
        )
        result = await graph.ainvoke(state.model_dump())

        # Extract metadata for evaluation
        tool_results = result.get("tool_results", [])
        used_tools = [r.get("tool_name") for r in tool_results]

        return {
            "scenario_id": scenario.id,
            "status": result.get("terminal_status"),
            "used_tools": used_tools,
            "answer": result.get("final_answer"),
            "error": result.get("error", {}).get("category") if result.get("error") else None,
            "success": self._check_success(scenario, result),
        }

    def _check_success(self, scenario: Scenario, result: dict[str, Any]) -> bool:
        # Simplified success check
        if scenario.expected_terminal_status != result.get("terminal_status"):
            return False
        if scenario.expected_error_category and scenario.expected_error_category != result.get(
            "error", {}
        ).get("category"):
            return False

        answer = result.get("final_answer") or ""
        for keyword in scenario.expected_answer_contains:
            if keyword not in answer:
                return False

        return True
