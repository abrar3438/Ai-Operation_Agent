from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CustomerSummary(BaseModel):
    customer_id: str
    display_name: str
    tier: str
    status: str


class OrderSummary(BaseModel):
    order_id: str
    customer_id: str
    status: str
    total_cents: int
    currency: str
    summary: str


class DocumentSummary(BaseModel):
    source_id: str
    title: str
    excerpt: str


class ActionProposal(BaseModel):
    action_type: str = Field(pattern=r"^(create_ticket|send_report)$")
    action_reference: str
    arguments_json: str = "{}"
    requesting_run_id: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern=r"^(approved|rejected)$")
    reviewer: str = Field(min_length=1, max_length=120)


class RunRecord(BaseModel):
    run_id: str
    thread_id: str
    request_preview: str = ""
    status: str
    model_label: str = "unset"
    provider_label: str = "unset"
    terminal_reason: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ToolEventRecord(BaseModel):
    run_id: str
    sequence: int = 0
    stage: str
    tool_name: str | None = None
    status: str
    duration_ms: int = 0
    retry_count: int = 0
    error_category: str | None = None
    detail_summary: str = ""
