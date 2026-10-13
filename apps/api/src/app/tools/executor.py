from __future__ import annotations

import json
from typing import Any

from app.db.repositories import (
    create_approval_request,
    get_customer,
    get_order,
)
from app.db.schemas import CustomerSummary, DocumentSummary, OrderSummary
from app.models.contracts import ErrorCategory, ToolCallStatus, ToolResult


class ToolExecutor:
    def __init__(
        self,
        session_factory,
        max_operand_abs: float = 1_000_000_000,  # 1e9 — guards runaway arithmetic
        max_result_abs: float = 10_000_000_000_000,  # 1e13 — before reporting overflow
    ) -> None:
        self.session_factory = session_factory
        self._max_operand_abs = max_operand_abs
        self._max_result_abs = max_result_abs

    def ping(self) -> None:
        with self.session_factory() as session:
            from sqlalchemy import select

            from app.db import models

            session.scalar(select(models.Document.id).limit(1))

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
                error=f"Database error: {str(e)}",
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

    def execute_search_documents(self, query: str) -> ToolResult:
        try:
            trimmed = query.strip()
            if not trimmed:
                return ToolResult(
                    tool_name="search_documents",
                    status=ToolCallStatus.ERROR,
                    error="query must be 1-500 characters",
                    error_category=ErrorCategory.VALIDATION_ERROR,
                )
            with self.session_factory() as session:
                from sqlalchemy import select

                from app.db import models

                pattern = f"%{trimmed.lower()}%"
                # Deterministic LIKE search (no vector DB; simple portable search)
                candidates = session.scalars(
                    select(models.Document).where(
                        models.Document.title.ilike(pattern)
                        | models.Document.content.ilike(pattern)
                        | models.Document.tags.ilike(pattern)
                    )
                ).all()
                # Also try per-token fallback so multi-word queries like "refund policy"
                # match docs whose words appear non-contiguously (e.g. "Refunds ... policy").
                if not candidates:
                    tokens = [t for t in trimmed.lower().split() if t.strip()]
                    if tokens:
                        token_clauses = []
                        for tok in tokens:
                            pat = f"%{tok}%"
                            token_clauses.append(
                                models.Document.title.ilike(pat)
                                | models.Document.content.ilike(pat)
                                | models.Document.tags.ilike(pat)
                            )
                        from sqlalchemy import or_

                        # OR across documents that match any token; rank prefers docs
                        # that match more tokens
                        candidates = session.scalars(
                            select(models.Document).where(or_(*token_clauses))
                        ).all()
                ranked = sorted(
                    candidates,
                    key=lambda d: (
                        0 if trimmed.lower() in d.title.lower() else 1,
                        0 if trimmed.lower() in d.tags.lower() else 1,
                        len(d.content),
                        d.source_id,
                    ),
                )
                hits: list[dict[str, Any]] = []
                for doc in ranked[:5]:
                    text = doc.content
                    # Deterministic excerpt: first match window, or head
                    lower = text.lower()
                    pos = lower.find(trimmed.lower())
                    if pos >= 0:
                        start = max(0, pos - 40)
                        excerpt = text[start : start + 180].strip()
                    else:
                        excerpt = text[:180].strip()
                    hits.append(
                        {
                            "source_id": doc.source_id,
                            "title": doc.title,
                            "excerpt": excerpt,
                            "tags": doc.tags,
                        }
                    )
                # INVARIANT: every source_id is from the database; never invented.
                if not hits:
                    return ToolResult(
                        tool_name="search_documents",
                        status=ToolCallStatus.OK,
                        result={
                            "query": trimmed,
                            "results": [],
                            "count": 0,
                            "message": "No relevant documents found in the corpus for this query.",
                        },
                    )
                return ToolResult(
                    tool_name="search_documents",
                    status=ToolCallStatus.OK,
                    result={"query": trimmed, "results": hits, "count": len(hits)},
                )
        except Exception as e:
            return ToolResult(
                tool_name="search_documents",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.INTERNAL_ERROR,
            )

    def _validate_operand(
        self, value: float, pos: int
    ) -> tuple[float | None, str | None, str | None]:
        # Typed, bounded numeric operand — no eval, no shell, no code.
        if not isinstance(value, int | float):
            return None, f"operand {pos} must be a number", ErrorCategory.VALIDATION_ERROR.value
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            msg = f"operand {pos} cannot be NaN/infinite"
            return None, msg, ErrorCategory.VALIDATION_ERROR.value
        if abs(value) > self._max_operand_abs:
            msg = f"operand {pos} exceeds numeric limit 1e9"
            return None, msg, ErrorCategory.VALIDATION_ERROR.value
        return float(value), None, None

    def execute_calculate(self, operation: str, operands: list[float]) -> ToolResult:  # noqa: C901
        ops: dict[str, str] = {
            "add": "sum of all operands",
            "subtract": "first minus rest",
            "multiply": "product of all operands",
            "divide": "first divided by rest (sequentially)",
            "percent": "percent: (operands[0] / 100) * operands[1]",
            "total_cents": "sum then rounded to cents (mirrors order totals)",
        }
        if operation not in ops:
            return ToolResult(
                tool_name="calculate",
                status=ToolCallStatus.ERROR,
                error=f"Unsupported operation: {operation}. Allowed: {', '.join(sorted(ops))}",
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        if not isinstance(operands, list):
            return ToolResult(
                tool_name="calculate",
                status=ToolCallStatus.ERROR,
                error="operands must be a list of 2-10 numbers",
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        if len(operands) < 2 or len(operands) > 10:
            return ToolResult(
                tool_name="calculate",
                status=ToolCallStatus.ERROR,
                error="operands must contain 2-10 numbers",
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        clean: list[float] = []
        for i, raw in enumerate(operands):
            val, err, _ = self._validate_operand(raw, i)
            if err is not None:
                return ToolResult(
                    tool_name="calculate",
                    status=ToolCallStatus.ERROR,
                    error=err,
                    error_category=ErrorCategory.VALIDATION_ERROR,
                )
            clean.append(val or 0.0)
        try:
            if operation == "add":
                result = sum(clean)
            elif operation == "subtract":
                result = clean[0] - sum(clean[1:])
            elif operation == "multiply":
                result = 1.0
                for v in clean:
                    result *= v
            elif operation == "divide":
                result = clean[0]
                for v in clean[1:]:
                    if v == 0:
                        return ToolResult(
                            tool_name="calculate",
                            status=ToolCallStatus.ERROR,
                            error="Division by zero",
                            error_category=ErrorCategory.VALIDATION_ERROR,
                        )
                    result /= v
            elif operation == "percent":
                if len(clean) != 2:
                    return ToolResult(
                        tool_name="calculate",
                        status=ToolCallStatus.ERROR,
                        error="percent requires exactly 2 operands (value, pct)",
                        error_category=ErrorCategory.VALIDATION_ERROR,
                    )
                result = (clean[0] / 100.0) * clean[1]
            elif operation == "total_cents":
                result = round(sum(clean) * 100) / 100.0
            else:
                return ToolResult(
                    tool_name="calculate",
                    status=ToolCallStatus.ERROR,
                    error=f"Unsupported operation: {operation}",
                    error_category=ErrorCategory.VALIDATION_ERROR,
                )
        except OverflowError:
            return ToolResult(
                tool_name="calculate",
                status=ToolCallStatus.ERROR,
                error="Numeric overflow",
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        if abs(result) > self._max_result_abs or (
            isinstance(result, float)
            and (result != result or result in (float("inf"), float("-inf")))
        ):
            return ToolResult(
                tool_name="calculate",
                status=ToolCallStatus.ERROR,
                error="Result exceeds numeric limits",
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        return ToolResult(
            tool_name="calculate",
            status=ToolCallStatus.OK,
            result={"operation": operation, "operands": clean, "result": result},
        )

    # ------------------------------------------------------------------
    # TASK-006: action *proposal* tools. These persist a durable pending
    # approval request and perform NO side effect. Execution lives behind
    # the later approval service, which is the only caller of the mocked
    # adapters in MockActionExecutor.
    # ------------------------------------------------------------------

    def execute_create_ticket(
        self,
        title: str,
        priority: str,
        customer_id: str,
        description: str = "",
        idempotency_key: str = "",
        requesting_run_id: str | None = None,
    ) -> ToolResult:
        try:
            with self.session_factory() as session, session.begin():
                customer = get_customer(session, customer_id)
                if customer is None:
                    return ToolResult(
                        tool_name="create_ticket",
                        status=ToolCallStatus.ERROR,
                        error=f"Customer not found: {customer_id}",
                        error_category=ErrorCategory.NOT_FOUND,
                    )
                action_reference = f"ticket-draft:{customer_id}"
                payload = {
                    "title": title,
                    "priority": priority,
                    "customer_id": customer_id,
                    "description": description,
                }
                record, created = create_approval_request(
                    session,
                    action_type="create_ticket",
                    action_reference=action_reference,
                    arguments_json=json.dumps(payload, sort_keys=True),
                    idempotency_key=idempotency_key,
                    requesting_run_id=requesting_run_id,
                )
                if not created:
                    return ToolResult(
                        tool_name="create_ticket",
                        status=ToolCallStatus.SKIPPED,
                        result={
                            "proposal_id": str(record.id),
                            "status": record.status,
                            "duplicate": True,
                        },
                    )
                return ToolResult(
                    tool_name="create_ticket",
                    status=ToolCallStatus.WAITING_APPROVAL,
                    result={
                        "proposal_id": str(record.id),
                        "action_type": record.action_type,
                        "status": record.status,
                        "title": title,
                        "priority": priority,
                        "customer_id": customer_id,
                    },
                )
        except ValueError as e:
            return ToolResult(
                tool_name="create_ticket",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        except Exception as e:
            return ToolResult(
                tool_name="create_ticket",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.INTERNAL_ERROR,
            )

    def execute_send_report(
        self,
        title: str,
        destination: str = "mock",
        payload_json: str = "{}",
        idempotency_key: str = "",
        requesting_run_id: str | None = None,
    ) -> ToolResult:
        try:
            try:
                json.loads(payload_json)
            except json.JSONDecodeError:
                return ToolResult(
                    tool_name="send_report",
                    status=ToolCallStatus.ERROR,
                    error="payload_json must be valid JSON",
                    error_category=ErrorCategory.VALIDATION_ERROR,
                )
            if destination != "mock":
                return ToolResult(
                    tool_name="send_report",
                    status=ToolCallStatus.ERROR,
                    error="Only mock delivery is supported; no live delivery exists",
                    error_category=ErrorCategory.VALIDATION_ERROR,
                )
            with self.session_factory() as session, session.begin():
                action_reference = f"report-draft:{title[:48]}"
                record, created = create_approval_request(
                    session,
                    action_type="send_report",
                    action_reference=action_reference,
                    arguments_json=payload_json,
                    idempotency_key=idempotency_key,
                    requesting_run_id=requesting_run_id,
                )
                if not created:
                    return ToolResult(
                        tool_name="send_report",
                        status=ToolCallStatus.SKIPPED,
                        result={
                            "proposal_id": str(record.id),
                            "status": record.status,
                            "duplicate": True,
                        },
                    )
                return ToolResult(
                    tool_name="send_report",
                    status=ToolCallStatus.WAITING_APPROVAL,
                    result={
                        "proposal_id": str(record.id),
                        "action_type": record.action_type,
                        "status": record.status,
                        "title": title,
                        "destination": destination,
                    },
                )
        except ValueError as e:
            return ToolResult(
                tool_name="send_report",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.VALIDATION_ERROR,
            )
        except Exception as e:
            return ToolResult(
                tool_name="send_report",
                status=ToolCallStatus.ERROR,
                error=str(e),
                error_category=ErrorCategory.INTERNAL_ERROR,
            )
