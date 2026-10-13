from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentRun, ApprovalRequest, ToolEvent
from app.db.session import create_sync_engine, get_session_factory

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


@router.get("")
def list_runs(
    status: str | None = None,
    model_label: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> list[dict[str, Any]]:
    query = select(AgentRun)
    if status:
        query = query.where(AgentRun.status == status)
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
    run = session.scalar(select(AgentRun).where(Agentrun_id_cond(run_id)))  # type: ignore[attr-defined]
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


def Agentrun_id_cond(run_id: str):
    return AgentRun.run_id == run_id
