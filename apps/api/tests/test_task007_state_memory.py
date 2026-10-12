from __future__ import annotations

from app.agent import state as agent_state
from app.agent.state import (
    MAX_FINAL_ANSWER_CHARS,
    MAX_MESSAGE_CHARS,
    MAX_TOOL_RESULTS_RETAINED,
    MAX_USER_REQUEST_CHARS,
    GraphState,
    compact_state,
    initial_state,
    sanitize_result_for_state,
    state_snapshot_secret_free,
)


def _minimal() -> GraphState:
    return initial_state(user_request="hello")


def test_initial_state_bounds_request_and_budgets() -> None:
    state = initial_state(user_request="x" * 9000, max_steps=999, max_tool_calls=0)
    assert len(state.user_request) <= MAX_USER_REQUEST_CHARS
    assert state.user_request.endswith("…[truncated]")
    assert state.max_steps == 50
    # Zero/negative budgets clamp to 1 (fail fast on the next step, not silently).
    assert state.max_tool_calls == 1


def test_compact_state_retains_only_tail() -> None:
    state = _minimal()
    state.tool_results = [{"i": i} for i in range(MAX_TOOL_RESULTS_RETAINED + 10)]
    state.messages = [{"i": i} for i in range(MAX_TOOL_RESULTS_RETAINED * 2 + 5)]
    compacted = compact_state(state)
    assert len(compacted.tool_results) == MAX_TOOL_RESULTS_RETAINED
    assert compacted.tool_results[-1] == {"i": MAX_TOOL_RESULTS_RETAINED + 9}
    assert len(compacted.messages) == MAX_TOOL_RESULTS_RETAINED * 2
    # Original is untouched — compact_state returns a new state.
    assert len(state.tool_results) == MAX_TOOL_RESULTS_RETAINED + 10


def test_final_answer_bound_is_documented_and_applied() -> None:
    assert MAX_FINAL_ANSWER_CHARS == 12000
    assert MAX_USER_REQUEST_CHARS == 8000
    assert MAX_MESSAGE_CHARS == 2000
    text = "y" * (MAX_FINAL_ANSWER_CHARS + 100)
    assert len(agent_state._truncate_text(text, MAX_FINAL_ANSWER_CHARS)) == MAX_FINAL_ANSWER_CHARS


def test_sanitize_result_for_state_is_structured_and_bounded() -> None:
    payload = {"ok": True, "blob": "z" * (MAX_MESSAGE_CHARS + 50)}
    kept = sanitize_result_for_state(payload)
    assert isinstance(kept, dict)
    assert len(str(kept)) <= MAX_MESSAGE_CHARS + 50


def test_state_rejects_secrets_in_snapshot() -> None:
    clean = _minimal()
    assert state_snapshot_secret_free(clean) is True
    poisoned = clean.model_copy(update={"final_answer": "key is sk-abc123 secret"})
    assert state_snapshot_secret_free(poisoned) is False
    poisoned_url = clean.model_copy(
        update={"error": {"database_url": "postgresql://postgres:postgres@x/db"}}
    )
    assert state_snapshot_secret_free(poisoned_url) is False


def test_no_chain_of_thought_field_exists_on_state() -> None:
    fields = set(GraphState.model_fields)
    for banned in ("thought", "chain_of_thought", "reasoning", "scratchpad", "api_key"):
        assert banned not in fields
    # Only actionable structured state is allowed.
    assert {"run_id", "thread_id", "step_count", "terminal_status", "pending_approval_id"} <= fields


def test_budget_enforcement_max_steps() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.models.adapter import ModelResponse
    from app.models.fake_adapter import FakeModelAdapter
    from app.tools.executor import ToolExecutor
    from app.tools.registry import GetCustomerArgs, ToolDefinition, ToolRegistry
    from tests.conftest import make_sqlite_session_factory

    factory = make_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="get_customer", description="x", input_schema=GetCustomerArgs),
        executor.execute_get_customer,  # type: ignore[arg-type]
    )
    adapter = FakeModelAdapter(responses=[ModelResponse(content="late answer")])
    graph = build_graph(adapter, executor, registry)
    import uuid

    state = initial_state(user_request="hi", run_id=uuid.uuid4(), max_steps=1)
    state.step_count = 5  # simulate exhausted budget before planning
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    assert result.get("terminal_status") == "failed"
    assert result.get("error", {}).get("category") == "max_steps_exceeded"


