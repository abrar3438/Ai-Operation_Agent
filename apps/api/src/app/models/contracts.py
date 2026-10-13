from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCallStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


class ErrorCategory(str, Enum):
    VALIDATION_ERROR = "validation_error"  # Permanent: user input was bad
    NOT_FOUND = "not_found"  # Permanent: record does not exist
    TIMEOUT = "timeout"  # Transient: request hung
    PROVIDER_ERROR = "provider_error"  # Could be transient (5xx) or permanent (4xx)
    AUTHORIZATION_ERROR = "authorization_error"  # Permanent: keys/credentials bad
    INTERNAL_ERROR = "internal_error"  # Unexpected exception
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"  # Transient exhaustion
    INVALID_RESPONSE = "invalid_response"  # Permanent agent/model semantic mismatch
    RATE_LIMIT_ERROR = "rate_limit_error"  # Transient: slow down


class AgentRequest(BaseModel):
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_request: str = Field(min_length=1, max_length=8000)
    thread_id: uuid.UUID | None = None


class ToolCallRequest(BaseModel):
    tool_name: str = Field(
        pattern=r"^(get_customer|get_order|search_database|search_documents|calculate|create_ticket|send_report)$"
    )
    arguments: dict[str, Any]
    idempotency_key: str = Field(min_length=8, max_length=128)


class ToolResult(BaseModel):
    tool_name: str
    status: ToolCallStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    error_category: ErrorCategory | None = None
    duration_ms: int = 0
    retry_count: int = 0


class FinalAnswer(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    confidence: float | None = None


class RunResult(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    final_answer: FinalAnswer | None = None
    tool_results: list[ToolResult] = Field(default_factory=list)
    terminal_reason: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    model_label: str
    provider_label: str


class StructuredError(BaseModel):
    category: ErrorCategory
    message: str
    retryable: bool
    details: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    run_id: uuid.UUID
    thread_id: uuid.UUID
    user_request: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls_count: int = 0
    step_count: int = 0
    max_steps: int = 12
    max_tool_calls: int = 8
    tool_results: list[ToolResult] = Field(default_factory=list)
    pending_approval_id: str | None = None
    terminal_status: RunStatus | None = None
    final_answer: FinalAnswer | None = None
    error: StructuredError | None = None
    model_label: str = "unset"
    provider_label: str = "unset"
