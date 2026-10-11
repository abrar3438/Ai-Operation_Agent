from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampedBase(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def utcnow() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)


class Customer(TimestampedBase):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, server_default="standard")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")

    __table_args__ = (
        CheckConstraint(
            "tier IN ('standard', 'business', 'enterprise')",
            name="ck_customers_tier",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')",
            name="ck_customers_status",
        ),
        Index("ix_customers_status", "status"),
    )


class SyntheticOrder(TimestampedBase):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    total_cents: Mapped[int] = mapped_column(nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default="USD")
    summary: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")

    __table_args__ = (
        ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        CheckConstraint(
            "status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled', 'refunded')",
            name="ck_orders_status",
        ),
        CheckConstraint("total_cents >= 0", name="ck_orders_total_cents_nonnegative"),
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_status", "status"),
    )


class Document(TimestampedBase):
    __tablename__ = "documents"

    source_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    tags: Mapped[str] = mapped_column(String(240), nullable=False, server_default="")

    __table_args__ = (Index("ix_documents_title", "title"),)


class Ticket(TimestampedBase):
    __tablename__ = "tickets"

    reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(nullable=False, server_default="")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, server_default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open")
    customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_tickets_status",
        ),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_customer_id", "customer_id"),
    )


class ReportJob(TimestampedBase):
    __tablename__ = "report_jobs"

    reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    payload: Mapped[str] = mapped_column(nullable=False, server_default="{}")
    destination: Mapped[str] = mapped_column(String(240), nullable=False, server_default="mock")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="queued")
    requested_by_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_report_jobs_status",
        ),
        Index("ix_report_jobs_status", "status"),
    )


class ApprovalRequest(TimestampedBase):
    __tablename__ = "approval_requests"

    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    arguments_json: Mapped[str] = mapped_column(nullable=False, server_default="{}")
    requesting_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    reviewer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('create_ticket', 'send_report')",
            name="ck_approval_requests_action_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name="ck_approval_requests_status",
        ),
        Index("ix_approval_requests_status", "status"),
        Index("ix_approval_requests_action_type", "action_type"),
    )


class AgentRun(TimestampedBase):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False)
    request_preview: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="queued")
    model_label: Mapped[str] = mapped_column(String(120), nullable=False, server_default="unset")
    provider_label: Mapped[str] = mapped_column(String(120), nullable=False, server_default="unset")
    terminal_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    final_answer: Mapped[str | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'queued', 'running', 'waiting_approval', "
            "'succeeded', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        Index("ix_agent_runs_status", "status"),
        Index("ix_agent_runs_thread_id", "thread_id"),
    )


class ToolEvent(TimestampedBase):
    __tablename__ = "tool_events"

    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False, server_default="0")
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int] = mapped_column(nullable=False, server_default="0")
    retry_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail_summary: Mapped[str] = mapped_column(String(1000), nullable=False, server_default="")

    __table_args__ = (
        CheckConstraint(
            "status IN ('ok', 'error', 'skipped', 'waiting_approval')",
            name="ck_tool_events_status",
        ),
        Index("ix_tool_events_run_id_sequence", "run_id", "sequence"),
    )


class EvaluationRun(TimestampedBase):
    __tablename__ = "evaluation_runs"

    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_label: Mapped[str] = mapped_column(String(120), nullable=False, server_default="unset")
    provider_label: Mapped[str] = mapped_column(String(120), nullable=False, server_default="unset")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="queued")
    summary_json: Mapped[str] = mapped_column(nullable=False, server_default="{}")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_evaluation_runs_status",
        ),
        Index("ix_evaluation_runs_dataset_version", "dataset_version"),
    )


class EvaluationCaseResult(TimestampedBase):
    __tablename__ = "evaluation_case_results"

    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    tool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail_json: Mapped[str] = mapped_column(nullable=False, server_default="{}")

    __table_args__ = (
        Index("ix_evaluation_case_results_run_id", "evaluation_run_id"),
        Index("ix_evaluation_case_results_case_id", "case_id"),
    )
