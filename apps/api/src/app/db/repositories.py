from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models

READ_ONLY_ORDER_STATUSES = {"pending", "paid", "shipped", "delivered", "cancelled", "refunded"}
READ_ONLY_CUSTOMER_STATUSES = {"active", "inactive", "suspended"}
APPROVAL_STATUSES = {"pending", "approved", "rejected", "expired"}
RUN_STATUSES = {"queued", "running", "waiting_approval", "succeeded", "failed", "cancelled"}
ACTION_TYPES = {"create_ticket", "send_report"}


def validate_status(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        raise ValueError(f"Invalid {field} status: {value!r}")
    return value


def get_customer(session: Session, customer_id: str) -> models.Customer | None:
    return session.scalar(select(models.Customer).where(models.Customer.customer_id == customer_id))


def get_order(session: Session, order_id: str) -> models.SyntheticOrder | None:
    return session.scalar(
        select(models.SyntheticOrder).where(models.SyntheticOrder.order_id == order_id)
    )


def list_customer_orders(
    session: Session, customer_id: str, limit: int = 50
) -> list[models.SyntheticOrder]:
    limit = max(1, min(limit, 200))
    rows = session.scalars(
        select(models.SyntheticOrder)
        .where(models.SyntheticOrder.customer_id == customer_id)
        .order_by(models.SyntheticOrder.created_at.desc())
        .limit(limit)
    )
    return list(rows)


def search_documents(session: Session, query: str, limit: int = 10) -> list[models.Document]:
    limit = max(1, min(limit, 50))
    pattern = f"%{query.strip().lower()}%"
    rows = session.scalars(
        select(models.Document)
        .where(
            func.lower(models.Document.title).like(pattern)
            | func.lower(models.Document.content).like(pattern)
            | func.lower(models.Document.tags).like(pattern)
        )
        .order_by(models.Document.source_id.asc())
        .limit(limit)
    )
    return list(rows)


def create_approval_request(
    session: Session,
    *,
    action_type: str,
    action_reference: str,
    arguments_json: str,
    idempotency_key: str,
    requesting_run_id: str | None = None,
) -> tuple[models.ApprovalRequest, bool]:
    validate_status_values(action_type, action_reference, idempotency_key)
    existing = session.scalar(
        select(models.ApprovalRequest).where(
            models.ApprovalRequest.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing, False
    record = models.ApprovalRequest(
        action_type=action_type,
        action_reference=action_reference,
        arguments_json=arguments_json,
        idempotency_key=idempotency_key,
        status="pending",
    )
    if requesting_run_id is not None:
        record.requesting_run_id = uuid.UUID(requesting_run_id)
    session.add(record)
    session.flush()
    return record, True


def validate_status_values(action_type: str, action_reference: str, idempotency_key: str) -> None:
    if action_type not in ACTION_TYPES:
        raise ValueError(f"Invalid action_type: {action_type!r}")
    if not action_reference or len(action_reference) > 64:
        raise ValueError("action_reference must be 1-64 characters")
    if not idempotency_key or len(idempotency_key) > 128:
        raise ValueError("idempotency_key must be 1-128 characters")


def decide_approval(
    session: Session,
    approval_id: str,
    *,
    decision: str,
    reviewer: str,
    decided_at: datetime | None = None,
) -> models.ApprovalRequest:
    if decision not in {"approved", "rejected"}:
        raise ValueError(f"Invalid decision: {decision!r}")
    if not reviewer or len(reviewer) > 120:
        raise ValueError("reviewer must be 1-120 characters")
    record = session.get(models.ApprovalRequest, approval_id)
    if record is None:
        raise LookupError(f"Approval request not found: {approval_id}")
    if record.status != "pending":
        raise ValueError(f"Approval request is already decided: {record.status}")
    record.status = decision
    record.reviewer = reviewer
    record.decided_at = decided_at or models.utcnow()
    session.flush()
    return record


def record_tool_event(
    session: Session,
    *,
    run_id: str,
    sequence: int,
    stage: str,
    status: str,
    tool_name: str | None = None,
    duration_ms: int = 0,
    retry_count: int = 0,
    error_category: str | None = None,
    detail_summary: str = "",
) -> models.ToolEvent:
    if not run_id or not stage or not status:
        raise ValueError("run_id, stage, and status are required")
    event = models.ToolEvent(
        run_id=run_id,
        sequence=sequence,
        stage=stage,
        status=status,
        tool_name=tool_name,
        duration_ms=duration_ms,
        retry_count=retry_count,
        error_category=error_category,
        detail_summary=detail_summary[:1000],
    )
    session.add(event)
    session.flush()
    return event
