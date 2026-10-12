from __future__ import annotations

import os
import sys
import uuid
from typing import Any

from sqlalchemy import select

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.actions.executor import MockActionExecutor  # noqa: E402
from app.db import models  # noqa: E402
from app.models.contracts import ToolCallStatus  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402
from app.tools.registry import (  # noqa: E402
    CreateTicketArgs,
    SendReportArgs,
    ToolDefinition,
    ToolRegistry,
)
from tests.conftest import (  # noqa: E402
    make_seeded_sqlite_session_factory,
    make_sqlite_session_factory,
)


def _registry(factory: Any) -> tuple[ToolRegistry, ToolExecutor]:
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="create_ticket",
            description="Propose a ticket (pending approval; never executes)",
            input_schema=CreateTicketArgs,
        ),
        executor.execute_create_ticket,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="send_report",
            description="Propose a report (pending approval; never executes)",
            input_schema=SendReportArgs,
        ),
        executor.execute_send_report,  # type: ignore[arg-type]
    )
    return registry, executor


def _approval_rows(factory: Any) -> list[models.ApprovalRequest]:
    with factory() as session:
        return list(session.scalars(select(models.ApprovalRequest)).all())


def _ticket_rows(factory: Any) -> list[models.Ticket]:
    with factory() as session:
        return list(session.scalars(select(models.Ticket)).all())


def _report_rows(factory: Any) -> list[models.ReportJob]:
    with factory() as session:
        return list(session.scalars(select(models.ReportJob)).all())


# ---------------------------------------------------------------------------
# create_ticket: pending proposal only, never a side effect
# ---------------------------------------------------------------------------


def test_create_ticket_produces_pending_proposal_only() -> None:
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    mock_actions = MockActionExecutor()

    result = executor.execute_create_ticket(
        title="Refund delayed",
        priority="high",
        customer_id="CUST-1001",
        description="Customer reports a late refund.",
        idempotency_key="task006-ticket-0001",
        requesting_run_id=str(uuid.uuid4()),
    )
    assert result.status == ToolCallStatus.WAITING_APPROVAL
    assert result.result is not None
    assert result.result["status"] == "pending"

    rows = _approval_rows(factory)
    assert len(rows) == 1
    assert rows[0].action_type == "create_ticket"
    assert rows[0].status == "pending"
    # No ticket row, no mocked execution: proposal only, zero side effects.
    assert _ticket_rows(factory) == []
    assert mock_actions.counts() == {"tickets": 0, "reports": 0}


def test_create_ticket_unknown_customer_is_not_found() -> None:
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)

    result = executor.execute_create_ticket(
        title="Refund delayed",
        priority="high",
        customer_id="CUST-9999",
        idempotency_key="task006-ticket-0002",
    )
    assert result.status == ToolCallStatus.ERROR
    assert result.error_category is not None
    assert result.error_category.value == "not_found"
    assert _approval_rows(factory) == []
    assert _ticket_rows(factory) == []


def test_create_ticket_rejects_malformed_payload_at_registry() -> None:
    factory = make_sqlite_session_factory()
    registry, _ = _registry(factory)
    valid, err = registry.validate_call("create_ticket", {"title": "", "priority": "mega"})
    assert valid is False
    assert err is not None


def test_create_ticket_idempotency_prevents_duplicates() -> None:
    factory = make_seeded_sqlite_session_factory()
    mock_actions = MockActionExecutor()
    first_run = str(uuid.uuid4())
    second_run = str(uuid.uuid4())

    executor = ToolExecutor(factory)
    first = executor.execute_create_ticket(
        title="Refund delayed",
        priority="high",
        customer_id="CUST-1001",
        idempotency_key="task006-ticket-dup-0001",
        requesting_run_id=first_run,
    )
    second = executor.execute_create_ticket(
        title="Refund delayed",
        priority="high",
        customer_id="CUST-1001",
        idempotency_key="task006-ticket-dup-0001",
        requesting_run_id=second_run,
    )
    assert first.status == ToolCallStatus.WAITING_APPROVAL
    assert second.status == ToolCallStatus.SKIPPED
    assert second.result is not None and second.result.get("duplicate") is True
    assert first.result["proposal_id"] == second.result["proposal_id"]

    rows = _approval_rows(factory)
    assert len(rows) == 1
    # Same key maps to the same durable proposal even across retry-like calls.
    assert rows[0].status == "pending"
    assert _ticket_rows(factory) == []
    assert mock_actions.counts() == {"tickets": 0, "reports": 0}


# ---------------------------------------------------------------------------
# send_report: pending proposal only, never a side effect
# ---------------------------------------------------------------------------


def test_send_report_produces_pending_proposal_only() -> None:
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    mock_actions = MockActionExecutor()

    result = executor.execute_send_report(
        title="Weekly ops digest",
        destination="mock",
        payload_json='{"week": 41}',
        idempotency_key="task006-report-0001",
        requesting_run_id=str(uuid.uuid4()),
    )
    assert result.status == ToolCallStatus.WAITING_APPROVAL
    assert result.result is not None
    assert result.result["status"] == "pending"

    rows = _approval_rows(factory)
    assert len(rows) == 1
    assert rows[0].action_type == "send_report"
    assert rows[0].status == "pending"
    # No report-job row, no mocked execution: proposal only, zero side effects.
    assert _report_rows(factory) == []
    assert mock_actions.counts() == {"tickets": 0, "reports": 0}


