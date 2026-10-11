from __future__ import annotations

import argparse
import sys
import time

sys.path.insert(0, "src")

from alembic import command as alembic_command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import models, seed_data  # noqa: E402
from app.db.repositories import READ_ONLY_CUSTOMER_STATUSES, READ_ONLY_ORDER_STATUSES  # noqa: E402
from app.db.session import create_sync_engine, get_session_factory  # noqa: E402


def upsert_customer(session: Session, payload: dict) -> models.Customer:
    if payload["status"] not in READ_ONLY_CUSTOMER_STATUSES:
        raise ValueError(f"Invalid customer status: {payload['status']!r}")
    row = session.scalar(
        select(models.Customer).where(models.Customer.customer_id == payload["customer_id"])
    )
    if row is None:
        row = models.Customer(**payload)
        session.add(row)
    else:
        for key, value in payload.items():
            setattr(row, key, value)
    return row


def upsert_order(session: Session, payload: dict) -> models.SyntheticOrder:
    if payload["status"] not in READ_ONLY_ORDER_STATUSES:
        raise ValueError(f"Invalid order status: {payload['status']!r}")
    row = session.scalar(
        select(models.SyntheticOrder).where(models.SyntheticOrder.order_id == payload["order_id"])
    )
    if row is None:
        row = models.SyntheticOrder(**payload)
        session.add(row)
    else:
        for key, value in payload.items():
            setattr(row, key, value)
    return row


def upsert_document(session: Session, payload: dict) -> models.Document:
    row = session.scalar(
        select(models.Document).where(models.Document.source_id == payload["source_id"])
    )
    if row is None:
        row = models.Document(**payload)
        session.add(row)
    else:
        for key, value in payload.items():
            setattr(row, key, value)
    return row


def wait_for_database(url: str, attempts: int = 30, delay_seconds: float = 2.0) -> None:
    engine = create_sync_engine(url)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except SQLAlchemyError as exc:
            last_error = exc
            print(f"[seed] database not ready (attempt {attempt}/{attempts})")
            time.sleep(delay_seconds)
    raise SystemExit(f"[seed] database not ready: {type(last_error).__name__}")


def apply_migrations(url: str) -> None:
    config = AlembicConfig("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    alembic_command.upgrade(config, "head")


def seed(session: Session) -> dict[str, int]:
    counts = {"customers": 0, "orders": 0, "documents": 0}
    for payload in seed_data.CUSTOMERS:
        upsert_customer(session, dict(payload))
        counts["customers"] += 1
    for payload in seed_data.ORDERS:
        upsert_order(session, dict(payload))
        counts["orders"] += 1
    for payload in seed_data.DOCUMENTS:
        upsert_document(session, dict(payload))
        counts["documents"] += 1
    session.flush()
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed the development database with synthetic demo data (idempotent)."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL (defaults to Settings.database_url).",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    url = args.database_url or settings.database_url.get_secret_value()
    wait_for_database(url)
    apply_migrations(url)
    engine = create_sync_engine(url)
    factory = get_session_factory(engine)
    with factory() as session, session.begin():
        counts = seed(session)
    print(
        "Seeded synthetic data: "
        f"{counts['customers']} customers, "
        f"{counts['orders']} orders, "
        f"{counts['documents']} documents."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
