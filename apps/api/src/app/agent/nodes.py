from __future__ import annotations

import json
import time
from typing import Any

from app.agent.state import GraphState
from app.models.adapter import ModelAdapter, ModelMessage
from app.models.contracts import ToolCallStatus, ToolResult
from app.tools.executor import ToolExecutor


def normalize_request(state: GraphState) -> dict[str, Any]:
    raw = state.user_request
    normalized = raw.strip()
    if len(normalized) > 8000:
        normalized = normalized[:8000]
    return {"normalized_request": normalized, "step_count": 1}


def planning_node(model: ModelAdapter, registry: Any) -> Any:
    async def _node(state: GraphState) -> dict[str, Any]:
        if state.step_count >= state.max_steps:
            return {
                "terminal_status": "failed",
                "error": {
                    "category": "max_steps_exceeded",
                    "message": f"Max steps {state.max_steps} reached",
                },
            }
        messages = [
            ModelMessage(
                role="system",
                content=(
                    "You are a read-only operations assistant. Call one "
                    "allowlisted tool per turn or answer directly."
                ),
            ),
            ModelMessage(
                role="user",
                content=state.normalized_request or state.user_request,
            ),
        ]
        tools = registry.get_tools_for_model()
        try:
            response = await model.chat(messages, tools=tools)
        except Exception as e:  # noqa: BLE001
            return {
                "terminal_status": "failed",
                "error": {"category": "provider_error", "message": str(e)},
            }
        if response.tool_calls:
            calls = [
                {
                    "id": tc.id,
                    "name": tc.function.get("name"),
                    "arguments": tc.function.get("arguments", {}),
                }
                for tc in response.tool_calls
            ]
            return {"pending_tool_calls": calls}
        if response.content:
            return {"final_answer": response.content, "terminal_status": "succeeded"}
        return {
            "terminal_status": "failed",
            "error": {
                "category": "invalid_response",
                "message": "Model returned empty response",
            },
        }

    return _node


def tool_dispatch_node(executor: ToolExecutor, registry: Any) -> Any:
    def _node(state: GraphState) -> dict[str, Any]:
        if not state.pending_tool_calls:
            return {}
        if state.tool_calls_count >= state.max_tool_calls:
            return {
                "terminal_status": "failed",
                "error": {
                    "category": "max_tool_calls_exceeded",
                    "message": f"Max tool calls {state.max_tool_calls} reached",
                },
            }
        results: list[dict[str, Any]] = []
        for call in state.pending_tool_calls:
            name = call.get("name", "")
            raw_args = call.get("arguments", {})
            if not registry.is_allowed(name):
                results.append(
                    {
                        "tool_name": name,
                        "status": "error",
                        "error": f"Unknown tool: {name}",
                        "error_category": "validation_error",
                        "call_id": call.get("id"),
                    }
                )
                continue
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except json.JSONDecodeError:  # noqa: BLE001
                    results.append(
                        {
                            "tool_name": name,
                            "status": "error",
                            "error": f"Invalid JSON arguments for {name}",
                            "error_category": "validation_error",
                            "call_id": call.get("id"),
                        }
                    )
                    continue
            valid, err = registry.validate_call(name, raw_args)
            if not valid:
                results.append(
                    {
                        "tool_name": name,
                        "status": "error",
                        "error": err,
                        "error_category": "validation_error",
                        "call_id": call.get("id"),
                    }
                )
                continue
            start = time.monotonic()
            if name == "get_customer":
                tr: ToolResult = executor.execute_get_customer(raw_args["customer_id"])
            elif name == "get_order":
                tr = executor.execute_get_order(raw_args["order_id"])
            elif name == "search_database":
                tr = executor.execute_search_database(
                    raw_args["entity"], raw_args.get("filters", {})
                )
            else:
                tr = ToolResult(
                    tool_name=name,
                    status=ToolCallStatus.ERROR,
                    error=f"Unhandled tool: {name}",
                )
            if tr.result is not None and not isinstance(tr.result, dict):
                results.append(
                    {
                        "tool_name": name,
                        "status": "error",
                        "error": "Malformed tool output: result must be dict or null",
                        "error_category": "invalid_response",
                        "call_id": call.get("id"),
                    }
                )
                continue
            elapsed = int((time.monotonic() - start) * 1000)
            results.append(
                {
                    "tool_name": tr.tool_name,
                    "status": tr.status.value,
                    "result": tr.result,
                    "error": tr.error,
                    "error_category": tr.error_category.value if tr.error_category else None,
                    "duration_ms": elapsed,
                    "call_id": call.get("id"),
                }
            )
        return {
            "tool_results": results,
            "pending_tool_calls": [],
            "tool_calls_count": state.tool_calls_count + len(results),
            "step_count": state.step_count + 1,
        }

    return _node


def result_handling_node() -> Any:
    def _node(state: GraphState) -> dict[str, Any]:
        if not state.tool_results:
            return {}
        last = state.tool_results[-1]
        if last.get("status") == "ok" and last.get("result"):
            summary = str(last["result"])[:500]
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Tool {last['tool_name']} succeeded: {summary}",
                    }
                ]
            }
        if last.get("status") == "error":
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Tool {last['tool_name']} failed: {last['error']}",
                    }
                ]
            }
        return {}

    return _node


def final_response_node() -> Any:
    def _node(state: GraphState) -> dict[str, Any]:
        if state.terminal_status:
            return {}
        if state.tool_results and any(r.get("status") == "ok" for r in state.tool_results):
            ok = [r for r in state.tool_results if r.get("status") == "ok"]
            return {
                "final_answer": f"Done. Results: {ok[-1]['result']}",
                "terminal_status": "succeeded",
            }
        return {
            "terminal_status": "failed",
            "error": {
                "category": "no_result",
                "message": "No successful tool result and no final answer",
            },
        }

    return _node
