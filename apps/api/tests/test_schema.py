from __future__ import annotations

import os
import sys

import pytest
import sqlalchemy as sa
from sqlalchemy import select

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db import models, repositories  # noqa: E402
from app.db.models import Base  # noqa: E402
from tests.conftest import make_sqlite_session_factory  # noqa: E402


def _sqlite_session():
    return make_sqlite_session_factory()()


def test_table_names_and_columns_match_architecture() -> None:
    table_names = set(Base.metadata.tables)
    expected = {
        "customers",
        "orders",
        "documents",
        "tickets",
        "report_jobs",
        "approval_requests",
        "agent_runs",
        "tool_events",
        "evaluation_runs",
        "evaluation_case_results",
    }
    assert expected <= table_names

    customers = Base.metadata.tables["customers"]
    assert {column.name for column in customers.columns} >= {
        "id",
        "customer_id",
        "display_name",
        "email",
        "tier",
        "status",
        "created_at",
        "updated_at",
    }
    approvals = Base.metadata.tables["approval_requests"]
    assert {column.name for column in approvals.columns} >= {
        "id",
        "action_type",
        "action_reference",
        "arguments_json",
        "requesting_run_id",
        "status",
        "reviewer",
        "decided_at",
        "idempotency_key",
        "expires_at",
        "created_at",
        "updated_at",
    }


def test_unique_business_keys_are_enforced() -> None:
    for table_name, column in [
        ("customers", "customer_id"),
        ("orders", "order_id"),
        ("documents", "source_id"),
        ("tickets", "reference"),
        ("report_jobs", "reference"),
        ("approval_requests", "idempotency_key"),
        ("agent_runs", "run_id"),
    ]:
        column_obj = Base.metadata.tables[table_name].columns[column]
        assert column_obj.unique is True, f"{table_name}.{column} must be unique"


def test_approval_status_values_are_constrained() -> None:
    constraint = next(
        c
        for c in Base.metadata.tables["approval_requests"].constraints
        if isinstance(c, sa.CheckConstraint) and c.name == "ck_approval_requests_status"
    )
    sql = str(constraint.sqltext)
    for status in ("pending", "approved", "rejected", "expired"):
        assert status in sql


def test_order_lookup_and_not_found() -> None:
    session = _sqlite_session()
    try:
        from scripts.seed import seed

        counts = seed(session)
        assert counts["orders"] == 6
        order = repositories.get_order(session, "ORD-5001")
        assert order is not None
        assert order.order_id == "ORD-5001"
        assert order.customer_id == "CUST-1001"
        assert order.status == "delivered"
        assert repositories.get_order(session, "ORD-9999") is None
    finally:
        session.close()


def test_seed_is_idempotent() -> None:
    session = _sqlite_session()
    try:
        from scripts.seed import seed, upsert_customer

        first = seed(session)
        second = seed(session)
        assert first == second == {"customers": 5, "orders": 6, "documents": 5}
        customers = session.scalars(select(models.Customer)).all()
        assert len(customers) == 5
        orders = session.scalars(select(models.SyntheticOrder)).all()
        assert len(orders) == 6
        documents = session.scalars(select(models.Document)).all()
        assert len(documents) == 5
        upsert_customer(
            session,
            {
                "customer_id": "CUST-1001",
                "display_name": "Acme Manufacturing Updated",
                "email": "ops@acme-manufacturing.example",
                "tier": "enterprise",
                "status": "active",
            },
        )
        assert len(session.scalars(select(models.Customer)).all()) == 5
        assert repositories.get_customer(session, "CUST-1001").display_name == (  # type: ignore[union-attr]
            "Acme Manufacturing Updated"
        )
    finally:
        session.close()


def test_approval_idempotency_and_decision_rules() -> None:
    session = _sqlite_session()
    try:
        with pytest.raises(ValueError):
            repositories.create_approval_request(
                session,
                action_type="delete_everything",
                action_reference="ACT-1",
                arguments_json="{}",
                idempotency_key="key-1",
            )
        first, created = repositories.create_approval_request(
            session,
            action_type="create_ticket",
            action_reference="TICKET-1",
            arguments_json='{"title": "x"}',
            idempotency_key="key-abc",
        )
        assert created is True
        assert first.status == "pending"
        second, created_again = repositories.create_approval_request(
            session,
            action_type="create_ticket",
            action_reference="TICKET-1",
            arguments_json='{"title": "x"}',
            idempotency_key="key-abc",
        )
        assert created_again is False
        assert second.id == first.id
        rows = session.scalars(select(models.ApprovalRequest)).all()
        assert len(rows) == 1

        with pytest.raises(ValueError):
            repositories.decide_approval(session, str(first.id), decision="maybe", reviewer="op")
        decided = repositories.decide_approval(
            session, str(first.id), decision="approved", reviewer="operator-1"
        )
        assert decided.status == "approved"
        assert decided.reviewer == "operator-1"
        assert decided.decided_at is not None
        with pytest.raises(ValueError, match="already decided"):
            repositories.decide_approval(
                session, str(first.id), decision="rejected", reviewer="operator-2"
            )
    finally:
        session.close()
