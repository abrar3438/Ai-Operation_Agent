from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.contracts import ErrorCategory, ToolCallStatus, ToolResult


class MockTicketRecord(BaseModel):
    reference: str
    title: str
    priority: str
    customer_id: str
    status: str = "open"
    executed_at: datetime | None = None


class MockReportRecord(BaseModel):
    reference: str
    title: str
    destination: str = "mock"
    status: str = "delivered_mock"
    executed_at: datetime | None = None


class MockActionExecutor:
    """Post-approval action executor with mocked/local adapters only.

    TASK-006 boundary: this class is NEVER called from the proposal tools.
    It exists so a later approval service (TASK-007) can execute an *approved*
    proposal exactly once. No email, no external ticket provider, no network.
    Every execution is recorded in-memory and stamped, so tests can prove
    whether or not a side effect happened.
    """

    def __init__(self) -> None:
        self.executed_tickets: list[MockTicketRecord] = []
        self.executed_reports: list[MockReportRecord] = []
        self.ticket_sequence = 0
        self.report_sequence = 0

    def execute_ticket(
        self, *, proposal_id: str, title: str, priority: str, customer_id: str
    ) -> ToolResult:
        from app.db.models import utcnow

        self.ticket_sequence += 1
        record = MockTicketRecord(
            reference=f"MOCK-TICKET-{self.ticket_sequence:04d}",
            title=title,
            priority=priority,
            customer_id=customer_id,
            executed_at=utcnow(),
        )
        self.executed_tickets.append(record)
        return ToolResult(
            tool_name="create_ticket",
            status=ToolCallStatus.OK,
            result={"reference": record.reference, "proposal_id": proposal_id, "mocked": True},
        )

    def execute_report(self, *, proposal_id: str, title: str, destination: str) -> ToolResult:
        from app.db.models import utcnow

        if destination != "mock":
            return ToolResult(
                tool_name="send_report",
                status=ToolCallStatus.ERROR,
                error="Only mock delivery is supported",
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        self.report_sequence += 1
        record = MockReportRecord(
            reference=f"MOCK-REPORT-{self.report_sequence:04d}",
            title=title,
            destination=destination,
            executed_at=utcnow(),
        )
        self.executed_reports.append(record)
        return ToolResult(
            tool_name="send_report",
            status=ToolCallStatus.OK,
            result={"reference": record.reference, "proposal_id": proposal_id, "mocked": True},
        )

    def counts(self) -> dict[str, int]:
        return {"tickets": len(self.executed_tickets), "reports": len(self.executed_reports)}
