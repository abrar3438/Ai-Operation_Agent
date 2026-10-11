from __future__ import annotations

import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings

MAX_ATTEMPTS = 30
DELAY_SECONDS = 2.0


def wait_for_database() -> None:
    url = get_settings().database_url.get_secret_value()
    engine = create_engine(url, pool_pre_ping=True)
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print(f"[wait_for_deps] database is ready after {attempt} attempt(s)")
            return
        except SQLAlchemyError as exc:
            last_error = exc
            print(f"[wait_for_deps] database not ready (attempt {attempt}/{MAX_ATTEMPTS})")
            time.sleep(DELAY_SECONDS)
    raise SystemExit(f"[wait_for_deps] database not ready: {type(last_error).__name__}")


if __name__ == "__main__":
    wait_for_database()
