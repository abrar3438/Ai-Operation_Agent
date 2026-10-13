from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    id: str
    description: str
    user_request: str
    expected_tools: list[str] = Field(default_factory=list)
    # Expected terminal state (e.g., 'succeeded', 'failed', 'waiting_approval')
    expected_terminal_status: str
    # Whether approval is required for the final action
    requires_approval: bool = False
    # Content keywords or constraints for the final answer
    expected_answer_contains: list[str] = Field(default_factory=list)
    # Categories of errors expected (if failed)
    expected_error_category: str | None = None
