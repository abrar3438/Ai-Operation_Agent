from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import app  # noqa: E402
from tests.conftest import make_seeded_sqlite_session_factory  # noqa: E402


@pytest.fixture
def api_client():
    factory = make_seeded_sqlite_session_factory()
    from app.api.v1 import approvals, evals, runs

    def _override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[approvals.get_db_session] = _override_session
    app.dependency_overrides[runs.get_db_session] = _override_session
    app.dependency_overrides[evals.get_db_session] = _override_session

    client = TestClient(app)
    yield client, factory
    app.dependency_overrides.clear()


def test_health_endpoints(api_client) -> None:
    client, _ = api_client
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json() == {"status": "ok"}

    res_ready = client.get("/health/ready")
    assert res_ready.status_code in (200, 503)


def test_run_submission_and_detail_flow(api_client) -> None:
    client, _ = api_client
    payload = {
        "user_request": "Lookup customer CUST-1001",
        "thread_id": str(uuid.uuid4()),
    }
    res = client.post(
        "/api/v1/runs",
        headers={"X-Operator-Role": "operator"},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    run_id = data["run_id"]
    assert run_id is not None
    assert data["status"] in ("succeeded", "failed")

    list_res = client.get(
        "/api/v1/runs",
        headers={"X-Operator-Role": "operator"},
    )
    assert list_res.status_code == 200
    runs_list = list_res.json()
    assert any(r["run_id"] == run_id for r in runs_list)

    detail_res = client.get(
        f"/api/v1/runs/{run_id}",
        headers={"X-Operator-Role": "operator"},
    )
    assert detail_res.status_code == 200
    details = detail_res.json()
    assert details["run_id"] == run_id
    assert "timeline" in details


def test_approvals_inbox_and_decision_lifecycle(api_client) -> None:
    client, factory = api_client
    from app.tools.executor import ToolExecutor

    executor = ToolExecutor(factory)
    prop = executor.execute_create_ticket(
        title="Integration test ticket",
        priority="high",
        customer_id="CUST-1001",
        idempotency_key="task015-appr-0001",
    )
    proposal_id = prop.result["proposal_id"]

    inbox = client.get(
        "/api/v1/approvals?status_filter=pending",
        headers={"X-Operator-Role": "operator"},
    )
    assert inbox.status_code == 200
    pending_list = inbox.json()
    assert any(p["id"] == proposal_id for p in pending_list)

    approve_res = client.post(
        f"/api/v1/approvals/{proposal_id}/approve",
        headers={"X-Operator-Role": "operator"},
        json={"reviewer": "integration-tester"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"


def test_unauthorized_access_blocked(api_client) -> None:
    client, _ = api_client
    res = client.get("/api/v1/runs")
    assert res.status_code == 403

    res2 = client.post(
        "/api/v1/runs",
        json={"user_request": "test"},
    )
    assert res2.status_code == 403
