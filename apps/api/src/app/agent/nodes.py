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
    # No chain-of-thought is stored: only the bounded, actionable request text.
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
    def _node(state: GraphState) -> dict[str, Any]:  # type: ignore[return]
        # TASK-007: pending_tool_calls is a short-lived control buffer. Fresh
        # entries from the immediately-preceding planning step execute; the
        # write below marks every dispatched call consumed in place, so the
        # append-only history can never re-dispatch it.
        fresh = [c for c in state.pending_tool_calls if c.get("fresh")]
        if not fresh:
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
        for call in fresh:
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
            elif name == "create_ticket":
                tr = executor.execute_create_ticket(
                    title=raw_args["title"],
                    priority=raw_args["priority"],
                    customer_id=raw_args["customer_id"],
                    description=raw_args.get("description", ""),
                    idempotency_key=raw_args["idempotency_key"],
                    requesting_run_id=raw_args.get("requesting_run_id"),
                )
            elif name == "send_report":
                tr = executor.execute_send_report(
                    title=raw_args["title"],
                    destination=raw_args.get("destination", "mock"),
                    payload_json=raw_args.get("payload_json", "{}"),
                    idempotency_key=raw_args["idempotency_key"],
                    requesting_run_id=raw_args.get("requesting_run_id"),
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
            # Structured observations only: name, status, typed result/error.
            sanitized = None
            if tr.result is not None:
                from app.agent.state import sanitize_result_for_state

                sanitized = sanitize_result_for_state(dict(tr.result))
            results.append(
                {
                    "tool_name": tr.tool_name,
                    "status": tr.status.value,
                    "result": sanitized,
                    "error": tr.error,
                    "error_category": tr.error_category.value if tr.error_category else None,
                    "duration_ms": elapsed,
                    "call_id": call.get("id"),
                }
            )
        # Executed entries are consumed in place (fresh to False): only
        # in-place marking prevents a second dispatch. Resume audits
        # `tool_results`, not this buffer. Kept OUTSIDE the per-call loop
        # so validation-only paths (continue) still consume the buffer.
        executed_ids = {call.get("id") for call in fresh}
        consumed = [
            {**call, "fresh": False} if call.get("id") in executed_ids else call
            for call in state.pending_tool_calls
        ]
        # Loop ended: finalize the consumed update for every path that reached
        # dispatch with fresh calls.
        update: dict[str, Any] = {
            "tool_results": results,
            "pending_tool_calls": consumed,
            "tool_calls_count": state.tool_calls_count + len(results),
            "step_count": state.step_count + 1,
        }
        if any(r.get("status") == "waiting_approval" for r in results):
            update["terminal_status"] = "waiting_approval"
            update["pending_approval_id"] = next(
                r.get("result", {}).get("proposal_id")
                for r in reversed(results)
                if r.get("status") == "waiting_approval"
            )
        return update

    return _node


def result_handling_node() -> Any:
    def _node(state: GraphState) -> dict[str, Any]:
        if not state.tool_results:
            return {}
        last = state.tool_results[-1]
        # Short-term context only: compact assistant note, not raw payloads.
        # Proposals are summarized by id/status — never by full payload.
        if last.get("status") == "waiting_approval":
            from app.agent.state import _truncate_text  # noqa: SLF001

            proposal = (last.get("result") or {}).get("proposal_id", "?")
            summary = _truncate_text(f"pending proposal {proposal} ({last['tool_name']})", 500)
            return {"messages": [{"role": "assistant", "content": f"Tool waiting: {summary}"}]}
        if last.get("status") == "ok" and last.get("result"):
            from app.agent.state import _truncate_text  # noqa: SLF001

            summary = _truncate_text(str(last["result"]), 500)
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
        # INVARIANT (TASK-006): an action proposal pauses the run. A final answer
        # must never claim the ticket/report was executed; it reports the pending
        # proposal and its identifiers.
        proposals = [r for r in state.tool_results if r.get("status") == "waiting_approval"]
        if proposals:
            pending = proposals[-1]
            return {
                "final_answer": (
                    f"Action proposal {pending.get('tool_name')} is pending approval "
                    f"(proposal: {pending.get('result', {}).get('proposal_id')}). "
                    "No ticket or report was created or sent."
                ),
                "pending_approval_id": pending.get("result", {}).get("proposal_id"),
                "terminal_status": "waiting_approval",
            }
        if state.tool_results and any(r.get("status") == "ok" for r in state.tool_results):
            ok = [r for r in state.tool_results if r.get("status") == "ok"]
            if sources:
                joined = ", ".join(sources)
                answer = f"Done. Results: {ok[-1]['result']} | Sources: {joined}"
            # Distinguish "no documents matched" from a successful doc search
            elif any(
                r.get("tool_name") == "search_documents"
                and r.get("status") == "ok"
                and (r.get("result") or {}).get("count") == 0
                for r in state.tool_results
            ):
                answer = (
                    "No relevant documents found in the corpus for this query. "
                    "No source identifiers are cited because none matched."
                )
            else:
                answer = f"Done. Results: {ok[-1]['result']}"
            # Output-size bound: truncate only with an explicit marker.
            from app.agent.state import MAX_FINAL_ANSWER_CHARS, _truncate_text  # noqa: SLF001

            return {
                "final_answer": _truncate_text(answer, MAX_FINAL_ANSWER_CHARS),
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