def test_send_report_rejects_malformed_payload() -> None:
    factory = make_sqlite_session_factory()
    executor = ToolExecutor(factory)
    mock_actions = MockActionExecutor()

    bad_json = executor.execute_send_report(
        title="Weekly ops digest",
        destination="mock",
        payload_json="{not-json",
        idempotency_key="task006-report-0002",
    )
    assert bad_json.status == ToolCallStatus.ERROR
    assert bad_json.error_category is not None
    assert bad_json.error_category.value == "validation_error"

    live_destination = executor.execute_send_report(
        title="Weekly ops digest",
        destination="ops@example.com",
        idempotency_key="task006-report-0003",
    )
    assert live_destination.status == ToolCallStatus.ERROR
    assert "mock" in (live_destination.error or "").lower()

    factory2_registry, _ = _registry(factory)
    valid, _ = factory2_registry.validate_call("send_report", {"title": "x"})
    assert valid is False

    assert _approval_rows(factory) == []
    assert _report_rows(factory) == []
    assert mock_actions.counts() == {"tickets": 0, "reports": 0}


def test_send_report_idempotency_prevents_duplicates() -> None:
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)

    first = executor.execute_send_report(
        title="Weekly ops digest",
        destination="mock",
        payload_json='{"week": 41}',
        idempotency_key="task006-report-dup-0001",
    )
    second = executor.execute_send_report(
        title="Weekly ops digest",
        destination="mock",
        payload_json='{"week": 41}',
        idempotency_key="task006-report-dup-0001",
    )
    assert first.status == ToolCallStatus.WAITING_APPROVAL
    assert second.status == ToolCallStatus.SKIPPED
    assert second.result is not None and second.result.get("duplicate") is True
    assert first.result["proposal_id"] == second.result["proposal_id"]

    rows = _approval_rows(factory)
    assert len(rows) == 1
    assert _report_rows(factory) == []


# ---------------------------------------------------------------------------
# Boundary: the proposal tools must never reach the mocked executors
# ---------------------------------------------------------------------------


def test_mock_executor_stays_idle_until_approval_layer_uses_it() -> None:
    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    mock_actions = MockActionExecutor()

    executor.execute_create_ticket(
        title="Refund delayed",
        priority="high",
        customer_id="CUST-1001",
        idempotency_key="task006-boundary-0001",
    )
    executor.execute_send_report(
        title="Weekly ops digest",
        destination="mock",
        idempotency_key="task006-boundary-0002",
    )
    assert mock_actions.counts() == {"tickets": 0, "reports": 0}
    assert len(_approval_rows(factory)) == 2
    assert _ticket_rows(factory) == []
    assert _report_rows(factory) == []


# ---------------------------------------------------------------------------
# Graph: a model-proposed action pauses with waiting_approval state
# ---------------------------------------------------------------------------


def test_graph_create_ticket_pauses_with_waiting_approval() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall
    from app.models.fake_adapter import FakeModelAdapter
    from app.tools.registry import CreateTicketArgs, SendReportArgs

    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="create_ticket", description="propose ticket", input_schema=CreateTicketArgs
        ),
        executor.execute_create_ticket,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="send_report", description="propose report", input_schema=SendReportArgs
        ),
        executor.execute_send_report,  # type: ignore[arg-type]
    )
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="a1",
                        type="function",
                        function={
                            "name": "create_ticket",
                            "arguments": (
                                '{"title": "Refund delayed", "priority": "high", '
                                '"customer_id": "CUST-1001", '
                                '"idempotency_key": "task006-graph-0001"}'
                            ),
                        },
                    )
                ],
            ),
            ModelResponse(content="Proposal created."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Create a ticket")
    result = asyncio.run(graph.ainvoke(state.model_dump()))
    tool_results = result.get("tool_results", [])
    ticket_results = [r for r in tool_results if r.get("tool_name") == "create_ticket"]
    assert ticket_results, "expected a create_ticket tool result"
    assert ticket_results[0]["status"] == "waiting_approval"

    rows = _approval_rows(factory)
    assert any(r.action_type == "create_ticket" and r.status == "pending" for r in rows)
    # Graph ran the proposal only — no ticket row and no action execution.
    assert _ticket_rows(factory) == []


def test_graph_duplicate_proposal_is_single_pending_record() -> None:
    import asyncio

    from app.agent.graph import build_graph
    from app.agent.state import GraphState
    from app.models.adapter import ModelResponse, ToolCall
    from app.models.fake_adapter import FakeModelAdapter
    from app.tools.registry import CreateTicketArgs, SendReportArgs

    factory = make_seeded_sqlite_session_factory()
    executor = ToolExecutor(factory)
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="create_ticket", description="propose ticket", input_schema=CreateTicketArgs
        ),
        executor.execute_create_ticket,  # type: ignore[arg-type]
    )
    registry.register(
        ToolDefinition(
            name="send_report", description="propose report", input_schema=SendReportArgs
        ),
        executor.execute_send_report,  # type: ignore[arg-type]
    )
    args = (
        '{"title": "Refund delayed", "priority": "high", "customer_id": "CUST-1001", '
        '"idempotency_key": "task006-graph-dup-0001"}'
    )
    adapter = FakeModelAdapter(
        responses=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="a2",
                        type="function",
                        function={"name": "create_ticket", "arguments": args},
                    )
                ],
            ),
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="a3",
                        type="function",
                        function={"name": "create_ticket", "arguments": args},
                    )
                ],
            ),
            ModelResponse(content="Done."),
        ]
    )
    graph = build_graph(adapter, executor, registry)
    state = GraphState(
        run_id=uuid.uuid4(), thread_id=uuid.uuid4(), user_request="Create a ticket, then again"
    )
    asyncio.run(graph.ainvoke(state.model_dump()))
    rows = _approval_rows(factory)
    assert len([r for r in rows if r.action_type == "create_ticket"]) == 1
    assert _ticket_rows(factory) == []
