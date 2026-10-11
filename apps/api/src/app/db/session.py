from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def create_sync_engine(url: str | None = None) -> Engine:
    database_url = url or get_settings().database_url.get_secret_value()
    connect_args: dict[str, object] = {}
    if database_url.startswith("postgresql"):
        connect_args = {"connect_timeout": 10}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def ping_ready(engine: Engine | None = None, timeout_seconds: float = 5.0) -> bool:
    target = engine or create_sync_engine()
    try:
        with target.connect() as connection:
            connection.execution_options(timeout=timeout_seconds)
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
    except Exception:  # noqa: BLE001 - readiness probe must never raise
        return False
