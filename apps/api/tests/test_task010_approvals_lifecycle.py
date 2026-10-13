from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from datetime import UTC  # noqa: E402

from app.api.v1.approvals import mock_action_executor  # noqa: E402
from app.main import app  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402
from tests.conftest import make_seeded_sqlite_session_factory  # noqa: E402


@pytest.fixture
def client_and_factory():
    factory = make_seeded_sqlite_session_factory()
    from app.api.v1 import approvals

    def _override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[approvals.get_db_session] = _override_session
    client = TestClient(app)
    yield client, factory
    app.dependency_overrides.clear()


def test_unauthorized_decision_rejected(client_and_factory) -> None:
    client, factory = client_and_factory
    executor = ToolExecutor(factory)
    res = executor.execute_create_ticket(
        title="Unauthorized test",
        priority="normal",
        customer_id="CUST-1001",
        idempotency_key="task010-unauth-0001",
    )
    proposal_id = res.result["proposal_id"]

    response = client.post(
        f"/api/v1/approvals/{proposal_id}/approve",
        json={"reviewer": "operator-1"},
    )
    assert response.status_code == 403

    response = client.post(
        f"/api/v1/approvals/{proposal_id}/approve",
        headers={"X-Operator-Role": "viewer"},
        json={"reviewer": "operator-1"},
    )
    assert response.status_code == 403


def test_pending_to_approved_to_executed(client_and_factory) -> None:
    client, factory = client_and_factory
    executor = ToolExecutor(factory)
    res = executor.execute_create_ticket(
        title="Server failure",
        priority="urgent",
        customer_id="CUST-1001",
        idempotency_key="task010-approve-0001",
    )
    proposal_id = res.result["proposal_id"]
    initial_tickets_count = len(mock_action_executor.executed_tickets)

    response = client.post(
        f"/api/v1/approvals/{proposal_id}/approve",
        headers={"X-Operator-Role": "operator"},
        json={"reviewer": "senior-operator"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    initial_stats = initial_tickets_count + 1
    assert len(mock_action_executor.executed_tickets) == initial_stats
    assert mock_action_executor.executed_tickets[-1].customer_id == "CUST-1001"


def test_pending_to_rejected_not_executed(client_and_factory) -> None:
    client, factory = client_and_factory
    executor = ToolExecutor(factory)
    res = executor.execute_send_report(
        title="Bad report",
        destination="mock",
        payload_json='{"bad": true}',
        idempotency_key="task010-reject-0001",
    )
    proposal_id = res.result["proposal_id"]
    initial_reports_count = len(mock_action_executor.executed_reports)

    response = client.post(
        f"/api/v1/approvals/{proposal_id}/reject",
        headers={"X-Operator-Role": "operator"},
        json={"reviewer": "security-officer"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert len(mock_action_executor.executed_reports) == initial_reports_count


def test_duplicate_or_late_decision_fails(client_and_factory) -> None:
    client, factory = client_and_factory
    executor = ToolExecutor(factory)
    res = executor.execute_create_ticket(
        title="Duplicate test",
        priority="low",
        customer_id="CUST-1001",
        idempotency_key="task010-late-0001",
    )
    proposal_id = res.result["proposal_id"]

    response1 = client.post(
        f"/api/v1/approvals/{proposal_id}/approve",
        headers={"X-Operator-Role": "operator"},
        json={"reviewer": "op-1"},
    )
    assert response1.status_code == 200

    response2 = client.post(
        f"/api/v1/approvals/{proposal_id}/reject",
        headers={"X-Operator-Role": "operator"},
        json={"reviewer": "op-2"},
    )
    assert response2.status_code == 400

    response3 = client.post(
        f"/api/v1/approvals/{proposal_id}/approve",
        headers={"X-Operator-Role": "operator"},
        json={"reviewer": "op-3"},
    )
    assert response3.status_code == 400


def test_expired_proposal_fails(client_and_factory) -> None:
    client, factory = client_and_factory
    executor = ToolExecutor(factory)
    res = executor.execute_create_ticket(
        title="Expired test",
        priority="low",
        customer_id="CUST-1001",
        idempotency_key="task010-expired-0001",
    )
    proposal_id = res.result["proposal_id"]

    # Backdate expires_at in DB
    from datetime import datetime, timedelta

    from app.db.models import ApprovalRequest

    with factory() as session:
        req = session.get(ApprovalRequest, proposal_id)
        if req:
            req.expires_at = datetime.now(UTC) - timedelta(hours=1)
            session.commit()

    response = client.post(
        f"/api/v1/approvals/{proposal_id}/approve",
        headers={"X-Operator-Role": "operator"},
        json={"reviewer": "op-1"},
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()
