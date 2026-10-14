from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.graph import build_graph
from app.agent.state import initial_state
from app.db.models import AgentRun, ApprovalRequest, ToolEvent
from app.db.session import create_sync_engine, get_session_factory
from app.models.adapter import ModelConfig
from app.models.contracts import AgentRequest
from app.models.openai_adapter import create_model_adapter
from app.tools.executor import ToolExecutor
from app.tools.registry import (
    CalculateArgs,
    CreateTicketArgs,
    GetCustomerArgs,
    GetOrderArgs,
    SearchDatabaseArgs,
    SearchDocumentsArgs,
    SendReportArgs,
    ToolDefinition,
    ToolRegistry,
)

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


def verify_operator_role(
    x_operator_role: Annotated[str | None, Header()] = None,
) -> str:
    if not x_operator_role or x_operator_role.lower() != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Operator role required via X-Operator-Role header",
        )
    return x_operator_role


def get_db_session() -> Iterator[Session]:
    engine = create_sync_engine()
    factory = get_session_factory(engine)
    with factory() as session:
        yield session


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_agent_run(
    payload: AgentRequest,
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> dict[str, Any]:
    try:
        run_id = payload.request_id
        thread_id = payload.thread_id or uuid.uuid4()
        started_at = datetime.now(UTC)

        factory = get_session_factory(create_sync_engine())
        executor = ToolExecutor(factory)
        registry = ToolRegistry()
        registry.register(
            ToolDefinition(name="get_customer", description="x", input_schema=GetCustomerArgs),
            executor.execute_get_customer,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(name="get_order", description="x", input_schema=GetOrderArgs),
            executor.execute_get_order,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(
                name="search_database",
                description="x",
                input_schema=SearchDatabaseArgs,
            ),
            executor.execute_search_database,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(
                name="search_documents",
                description="x",
                input_schema=SearchDocumentsArgs,
            ),
            executor.execute_search_documents,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(name="calculate", description="x", input_schema=CalculateArgs),
            executor.execute_calculate,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(name="create_ticket", description="x", input_schema=CreateTicketArgs),
            executor.execute_create_ticket,  # type: ignore[arg-type]
        )
        registry.register(
            ToolDefinition(name="send_report", description="x", input_schema=SendReportArgs),
            executor.execute_send_report,  # type: ignore[arg-type]
        )

        config = ModelConfig.from_env()
        adapter = create_model_adapter(config)

        graph = build_graph(adapter, executor, registry)
        state = initial_state(
            user_request=payload.user_request,
            run_id=run_id,
            thread_id=thread_id,
            model_label=config.model,
            provider_label=adapter.get_provider_name(),
        )

        result = await graph.ainvoke(state.model_dump())
        finished_at = datetime.now(UTC)

        term_status = result.get("terminal_status", "succeeded")
        final_answer = result.get("final_answer")

        # Persist run record
        run_record = AgentRun(
            run_id=str(run_id),
            thread_id=str(thread_id),
            request_preview=payload.user_request[:500],
            status=term_status,
            model_label=config.model,
            provider_label=adapter.get_provider_name(),
            final_answer=final_answer,
            started_at=started_at,
            finished_at=finished_at,
        )
        session.add(run_record)

        # Persist tool events
        tool_results = result.get("tool_results", [])
        for idx, tr in enumerate(tool_results, start=1):
            event = ToolEvent(
                run_id=str(run_id),
                sequence=idx,
                stage="dispatch",
                tool_name=tr.get("tool_name"),
                status=tr.get("status", "ok"),
                duration_ms=tr.get("duration_ms", 0),
                retry_count=0,
                error_category=tr.get("error_category"),
                detail_summary=str(tr.get("result") or tr.get("error") or "")[:1000],
            )
            session.add(event)

        session.commit()

        return {
            "run_id": str(run_id),
            "thread_id": str(thread_id),
            "status": term_status,
            "final_answer": final_answer,
            "pending_approval_id": result.get("pending_approval_id"),
            "tool_results_count": len(tool_results),
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Agent execution error: {str(e)}") from e


@router.get("")
def list_runs(
    status_filter: str | None = Query(default=None, alias="status"),
    model_label: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> list[dict[str, Any]]:
    query = select(AgentRun)
    if status_filter:
        query = query.where(AgentRun.status == status_filter)
    if model_label:
        query = query.where(AgentRun.model_label == model_label)

    rows = session.scalars(
        query.order_by(AgentRun.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return [
        {
            "run_id": r.run_id,
            "thread_id": r.thread_id,
            "request_preview": r.request_preview,
            "status": r.status,
            "model_label": r.model_label,
            "provider_label": r.provider_label,
            "terminal_reason": r.terminal_reason,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{run_id}")
def get_run_details(
    run_id: str,
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> dict[str, Any]:
    run = session.scalar(select(AgentRun).where(AgentRun.run_id == run_id))
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    events = session.scalars(
        select(ToolEvent).where(ToolEvent.run_id == run_id).order_by(ToolEvent.sequence.asc())
    ).all()

    approvals = session.scalars(
        select(ApprovalRequest).where(ApprovalRequest.requesting_run_id == run.id)
    ).all()

    duration_ms = 0
    if run.started_at and run.finished_at:
        duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

    timeline = [
        {
            "sequence": e.sequence,
            "stage": e.stage,
            "tool_name": e.tool_name,
            "status": e.status,
            "duration_ms": e.duration_ms,
            "retry_count": e.retry_count,
            "error_category": e.error_category,
            "detail_summary": e.detail_summary,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]

    approval_records = [
        {
            "approval_id": str(a.id),
            "action_type": a.action_type,
            "status": a.status,
            "reviewer": a.reviewer,
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
        }
        for a in approvals
    ]

    return {
        "run_id": run.run_id,
        "thread_id": run.thread_id,
        "request_preview": run.request_preview,
        "status": run.status,
        "model_label": run.model_label,
        "provider_label": run.provider_label,
        "terminal_reason": run.terminal_reason,
        "final_answer": run.final_answer,
        "tool_call_count": len(events),
        "duration_ms": duration_ms,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "timeline": timeline,
        "approvals": approval_records,
    }
