from __future__ import annotations

import json
import operator
import uuid
from typing import Annotated, Any

from pydantic import BaseModel, Field

# TASK-007 memory boundaries. Transient reasoning/control state lives ONLY in
# GraphState and dies with the run unless it is copied into a durable record
# below. Durable truth lives ONLY in PostgreSQL tables (agent_runs,
# tool_events, approval_requests, evaluation runs/results). Nothing in this
# module stores hidden chain-of-thought, provider keys, or raw private payloads.

MAX_USER_REQUEST_CHARS = 8000
MAX_FINAL_ANSWER_CHARS = 12000
MAX_MESSAGE_CHARS = 2000
MAX_TOOL_RESULTS_RETAINED = 20


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    marker = "…[truncated]"
    return value[: limit - len(marker)] + marker


class GraphState(BaseModel):
    run_id: uuid.UUID
    thread_id: uuid.UUID
    user_request: str
    normalized_request: str | None = None
    messages: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)
    tool_results: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)
    # Control buffer only: planning appends fresh calls, dispatch consumes them
    # by rewriting fresh flags in place (see nodes.tool_dispatch_node), and
    # every reader uses the fresh-only convention. The field keeps the
    # append reducer supported by this LangGraph version.
    pending_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    pending_approval_id: str | None = None
    step_count: int = 0
    tool_calls_count: int = 0
    max_steps: int = 12
    max_tool_calls: int = 8
    terminal_status: str | None = None
    final_answer: str | None = None
    error: dict[str, Any] | None = None
    model_label: str = "unset"
    provider_label: str = "unset"


def initial_state(
    *,
    user_request: str,
    run_id: uuid.UUID | None = None,
    thread_id: uuid.UUID | None = None,
    max_steps: int = 12,
    max_tool_calls: int = 8,
    model_label: str = "unset",
    provider_label: str = "unset",
) -> GraphState:
    bounded = _truncate_text(user_request.strip(), MAX_USER_REQUEST_CHARS)
    return GraphState(
        run_id=run_id or uuid.uuid4(),
        thread_id=thread_id or uuid.uuid4(),
        user_request=bounded,
        max_steps=max(1, min(max_steps, 50)),
        max_tool_calls=max(1, min(max_tool_calls, 50)),
        model_label=model_label,
        provider_label=provider_label,
    )


def compact_state(state: GraphState) -> GraphState:
    """Enforce retained-context limits. Returns a NEW state; never mutates."""
    if len(state.tool_results) > MAX_TOOL_RESULTS_RETAINED:
        kept = state.tool_results[-MAX_TOOL_RESULTS_RETAINED:]
    else:
        kept = list(state.tool_results)
    if len(state.messages) > MAX_TOOL_RESULTS_RETAINED * 2:
        kept_messages = state.messages[-(MAX_TOOL_RESULTS_RETAINED * 2) :]
    else:
        kept_messages = list(state.messages)
    return state.model_copy(
        update={"tool_results": kept, "messages": kept_messages},
    )


def sanitize_result_for_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Bound one tool result before it enters state. Structured only."""
    blob = json.dumps(payload)
    if len(blob) <= MAX_MESSAGE_CHARS:
        return payload
    trimmed: dict[str, Any] = {}
    budget = MAX_MESSAGE_CHARS
    for key, value in payload.items():
        chunk = json.dumps({key: value})
        if len(chunk) > budget and trimmed:
            break
        if len(chunk) > budget:
            trimmed[key] = _truncate_text(str(value), budget - 20)
            break
        trimmed[key] = value
        budget -= len(chunk)
    trimmed["_truncated"] = True
    return trimmed


def state_snapshot_secret_free(state: GraphState) -> bool:
    """Fail-closed guard used by persistence: reject secrets in stored state."""
    blob = state.model_dump_json().lower()
    markers = (
        "api_key",
        "apikey",
        "authorization",
        "bearer ",
        "sk-",
        "passwd",
        "db_password",
        "database_url",
    )
    return not any(marker in blob for marker in markers)