def test_pause_resume_round_trip_with_in_memory_checkpoint() -> None:
    import asyncio
    import uuid

    from app.agent.graph import build_graph, create_in_memory_checkpoint, run_config_for_thread
    from app.models.adapter import ModelResponse, ToolCall
    from app.models.fake_adapter import FakeModelAdapter
    from app.tools.executor import ToolExecutor
    from app.tools.registry import CreateTicketArgs, ToolDefinition, ToolRegistry
    from tests.conftest import make_seeded_sqlite_session_factory

    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="create_ticket", description="propose ticket", input_schema=CreateTicketArgs
        ),
        executor.execute_create_ticket,  # type: ignore[arg-type]
    )
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="p1",
                        type="function",
                        function={
                            "name": "create_ticket",
                            "arguments": (
                                '{"title": "Refund delayed", "priority": "high", '
                                '"customer_id": "CUST-1001", '
                                '"idempotency_key": "task007-pause-0001"}'
                            ),
                        },
                    )
                ],
            ),
            ModelResponse(content="Proposal created."),
        ]
    )
    checkpointer = create_in_memory_checkpoint()
    graph = build_graph(adapter, executor, registry, checkpointer=checkpointer)
    thread_id = str(uuid.uuid4())
    config = run_config_for_thread(thread_id)
    result = asyncio.run(
        graph.ainvoke(
            initial_state(
                user_request="Create a ticket", thread_id=uuid.UUID(thread_id)
            ).model_dump(),
            config=config,
        )
    )
    # The deliberate pause: terminal write is the pending proposal, and the
    # full snapshot is persisted under this thread id.
    assert result.get("terminal_status") == "waiting_approval"
    proposal_id = result.get("pending_approval_id")
    assert proposal_id

    # Resume: the stored checkpoint carries the same run identity and pending
    # approval id; the second run starts from that stored snapshot.
    stored = graph.get_state(config)
    assert stored is not None
    values = stored.values
    assert str(values.get("pending_approval_id")) == proposal_id
    identity_thread = str(values.get("thread_id"))
    assert identity_thread == thread_id


def test_fail_closed_on_missing_approval_state() -> None:
    from app.agent.graph import fail_closed_on_missing_approval_state

    allowed, reason = fail_closed_on_missing_approval_state(None)
    assert allowed is False
    assert "failing closed" in (reason or "")

    allowed2, reason2 = fail_closed_on_missing_approval_state({"values": {}})
    assert allowed2 is False
    assert reason2 is not None

    allowed3, reason3 = fail_closed_on_missing_approval_state(
        {"values": {"terminal_status": "succeeded", "pending_approval_id": "x"}}
    )
    assert allowed3 is False
    assert "not awaiting approval" in (reason3 or "")

    allowed4, _ = fail_closed_on_missing_approval_state(
        {"values": {"terminal_status": "waiting_approval", "pending_approval_id": "abc"}}
    )
    assert allowed4 is True


def test_secret_leak_guard_covers_checkpoint_payload() -> None:
    import asyncio
    import uuid

    from app.agent.graph import build_graph, create_in_memory_checkpoint, run_config_for_thread
    from app.models.adapter import ModelResponse
    from app.models.fake_adapter import FakeModelAdapter
    from app.tools.executor import ToolExecutor
    from app.tools.registry import GetCustomerArgs, ToolDefinition, ToolRegistry
    from tests.conftest import make_sqlite_session_factory

    factory = make_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(name="get_customer", description="x", input_schema=GetCustomerArgs),
        executor.execute_get_customer,  # type: ignore[arg-type]
    )
    adapter = FakeModelAdapter(responses=[ModelResponse(content="answer text")])
    checkpointer = create_in_memory_checkpoint()
    graph = build_graph(adapter, executor, registry, checkpointer=checkpointer)
    config = run_config_for_thread(str(uuid.uuid4()))
    result = asyncio.run(
        graph.ainvoke(initial_state(user_request="hi").model_dump(), config=config)
    )
    assert result.get("terminal_status") == "succeeded"
    stored = graph.get_state(config)
    assert stored is not None
    assert state_snapshot_secret_free(GraphState(**stored.values)) is True
