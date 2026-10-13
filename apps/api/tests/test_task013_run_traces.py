from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db.models import AgentRun, ToolEvent  # noqa: E402
from app.main import app  # noqa: E402
from tests.conftest import make_seeded_sqlite_session_factory  # noqa: E402


@pytest.fixture
def client_and_factory():
    factory = make_seeded_sqlite_session_factory()
    from app.api.v1 import runs

    def _override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[runs.get_db_session] = _override_session
    client = TestClient(app)
    yield client, factory
    app.dependency_overrides.clear()


def test_list_runs_pagination_and_filtering(client_and_factory) -> None:
    client, factory = client_and_factory
    run_id_1 = str(uuid.uuid4())
    run_id_2 = str(uuid.uuid4())

    with factory() as session:
        r1 = AgentRun(
            run_id=run_id_1,
            thread_id=str(uuid.uuid4()),
            request_preview="Lookup customer",
            status="succeeded",
            model_label="gpt oss 120b",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        r2 = AgentRun(
            run_id=run_id_2,
            thread_id=str(uuid.uuid4()),
            request_preview="Get order",
            status="failed",
            model_label="gpt-4o",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        session.add_all([r1, r2])
        session.commit()

    # List all without filter
    res = client.get("/api/v1/runs", headers={"X-Operator-Role": "operator"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2

    # Filter by status
    res_failed = client.get("/api/v1/runs?status=failed", headers={"X-Operator-Role": "operator"})
    assert res_failed.status_code == 200
    failed_data = res_failed.json()
    assert all(r["status"] == "failed" for r in failed_data)

    # Filter by model label
    res_model = client.get(
        "/api/v1/runs?model_label=gpt%20oss%20120b",
        headers={"X-Operator-Role": "operator"},
    )
    assert res_model.status_code == 200
    model_data = res_model.json()
    assert all(r["model_label"] == "gpt oss 120b" for r in model_data)


def test_get_run_details_and_trace_ordering(client_and_factory) -> None:
    client, factory = client_and_factory
    run_id = str(uuid.uuid4())

    with factory() as session:
        run = AgentRun(
            run_id=run_id,
            thread_id=str(uuid.uuid4()),
            request_preview="Complex workflow",
            status="succeeded",
            model_label="gpt oss 120b",
            final_answer="Done successfully.",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        session.add(run)
        session.commit()

        # Add chronological tool events
        e1 = ToolEvent(
            run_id=run_id,
            sequence=1,
            stage="planning",
            tool_name="get_customer",
            status="ok",
            duration_ms=120,
            detail_summary="Fetched CUST-1001",
        )
        e2 = ToolEvent(
            run_id=run_id,
            sequence=2,
            stage="dispatch",
            tool_name="calculate",
            status="ok",
            duration_ms=45,
            detail_summary="Calculated sum",
        )
        session.add_all([e1, e2])
        session.commit()

    res = client.get(f"/api/v1/runs/{run_id}", headers={"X-Operator-Role": "operator"})
    assert res.status_code == 200
    details = res.json()
    assert details["run_id"] == run_id
    assert details["tool_call_count"] == 2
    timeline = details["timeline"]
    assert len(timeline) == 2
    assert timeline[0]["sequence"] == 1
    assert timeline[0]["tool_name"] == "get_customer"
    assert timeline[1]["sequence"] == 2
    assert timeline[1]["tool_name"] == "calculate"


def test_get_run_not_found(client_and_factory) -> None:
    client, _ = client_and_factory
    res = client.get("/api/v1/runs/nonexistent-run-id", headers={"X-Operator-Role": "operator"})
    assert res.status_code == 404
