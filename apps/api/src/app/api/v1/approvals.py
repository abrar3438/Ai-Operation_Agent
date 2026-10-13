from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.actions.executor import MockActionExecutor
from app.db.models import ApprovalRequest, utcnow
from app.db.repositories import decide_approval, record_tool_event
from app.db.session import create_sync_engine, get_session_factory
from app.models.contracts import ToolCallStatus, ToolResult

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

# Shared singleton mock action executor for the MVP lifecycle
mock_action_executor = MockActionExecutor()


class ApprovalDecisionPayload(BaseModel):
    reviewer: str = Field(min_length=1, max_length=120)


def verify_operator_role(
    x_operator_role: Annotated[str | None, Header()] = None,
) -> str:
    """Local single-operator MVP authorization boundary.

    Limitation: trusts the X-Operator-Role header; suitable for local dev
    and testing only, not a production OAuth/OIDC implementation.
    """
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
def list_approvals(
    status_filter: str | None = None,
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> list[dict[str, Any]]:
    query = select(ApprovalRequest)
    if status_filter:
        query = query.where(ApprovalRequest.status == status_filter)
    rows = session.scalars(query.order_by(ApprovalRequest.created_at.desc())).all()
    return [
        {
            "id": str(r.id),
            "action_type": r.action_type,
            "action_reference": r.action_reference,
            "status": r.status,
            "reviewer": r.reviewer,
            "created_at": r.created_at.isoformat(),
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            "arguments": json.loads(r.arguments_json),
        }
        for r in rows
    ]


@router.get("/{approval_id}")
def get_approval(
    approval_id: str,
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> dict[str, Any]:
    r = session.get(ApprovalRequest, approval_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"Approval request not found: {approval_id}")
    return {
        "id": str(r.id),
        "action_type": r.action_type,
        "action_reference": r.action_reference,
        "arguments": json.loads(r.arguments_json),
        "status": r.status,
        "reviewer": r.reviewer,
        "created_at": r.created_at.isoformat(),
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
    }


@router.post("/{approval_id}/approve")
def approve_proposal(
    approval_id: str,
    payload: ApprovalDecisionPayload,
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> dict[str, Any]:
    record = session.get(ApprovalRequest, approval_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Approval request not found: {approval_id}")

    # Revalidation: status must be pending, and check expiry if set
    if record.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve proposal in status: {record.status!r}",
        )
    if record.expires_at:
        exp = record.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        if exp < utcnow():
            record.status = "expired"
            session.commit()
            raise HTTPException(status_code=400, detail="Approval request has expired")

    try:
        # Atomic decision transition
        with session.begin_nested():
            decide_approval(
                session,
                approval_id,
                decision="approved",
                reviewer=payload.reviewer,
            )

            # Revalidate payload before action execution
            args = json.loads(record.arguments_json)
            exec_result: ToolResult

            if record.action_type == "create_ticket":
                exec_result = mock_action_executor.execute_ticket(
                    proposal_id=str(record.id),
                    title=args.get("title", ""),
                    priority=args.get("priority", "normal"),
                    customer_id=args.get("customer_id", ""),
                )
            elif record.action_type == "send_report":
                exec_result = mock_action_executor.execute_report(
                    proposal_id=str(record.id),
                    title=args.get("title", "Report"),
                    destination=args.get("destination", "mock"),
                )
            else:
                raise ValueError(f"Unknown action type: {record.action_type}")

            if exec_result.status != ToolCallStatus.OK:
                raise RuntimeError(f"Action execution failed: {exec_result.error}")

            # Durable audit event
            if record.requesting_run_id:
                record_tool_event(
                    session,
                    run_id=str(record.requesting_run_id),
                    sequence=999,
                    stage="approval_execution",
                    status="ok",
                    tool_name=record.action_type,
                    detail_summary=f"Approved by {payload.reviewer}. Executed successfully.",
                )
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Approval execution error: {str(e)}") from e

    return {
        "status": "approved",
        "approval_id": approval_id,
        "reviewer": payload.reviewer,
        "execution_result": exec_result.result,
    }


@router.post("/{approval_id}/reject")
def reject_proposal(
    approval_id: str,
    payload: ApprovalDecisionPayload,
    session: Session = Depends(get_db_session),  # noqa: B008
    _: str = Depends(verify_operator_role),  # noqa: B008
) -> dict[str, Any]:
    record = session.get(ApprovalRequest, approval_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Approval request not found: {approval_id}")

    if record.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject proposal in status: {record.status!r}",
        )

    try:
        with session.begin_nested():
            decide_approval(
                session,
                approval_id,
                decision="rejected",
                reviewer=payload.reviewer,
            )
            if record.requesting_run_id:
                record_tool_event(
                    session,
                    run_id=str(record.requesting_run_id),
                    sequence=999,
                    stage="approval_execution",
                    status="skipped",
                    tool_name=record.action_type,
                    detail_summary=f"Rejected by {payload.reviewer}. Zero side effects.",
                )
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Rejection error: {str(e)}") from e

    return {
        "status": "rejected",
        "approval_id": approval_id,
        "reviewer": payload.reviewer,
    }
