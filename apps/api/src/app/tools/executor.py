from __future__ import annotations

from typing import Any

from app.db.repositories import (
    get_customer,
    get_order,
)
from app.db.schemas import CustomerSummary, DocumentSummary, OrderSummary
from app.models.contracts import ErrorCategory, ToolCallStatus, ToolResult


class ToolExecutor:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def execute_get_customer(self, customer_id: str) -> ToolResult:
        try:
            with self.session_factory() as session:
                customer = get_customer(session, customer_id)
                if customer is None:
                    return ToolResult(
                        tool_name="get_customer",
                        status=ToolCallStatus.ERROR,
                        error=f"Customer not found: {customer_id}",
                        error_category=ErrorCategory.NOT_FOUND,
                    )
                summary = CustomerSummary(
                    customer_id=customer.customer_id,
                    display_name=customer.display_name,
                    tier=customer.tier,
                    status=customer.status,
                )
                return ToolResult(
                    tool_name="get_customer",
                    status=ToolCallStatus.OK,
                    result=summary.model_dump(),
                )
        except Exception as e:
            return ToolResult(
                tool_name="get_customer",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.INTERNAL_ERROR,
            )

    def execute_get_order(self, order_id: str) -> ToolResult:
        try:
            with self.session_factory() as session:
                order = get_order(session, order_id)
                if order is None:
                    return ToolResult(
                        tool_name="get_order",
                        status=ToolCallStatus.ERROR,
                        error=f"Order not found: {order_id}",
                        error_category=ErrorCategory.NOT_FOUND,
                    )
                summary = OrderSummary(
                    order_id=order.order_id,
                    customer_id=order.customer_id,
                    status=order.status,
                    total_cents=order.total_cents,
                    currency=order.currency,
                    summary=order.summary,
                )
                return ToolResult(
                    tool_name="get_order",
                    status=ToolCallStatus.OK,
                    result=summary.model_dump(),
                )
        except Exception as e:
            return ToolResult(
                tool_name="get_order",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.INTERNAL_ERROR,
            )

    def execute_search_database(self, entity: str, filters: dict[str, Any]) -> ToolResult:
        try:
            if entity == "customers":
                allowed_filters = {"customer_id", "display_name", "email", "tier", "status"}
                invalid = set(filters.keys()) - allowed_filters
                if invalid:
                    return ToolResult(
                        tool_name="search_database",
                        status=ToolCallStatus.ERROR,
                        error=f"Unknown filters for customers: {invalid}",
                        error_category=ErrorCategory.VALIDATION_ERROR,
                    )
                with self.session_factory() as session:
                    from sqlalchemy import select

                    from app.db import models

                    query = select(models.Customer)
                    if "customer_id" in filters:
                        query = query.where(models.Customer.customer_id == filters["customer_id"])
                    if "display_name" in filters:
                        query = query.where(
                            models.Customer.display_name.ilike(f"%{filters['display_name']}%")
                        )
                    if "email" in filters:
                        query = query.where(models.Customer.email.ilike(f"%{filters['email']}%"))
                    if "tier" in filters:
                        query = query.where(models.Customer.tier == filters["tier"])
                    if "status" in filters:
                        query = query.where(models.Customer.status == filters["status"])

                    customers = session.scalars(query.limit(50)).all()
                    results = [
                        CustomerSummary(
                            customer_id=c.customer_id,
                            display_name=c.display_name,
                            tier=c.tier,
                            status=c.status,
                        ).model_dump()
                        for c in customers
                    ]
                    return ToolResult(
                        tool_name="search_database",
                        status=ToolCallStatus.OK,
                        result={"entity": "customers", "records": results, "count": len(results)},
                    )

            elif entity == "orders":
                allowed_filters = {"order_id", "customer_id", "status", "currency"}
                invalid = set(filters.keys()) - allowed_filters
                if invalid:
                    return ToolResult(
                        tool_name="search_database",
                        status=ToolCallStatus.ERROR,
                        error=f"Unknown filters for orders: {invalid}",
                        error_category=ErrorCategory.VALIDATION_ERROR,
                    )
                with self.session_factory() as session:
                    from sqlalchemy import select

                    from app.db import models

                    query = select(models.SyntheticOrder)
                    if "order_id" in filters:
                        query = query.where(models.SyntheticOrder.order_id == filters["order_id"])
                    if "customer_id" in filters:
                        query = query.where(
                            models.SyntheticOrder.customer_id == filters["customer_id"]
                        )
                    if "status" in filters:
                        query = query.where(models.SyntheticOrder.status == filters["status"])
                    if "currency" in filters:
                        query = query.where(models.SyntheticOrder.currency == filters["currency"])

                    orders = session.scalars(query.limit(50)).all()
                    results = [
                        OrderSummary(
                            order_id=o.order_id,
                            customer_id=o.customer_id,
                            status=o.status,
                            total_cents=o.total_cents,
                            currency=o.currency,
                            summary=o.summary,
                        ).model_dump()
                        for o in orders
                    ]
                    return ToolResult(
                        tool_name="search_database",
                        status=ToolCallStatus.OK,
                        result={"entity": "orders", "records": results, "count": len(results)},
                    )

            elif entity == "documents":
                allowed_filters = {"source_id", "title", "tags"}
                invalid = set(filters.keys()) - allowed_filters
                if invalid:
                    return ToolResult(
                        tool_name="search_database",
                        status=ToolCallStatus.ERROR,
                        error=f"Unknown filters for documents: {invalid}",
                        error_category=ErrorCategory.VALIDATION_ERROR,
                    )
                with self.session_factory() as session:
                    from sqlalchemy import select

                    from app.db import models

                    query = select(models.Document)
                    if "source_id" in filters:
                        query = query.where(models.Document.source_id == filters["source_id"])
                    if "title" in filters:
                        query = query.where(models.Document.title.ilike(f"%{filters['title']}%"))
                    if "tags" in filters:
                        query = query.where(models.Document.tags.ilike(f"%{filters['tags']}%"))

                    documents = session.scalars(query.limit(50)).all()
                    results = [
                        DocumentSummary(
                            source_id=d.source_id,
                            title=d.title,
                            excerpt=d.content[:200] + "..." if len(d.content) > 200 else d.content,
                        ).model_dump()
                        for d in documents
                    ]
                    return ToolResult(
                        tool_name="search_database",
                        status=ToolCallStatus.OK,
                        result={"entity": "documents", "records": results, "count": len(results)},
                    )

            else:
                return ToolResult(
                    tool_name="search_database",
                    status=ToolCallStatus.ERROR,
                    error=f"Unknown entity: {entity}. Allowed: customers, orders, documents",
                    error_category=ErrorCategory.VALIDATION_ERROR,
                )

        except Exception as e:
            return ToolResult(
                tool_name="search_database",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.INTERNAL_ERROR,
            )
