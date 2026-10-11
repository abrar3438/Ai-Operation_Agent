from __future__ import annotations

CUSTOMERS = [
    {
        "customer_id": "CUST-1001",
        "display_name": "Acme Manufacturing",
        "email": "ops@acme-manufacturing.example",
        "tier": "enterprise",
        "status": "active",
    },
    {
        "customer_id": "CUST-1002",
        "display_name": "Bluepeak Logistics",
        "email": "support@bluepeak-logistics.example",
        "tier": "business",
        "status": "active",
    },
    {
        "customer_id": "CUST-1003",
        "display_name": "Cedar Clinic Group",
        "email": "admin@cedar-clinic.example",
        "tier": "standard",
        "status": "active",
    },
    {
        "customer_id": "CUST-1004",
        "display_name": "Dunmore Retail Co",
        "email": "hello@dunmore-retail.example",
        "tier": "standard",
        "status": "inactive",
    },
    {
        "customer_id": "CUST-1005",
        "display_name": "Elm Street Foods",
        "email": "team@elm-street-foods.example",
        "tier": "business",
        "status": "suspended",
    },
]

ORDERS = [
    {
        "order_id": "ORD-5001",
        "customer_id": "CUST-1001",
        "status": "delivered",
        "total_cents": 125000,
        "currency": "USD",
        "summary": "Quarterly sensor calibration kit",
    },
    {
        "order_id": "ORD-5002",
        "customer_id": "CUST-1001",
        "status": "shipped",
        "total_cents": 84200,
        "currency": "USD",
        "summary": "Replacement conveyor rollers",
    },
    {
        "order_id": "ORD-5003",
        "customer_id": "CUST-1002",
        "status": "paid",
        "total_cents": 21050,
        "currency": "USD",
        "summary": "Fleet tracking device bundle",
    },
    {
        "order_id": "ORD-5004",
        "customer_id": "CUST-1003",
        "status": "pending",
        "total_cents": 9999,
        "currency": "USD",
        "summary": "Waiting-room display stands",
    },
    {
        "order_id": "ORD-5005",
        "customer_id": "CUST-1002",
        "status": "cancelled",
        "total_cents": 45000,
        "currency": "USD",
        "summary": "Cancelled cold-chain upgrade",
    },
    {
        "order_id": "ORD-5006",
        "customer_id": "CUST-1005",
        "status": "refunded",
        "total_cents": 12300,
        "currency": "USD",
        "summary": "Refunded packaging trial",
    },
]

DOCUMENTS = [
    {
        "source_id": "DOC-REFUND-POLICY",
        "title": "Refund Handling Policy",
        "content": (
            "Refunds are issued to the original payment method within 10 business days "
            "after a return is inspected. Orders marked refunded include the refund memo "
            "in the order summary. Operators must cite this policy when answering refund questions."
        ),
        "tags": "refund,policy,billing",
    },
    {
        "source_id": "DOC-SHIPPING-SLA",
        "title": "Shipping SLA Overview",
        "content": (
            "Standard shipments arrive in 3-5 business days. Shipped orders expose a tracking "
            "reference in the order summary. Delivered orders are considered complete unless a "
            "separate ticket is open."
        ),
        "tags": "shipping,sla,delivery",
    },
    {
        "source_id": "DOC-TICKET-ESCALATION",
        "title": "Ticket Escalation Guide",
        "content": (
            "Escalate a ticket to urgent priority when an enterprise customer reports a "
            "production outage. Normal tickets stay at normal priority. Every escalation must "
            "be proposed as a ticket action and approved before it is recorded."
        ),
        "tags": "ticket,escalation,support",
    },
    {
        "source_id": "DOC-REPORT-CADENCE",
        "title": "Weekly Operations Report Cadence",
        "content": (
            "Operations reports are drafted weekly and sent only after reviewer approval. "
            "Drafts list open tickets, delayed shipments, and refund totals. Mock delivery is "
            "used for demonstrations."
        ),
        "tags": "report,operations,cadence",
    },
    {
        "source_id": "DOC-APPROVAL-POLICY",
        "title": "Action Approval Policy",
        "content": (
            "Ticket creation and report sending always require explicit human approval. "
            "A model request creates a pending proposal only. Rejections terminate the action "
            "without side effects, and approvals are idempotent."
        ),
        "tags": "approval,policy,safety",
    },
]
