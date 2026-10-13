from __future__ import annotations

from app.evals.schemas import Scenario

SCENARIOS: list[Scenario] = [
    Scenario(
        id="normal-customer-lookup",
        description="Lookup valid customer",
        user_request="Get info for customer CUST-1001",
        expected_tools=["get_customer"],
        expected_terminal_status="succeeded",
        expected_answer_contains=["Acme Manufacturing"],
    ),
    Scenario(
        id="missing-record",
        description="Lookup non-existent customer",
        user_request="Get info for customer CUST-9999",
        expected_tools=["get_customer"],
        expected_terminal_status="failed",
        expected_error_category="not_found",
    ),
    Scenario(
        id="no-results-documents",
        description="Search unknown document topic",
        user_request="Search for pizza recipes in internal documents",
        expected_tools=["search_documents"],
        expected_terminal_status="succeeded",
        expected_answer_contains=["No relevant documents found"],
    ),
    Scenario(
        id="arithmetic-calc",
        description="Perform basic arithmetic",
        user_request="Calculate 100 plus 50",
        expected_tools=["calculate"],
        expected_terminal_status="succeeded",
        expected_answer_contains=["150"],
    ),
    Scenario(
        id="unsupported-action",
        description="Attempt unsupported action",
        user_request="Delete order ORD-5001",
        expected_tools=[],
        expected_terminal_status="failed",
        expected_error_category="validation_error",
    ),
]
