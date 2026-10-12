from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    final_response_node,
    normalize_request,
    planning_node,
    result_handling_node,
    tool_dispatch_node,
)
from app.agent.state import GraphState


def should_continue(state: GraphState) -> str:
    if state.terminal_status == "waiting_approval":
        # The proposal is durable in approval_requests; route to a no-op so the
        # run never advances to execution in this task's scope.
        return "awaiting"
    if state.terminal_status:
        return "final"
    # Fresh-only gate: consumed history (fresh=False) must never re-dispatch.
    if any(c.get("fresh") for c in state.pending_tool_calls):
        return "dispatch"
    if state.final_answer:
        return "final"
    return "plan"


def awaiting_node(state: GraphState) -> dict:  # type: ignore[no-untyped-def]
    # Deliberate persisted pause: no tool dispatch, no execution, no retry.
    # TASK-010's approval decision resumes (or terminates) this run.
    return {}


def after_dispatch(state: GraphState) -> str:
    if state.terminal_status == "waiting_approval":
        return "awaiting"
    if state.terminal_status:
        return "final"
    return "handle"


def after_handle(state: GraphState) -> str:
    if state.terminal_status == "waiting_approval":
        return "awaiting"
    if state.terminal_status:
        return "final"
    if state.step_count >= state.max_steps:
        return "final"
    return "plan"


def build_graph(model, executor, registry, checkpointer=None):  # type: ignore[no-untyped-def]
    graph = StateGraph(GraphState)
    graph.add_node("normalize", normalize_request)
    graph.add_node("plan", planning_node(model, registry))
    graph.add_node("dispatch", tool_dispatch_node(executor, registry))
    graph.add_node("handle", result_handling_node())
    graph.add_node("awaiting", awaiting_node)
    graph.add_node("final", final_response_node())
    graph.set_entry_point("normalize")
    graph.add_edge("normalize", "plan")
    graph.add_conditional_edges(
        "plan",
        should_continue,
        {"dispatch": "dispatch", "final": "final", "plan": "plan", "awaiting": "awaiting"},
    )
    graph.add_conditional_edges(
        "dispatch",
        after_dispatch,
        {"handle": "handle", "final": "final", "awaiting": "awaiting"},
    )
    graph.add_conditional_edges(
        "handle", after_handle, {"plan": "plan", "final": "final", "awaiting": "awaiting"}
    )
    graph.add_edge("awaiting", END)
    graph.add_edge("final", END)
    if checkpointer is None:
        return graph.compile()
    return graph.compile(checkpointer=checkpointer)


def run_config_for_thread(thread_id: str) -> dict[str, dict[str, str]]:
    """Runnable config carrying run identity across pause/resume."""
    return {"configurable": {"thread_id": str(thread_id)}}


def extract_persisted_identity(stored: dict) -> dict[str, str | None]:
    """Pull only resume identity out of stored checkpoint state."""
    values = stored.get("values", stored)
    return {
        "run_id": values.get("run_id"),
        "thread_id": values.get("thread_id"),
        "pending_approval_id": values.get("pending_approval_id"),
        "terminal_status": values.get("terminal_status"),
    }


def fail_closed_on_missing_approval_state(
    stored: dict | None,
) -> tuple[bool, str | None]:
    """Decide whether action execution may proceed after resume.

    Returns (allowed, reason). Missing or unreadable checkpoint state means
    the approval cannot be proven durable, so execution is forbidden.
    """
    if not stored or "values" not in stored:
        return False, "approval checkpoint state unavailable; failing closed"
    identity = extract_persisted_identity(stored)
    if identity.get("terminal_status") != "waiting_approval":
        return (
            False,
            f"run is not awaiting approval (status={identity.get('terminal_status')})",
        )
    if not identity.get("pending_approval_id"):
        return False, "no pending approval identity in checkpoint state"
    return True, None


def create_in_memory_checkpoint():
    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver()


def create_postgres_checkpoint(conn_string: str):  # type: ignore[no-untyped-def]
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg import Connection
    from psycopg.rows import dict_row

    conn = Connection.connect(conn_string, row_factory=dict_row, autocommit=True)
    saver = PostgresSaver(conn)  # type: ignore[arg-type]
    saver.setup()
    return saver
