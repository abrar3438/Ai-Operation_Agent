from __future__ import annotations

import pytest

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://postgres:postgres@localhost:5433/agentdb",
        redis_url="redis://localhost:6379/0",
        cors_origins=["http://localhost:3000"],
    )


# ---------------------------------------------------------------------------
# Shared SQLite fixture factory used across DB/tool/graph tests. The PostgreSQL
# UUID columns are shimmed once (module import), so :memory: databases are
# per-test isolated while metadata mutation never repeats and never leaks the
# PostgreSQL type into a created SQLite database.
# ---------------------------------------------------------------------------

import sqlalchemy as sa  # noqa: E402
from sqlalchemy.dialects.postgresql import UUID as _PGUUID  # noqa: E402

from app.db.models import Base as _DBBase  # noqa: E402


class _SQLitePostgresUUIDShim(sa.TypeDecorator):  # noqa: N801
    impl = sa.CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):  # type: ignore[no-untyped-def]
        return None if value is None else str(value)

    def process_result_value(self, value, dialect):  # type: ignore[no-untyped-def]
        import uuid

        return None if value is None else uuid.UUID(str(value))


_SHIMMED_TABLES: set[str] = set()


def ensure_sqlite_uuid_shim() -> None:
    for table in _DBBase.metadata.tables.values():
        if table.name in _SHIMMED_TABLES:
            continue
        for column in list(table.columns):
            current = column.type
            if isinstance(current, _PGUUID) and not isinstance(current, _SQLitePostgresUUIDShim):
                column.type = _SQLitePostgresUUIDShim()
        _SHIMMED_TABLES.add(table.name)


ensure_sqlite_uuid_shim()


def make_sqlite_session_factory():  # type: ignore[no-untyped-def]
    import tempfile

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    engine = create_engine(f"sqlite:///{db_file.name}")
    _DBBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    factory._sqlite_tmpfile = db_file.name  # type: ignore[attr-defined]
    return factory


def make_seeded_sqlite_session_factory():  # type: ignore[no-untyped-def]
    from scripts.seed import seed  # type: ignore[import-untyped]

    factory = make_sqlite_session_factory()
    with factory() as session:
        seed(session)
        session.commit()
    return factory
