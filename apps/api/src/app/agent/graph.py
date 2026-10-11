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
    if state.terminal_status:
        return "final"
    if any(c.get("fresh") for c in state.pending_tool_calls):
        return "dispatch"
    if state.final_answer:
        return "final"
    return "plan"


def after_dispatch(state: GraphState) -> str:
    if state.terminal_status:
        return "final"
    return "handle"


def after_handle(state: GraphState) -> str:
    if state.terminal_status:
        return "final"
    if state.step_count >= state.max_steps:
        return "final"
    return "plan"


def build_graph(model, executor, registry):  # type: ignore[no-untyped-def]
    graph = StateGraph(GraphState)
    graph.add_node("normalize", normalize_request)
    graph.add_node("plan", planning_node(model, registry))
    graph.add_node("dispatch", tool_dispatch_node(executor, registry))
    graph.add_node("handle", result_handling_node())
    graph.add_node("final", final_response_node())
    graph.set_entry_point("normalize")
    graph.add_edge("normalize", "plan")
    graph.add_conditional_edges(
        "plan",
        should_continue,
        {"dispatch": "dispatch", "final": "final", "plan": "plan"},
    )
    graph.add_conditional_edges("dispatch", after_dispatch, {"handle": "handle", "final": "final"})
    graph.add_conditional_edges("handle", after_handle, {"plan": "plan", "final": "final"})
    graph.add_edge("final", END)
    return graph.compile()


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
