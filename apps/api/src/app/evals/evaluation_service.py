from __future__ import annotations

import json
import os
import statistics
import time
from datetime import UTC, datetime
from typing import Any

from app.evals.data_v1 import SCENARIOS
from app.evals.runner import ScenarioRunner
from app.evals.schemas import Scenario
from app.models.adapter import ModelAdapter
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


class EvaluationService:
    def __init__(
        self,
        model_adapter: ModelAdapter,
        executor: ToolExecutor,
        registry: ToolRegistry,
        dataset_version: str = "v1",
    ) -> None:
        self.runner = ScenarioRunner(model_adapter, executor, registry)
        self.dataset_version = dataset_version

    async def run_evaluation(self, scenarios: list[Scenario] | None = None) -> dict[str, Any]:
        target_scenarios = scenarios if scenarios is not None else SCENARIOS
        start_time = datetime.now(UTC)

        results: list[dict[str, Any]] = []
        latencies_ms: list[float] = []

        for scenario in target_scenarios:
            t0 = time.monotonic()
            outcome = await self.runner.run_scenario(scenario)
            t1 = time.monotonic()
            duration_ms = (t1 - t0) * 1000.0
            latencies_ms.append(duration_ms)

            outcome["latency_ms"] = duration_ms
            results.append(outcome)

        # Calculate metrics
        total = len(target_scenarios)
        successful = sum(1 for r in results if r["success"])
        safety_failures = sum(
            1
            for r in results
            if r["error"] in {"validation_error", "authorization_error"} and not r["success"]
        )
        error_count = sum(1 for r in results if r["status"] == "failed")

        latencies_sorted = sorted(latencies_ms)
        median_lat = statistics.median(latencies_sorted) if latencies_sorted else 0.0
        p95_idx = int(0.95 * len(latencies_sorted))
        p95_lat = (
            latencies_sorted[min(p95_idx, len(latencies_sorted) - 1)] if latencies_sorted else 0.0
        )

        adapter_obj = self.runner.model_adapter
        provider_name = getattr(
            adapter_obj,
            "get_provider_name",
            lambda: "fake",
        )()

        metrics = {
            "dataset_version": self.dataset_version,
            "timestamp": start_time.isoformat(),
            "model_label": provider_name,
            "total_cases": total,
            "passed_cases": successful,
            "task_completion_rate": (successful / total) * 100 if total > 0 else 0.0,
            "error_rate": (error_count / total) * 100 if total > 0 else 0.0,
            "safety_policy_violations": safety_failures,
            "latency_median_ms": median_lat,
            "latency_p95_ms": p95_lat,
        }

        report = {
            "metrics": metrics,
            "results": results,
            "known_limitations": [
                "Evaluations run with deterministic fake model adapters "
                "and synthetic in-memory data.",
                "Real LLM latency and provider error rates vary depending on "
                "the active model provider endpoint.",
            ],
        }

        self._save_report_artifacts(report)
        return report

    def _save_report_artifacts(self, report: dict[str, Any]) -> None:
        reports_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "evals",
                "reports",
            )
        )
        os.makedirs(reports_dir, exist_ok=True)

        timestamp_slug = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(reports_dir, f"eval_report_{timestamp_slug}.json")
        summary_path = os.path.join(reports_dir, f"eval_report_{timestamp_slug}.md")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        m = report["metrics"]
        limitations = "\n".join(f"- {lim}" for lim in report["known_limitations"])
        summary_content = f"""# Evaluation Report — Dataset {m["dataset_version"]}

- **Timestamp:** {m["timestamp"]}
- **Model / Provider:** {m["model_label"]}
- **Total Cases:** {m["total_cases"]}
- **Passed Cases:** {m["passed_cases"]}
- **Task Completion Rate:** {m["task_completion_rate"]:.1f}%
- **Error / Fallback Rate:** {m["error_rate"]:.1f}%
- **Safety Policy Violations:** {m["safety_policy_violations"]}
- **Latency Median:** {m["latency_median_ms"]:.2f} ms
- **Latency P95:** {m["latency_p95_ms"]:.2f} ms

## Known Limitations
{limitations}
"""
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_content)
