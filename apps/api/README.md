# AI Operations Agent API

TASK-001 foundation scaffold. No agent tools, graph logic, or operational features are implemented yet. See the repository `README.md`, `TASKS.md`, and `docs/ARCHITECTURE.md` for scope.

## Layout

```text
apps/api/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/app/
│   ├── main.py            # FastAPI app factory and router wiring
│   ├── config.py          # Typed environment configuration (pydantic-settings)
│   ├── logging.py         # Structured logging with redaction
│   ├── api/v1/health.py   # /health/live and /health/ready
│   ├── db/session.py      # SQLAlchemy engine/session + ping_ready
│   └── cache/redis_client.py  # Redis client + ping_ready
└── tests/
    ├── conftest.py
    ├── test_config.py
    └── test_health.py
```

## Local commands

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Database seed (synthetic, idempotent)

Seeding only touches the development database named in `DATABASE_URL` and never
drops tables. It upserts the bundled synthetic customers, orders, and documents,
so running it twice cannot create duplicates:

```bash
uv run python scripts/seed.py
uv run python scripts/seed.py --database-url "postgresql+psycopg://postgres:postgres@localhost:5433/agentdb"
```

Apply migrations before seeding (the seed command also upgrades first):

```bash
uv run alembic upgrade head
uv run python scripts/seed.py
```

Database configuration follows the project `.env.example` and `docker-compose.yml`. Actual connection values live in `.env`, which is never committed.
