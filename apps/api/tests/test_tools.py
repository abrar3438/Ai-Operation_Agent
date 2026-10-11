from __future__ import annotations

import os
import sys
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# Add project root to path for importing app modules
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db.models import Base as DBBase  # noqa: E402
from app.tools.executor import ToolExecutor  # noqa: E402


class _PGUUIDShim(sa.TypeDecorator):
    impl = sa.CHAR(36)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any):  # type: ignore[no-untyped-def]
        return None if value is None else str(value)

    def process_result_value(self, value: Any, dialect: Any):  # type: ignore[no-untyped-def]
        import uuid

        return None if value is None else uuid.UUID(str(value))


def _sqlite_session():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    for table in DBBase.metadata.tables.values():
        for column in list(table.columns):
            if isinstance(column.type, PGUUID):
                column.type = _PGUUIDShim()
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection: Any, _record: Any):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    DBBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_executor(factory: Any) -> ToolExecutor:
    return ToolExecutor(factory)


# ---------------------------------------------------------------------------
# get_customer
# ---------------------------------------------------------------------------


def test_get_customer_returns_synthetic_record() -> None:
    factory = _sqlite_session()
    from scripts.seed import seed  # type: ignore[import-untyped]

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_get_customer("CUST-1001")
    assert result.status.value == "ok"
    assert result.result is not None
    assert result.result["customer_id"] == "CUST-1001"
    assert "display_name" in result.result


def test_get_customer_not_found() -> None:
    factory = _sqlite_session()
    from scripts.seed import seed

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_get_customer("CUST-9999")
    assert result.status.value == "error"
    assert result.error_category.value == "not_found"


def test_get_customer_empty_id_is_error() -> None:
    factory = _sqlite_session()
    executor = make_executor(factory)
    result = executor.execute_get_customer("")
    # empty customer_id not found is treated as not_found
    assert result.status.value == "error"


# ---------------------------------------------------------------------------
# get_order
# ---------------------------------------------------------------------------


def test_get_order_returns_synthetic_record() -> None:
    factory = _sqlite_session()
    from scripts.seed import seed

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_get_order("ORD-5001")
    assert result.status.value == "ok"
    assert result.result is not None
    assert result.result["order_id"] == "ORD-5001"
    assert result.result["customer_id"] == "CUST-1001"


def test_get_order_not_found() -> None:
    factory = _sqlite_session()
    from scripts.seed import seed

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_get_order("ORD-9999")
    assert result.status.value == "error"
    assert result.error_category.value == "not_found"


# ---------------------------------------------------------------------------
# search_database
# ---------------------------------------------------------------------------


def test_search_database_customers_by_tier() -> None:
    factory = _sqlite_session()
    from scripts.seed import seed

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_search_database("customers", {"tier": "enterprise"})
    assert result.status.value == "ok"
    assert result.result is not None
    assert result.result["entity"] == "customers"
    assert any(r["customer_id"] == "CUST-1001" for r in result.result["records"])


def test_search_database_orders_by_customer_id() -> None:
    factory = _sqlite_session()
    from scripts.seed import seed

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_search_database("orders", {"customer_id": "CUST-1001"})
    assert result.status.value == "ok"
    assert all(r["customer_id"] == "CUST-1001" for r in result.result["records"])


def test_search_database_documents_by_source_id() -> None:
    factory = _sqlite_session()
    from scripts.seed import seed

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_search_database("documents", {"source_id": "DOC-REFUND-POLICY"})
    assert result.status.value == "ok"
    assert len(result.result["records"]) == 1
    assert result.result["records"][0]["source_id"] == "DOC-REFUND-POLICY"


def test_search_database_unknown_entity_is_validation_error() -> None:
    factory = _sqlite_session()
    executor = make_executor(factory)
    result = executor.execute_search_database("admin_users", {})
    assert result.status.value == "error"
    assert result.error_category.value == "validation_error"
    assert "Unknown entity" in result.error


def test_search_database_unknown_filter_is_validation_error() -> None:
    factory = _sqlite_session()
    executor = make_executor(factory)
    result = executor.execute_search_database("customers", {"hacked_column": "value"})
    assert result.status.value == "error"
    assert result.error_category.value == "validation_error"
    assert "Unknown filters" in result.error


def test_search_database_no_injection_through_filter_values() -> None:
    """Filter values must never create SQL that drops tables."""
    factory = _sqlite_session()
    from scripts.seed import seed

    with factory() as s:
        seed(s)
        s.commit()
    executor = make_executor(factory)
    result = executor.execute_search_database(
        "customers",
        {"display_name": "'; DROP TABLE customers; --"},
    )
    # Should be treated as a literal LIKE search, not as executed SQL.
    assert result.status.value == "ok"
    assert result.result["count"] == 0
    # Table must still exist.
    factory2 = factory
    executor2 = make_executor(factory2)
    result2 = executor2.execute_search_database("customers", {"customer_id": "CUST-1001"})
    assert result2.result["count"] == 1


def test_search_database_unknown_filter_for_orders() -> None:
    factory = _sqlite_session()
    executor = make_executor(factory)
    result = executor.execute_search_database("orders", {"unknown_col": "x"})
    assert result.error_category.value == "validation_error"


def test_search_database_unknown_filter_for_documents() -> None:
    factory = _sqlite_session()
    executor = make_executor(factory)
    result = executor.execute_search_database("documents", {"content": "x"})
    assert result.error_category.value == "validation_error"


# ---------------------------------------------------------------------------
# Model adapter / fake adapter / contracts
# ---------------------------------------------------------------------------


def test_fake_adapter_returns_configured_response() -> None:
    import asyncio

    from app.models.adapter import ModelResponse
    from app.models.fake_adapter import FakeModelAdapter

    async def _run() -> None:
        adapter = FakeModelAdapter(responses=[ModelResponse(content="hello")])
        from app.models.adapter import ModelMessage

        result = await adapter.chat([ModelMessage(role="user", content="hi")])
        assert result.content == "hello"
        assert adapter.call_count == 1

    asyncio.run(_run())


def test_fake_adapter_invalid_tool_name_is_caught_by_validation() -> None:
    from pydantic import ValidationError

    from app.models.contracts import ToolCallRequest

    with pytest.raises(ValidationError):
        ToolCallRequest(tool_name="drop_table", arguments={}, idempotency_key="k" * 12)
