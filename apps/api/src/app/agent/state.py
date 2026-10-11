from __future__ import annotations

import operator
import uuid
from typing import Annotated, Any

from pydantic import BaseModel, Field


class GraphState(BaseModel):
    run_id: uuid.UUID
    thread_id: uuid.UUID
    user_request: str
    normalized_request: str | None = None
    messages: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)
    tool_results: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)
    pending_tool_calls: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)
    pending_approval_id: str | None = None
    step_count: int = 0
    tool_calls_count: int = 0
    max_steps: int = 12
    max_tool_calls: int = 8
    terminal_status: str | None = None
    final_answer: str | None = None
    error: dict[str, Any] | None = None
    model_label: str = "unset"
    provider_label: str = "unset"
