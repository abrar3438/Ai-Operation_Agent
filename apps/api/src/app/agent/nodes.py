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
    # `normalized_request` merge keeps the plain str value; the state reducer
    # replaces `pending_tool_calls` wholesale (see state.py) so a fresh model
    # call can never inherit a tool call from a previous step.
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
                    "fresh": True,
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
        # pending_tool_calls uses the default append reducer, so dispatch must
        # only act on calls placed by the immediately-preceding planning step
        # (marked fresh) and must consume them explicitly.
        pending = [c for c in state.pending_tool_calls if c.get("fresh")]
        if not pending:
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
        for call in pending:
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
            elif name == "search_documents":
                # Registry gives us a typed query; normalize string vs dict.
                q = raw_args.get("query", "")
                if not isinstance(q, str):
                    q = str(q)
                tr = executor.execute_search_documents(q)
            elif name == "calculate":
                tr = executor.execute_calculate(raw_args["operation"], raw_args.get("operands", []))
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
        # Mark consumed calls so a later serialization round-trip cannot dispatch
        # the same call twice. (`fresh: False` entries are ignored by dispatch.)
        consumed = [
            {**call, "fresh": False} if call.get("fresh") else call
            for call in state.pending_tool_calls
        ]
        return {
            "tool_results": results,
            "pending_tool_calls": consumed,
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
        # INVARIANT (TASK-005): never invent sources. If search_documents returned
        # zero hits, surface the no-answer state instead of hallucinating.
        doc_hits: list[dict[str, Any]] = []
        for r in state.tool_results:
            if r.get("tool_name") == "search_documents" and r.get("result"):
                doc_hits.extend(r["result"].get("results", []) or [])
        sources = [h["source_id"] for h in doc_hits]
        if state.tool_results and any(r.get("status") == "ok" for r in state.tool_results):
            ok = [r for r in state.tool_results if r.get("status") == "ok"]
            if sources:
                joined = ", ".join(sources)
                return {
                    "final_answer": f"Done. Results: {ok[-1]['result']} | Sources: {joined}",
                    "terminal_status": "succeeded",
                }
            # Distinguish "no documents matched" from a successful doc search
            search_ok_no_results = any(
                r.get("tool_name") == "search_documents"
                and r.get("status") == "ok"
                and (r.get("result") or {}).get("count") == 0
                for r in state.tool_results
            )
            if search_ok_no_results:
                return {
                    "final_answer": (
                        "No relevant documents found in the corpus for this query. "
                        "No source identifiers are cited because none matched."
                    ),
                    "terminal_status": "succeeded",
                }
            return {
                "final_answer": f"Done. Results: {ok[-1]['result']}",
                "terminal_status": "succeeded",
            }
        no_result_msg = "No successful tool result and no final answer"
        return {
            "terminal_status": "failed",
            "error": {
                "category": "no_result",
                "message": no_result_msg,
            },
        }

    return _node
