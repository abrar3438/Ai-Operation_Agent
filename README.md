# AI Operations Agent

> A production-minded operations assistant that uses a controlled tool-calling workflow to look up customer/order information, search knowledge, calculate values, and propose operational actions with human approval.

**Status:** TASK-005 complete — monorepo foundation, action proposal tools, and operational tooling (search/calc). No approval execution, UI, or evaluation runner implemented yet. TASK-003 model adapter and read-only tools are also in place (CraftX provider; see Local development below).

## Why this project exists

Operations teams often switch between customer records, order information, internal documents, calculations, and ticket/report workflows. This project demonstrates how to build an agent that can route work through explicit tools while keeping validation, safety, observability, and evaluation outside the LLM's control.

## Main capabilities

- Tool calling with validated, structured inputs and outputs.
- LangGraph workflow with explicit state, bounded steps, and controlled routing.
- Read-only tools: `get_customer`, `get_order`, `search_database`, `search_documents`, and `calculate`.
- Approval-gated action tools: `create_ticket` and `send_report`.
- Human review queue that can approve or reject proposed actions before they execute.
- Timeouts, bounded retries, input/output validation, fallback behavior, and loop prevention.
- Redis caching for eligible read-only operations only.
- Structured run traces, tool execution logs, and a versioned evaluation set with measurable results.
- Local Docker Compose stack with PostgreSQL, Redis, API, web UI, and pgAdmin for development.

## Planned technology stack

| Layer | Choice |
|---|---|
| Agent orchestration | Python + LangGraph |
| API | FastAPI + Pydantic |
| Model integration | Configurable model adapter; OpenAI-compatible endpoint support for the first adapter |
| Primary database | PostgreSQL + SQLAlchemy + Alembic |
| Graph checkpointing | PostgreSQL-backed LangGraph checkpointer, where supported by the selected LangGraph package version |
| Cache | Redis; cache only approved, deterministic read-only results |
| Frontend | Next.js + TypeScript + Tailwind CSS |
| Testing | pytest; frontend unit/component tests; Playwright end-to-end tests |
| Local services | Docker Compose; pgAdmin for local database inspection |
| Observability | Structured logs, correlation/run IDs, trace and tool-event records; optional external tracing adapter later |

## Architecture at a glance

```mermaid
flowchart TD
    U[Operator] --> W[Next.js Operations Console]
    W --> API[FastAPI API]
    API --> G[LangGraph Agent Workflow]
    G --> M[Configurable Model Adapter]
    G --> T[Validated Tool Registry]
    T --> DB[(PostgreSQL: operational data, approvals, runs)]
    T --> DOC[Document Search Service]
    T --> C[Redis: eligible read cache]
    G --> HITL[Human Approval Checkpoint]
    HITL --> W
    G --> OBS[Structured Events and Traces]
    OBS --> DB
```

## Repository map (TASK-001 implemented)

```text
ai-operations-agent/
├── AGENTS.md
├── README.md
├── TASKS.md
├── .env.example
├── .gitignore
├── .dockerignore
├── docker-compose.yml      # api, web, postgres, redis, pgAdmin (dev-tools profile)
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DESIGN.md
│   ├── RULES.md
│   ├── TEST_PLAN.md
│   ├── SECURITY.md
│   ├── DECISIONS.md
│   ├── MEMORY.md
│   └── TECHNICAL_REFERENCES.md
├── apps/
│   ├── api/       # FastAPI foundation: config, health endpoints, DB/Redis clients, tests, Alembic
│   └── web/       # Next.js operator console scaffold
├── evals/         # Placeholder; versioned fixtures and runner arrive in later tasks
└── infra/         # Reserved; Docker-related configuration if it grows beyond Compose
```

The actual code layout may be refined during setup, but any change must be recorded in `docs/DECISIONS.md` and reflected in this README. The DB readiness script lives at `apps/api/scripts/wait_for_deps.py` so the API image can use it without a runtime infrastructure package.

## Local development (TASK-001 verified)

1. Install Docker Desktop and Git. Install a supported Node.js LTS release and [uv](https://docs.astral.sh/uv/) only if you also want to run services outside Docker.
2. Copy `.env.example` to `.env` and adjust local credentials/model provider settings. Never commit `.env`.
   - **CraftX users:** put the real key in `.env` as
     ```
     LLM_PROVIDER=openai_compatible
     LLM_BASE_URL=https://api.craftx.corecraftsolutions.com/api/v1
     LLM_MODEL=gpt oss 120b
     LLM_API_KEY=your-real-craftx-key
     ```
     `.env.example` may carry `CRAFTX_ENDPOINT`/`CRAFTX_MODEL` as discoverable non-secrets, but the key itself stays server-side only.
3. Start the complete development stack:

   ```bash
   docker compose config        # validate; confirm agent-postgres, 5433:5432, API 8001
   docker compose up --build
   ```

4. Host ports (chosen to avoid the Enterprise RAG stack on `8000`/`5432`):

   | Service | Host URL |
   |---|---|
   | Web console | `http://localhost:3000` |
   | API health | `http://localhost:8001/health/live`, `http://localhost:8001/health/ready` |
   | PostgreSQL | `localhost:5433` (database `agentdb`) |
   | Redis | `localhost:6379` |
   | pgAdmin (local dev only) | `http://localhost:5050` via `docker compose --profile dev-tools up` |

> pgAdmin comes with the `agent-postgres` server pre-registered ("AI Operations Agent (local)", database `agentdb`, restricted to that database). Passwords are never stored in the pre-registration file, so enter `postgres` the first time you connect. Keep the placeholder `PGADMIN_DEFAULT_PASSWORD` replaced in your own `.env`.

5. The API connects inside Compose with `DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/agentdb`. From the Windows host, use `postgresql+psycopg://postgres:postgres@localhost:5433/agentdb`. Never use `localhost` from inside the backend container.
6. Seed synthetic demonstration data using the documented seed command after the first implementation of that command (TASK-002).

Backend checks from `apps/api`: `uv sync`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest`.
Frontend checks from `apps/web`: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build`.

## Development journal — problems faced and what was done

This is an interview-facing record of real, verifiable decisions made during the build. Nothing here depends on prompt wording.

| Problem | What was done | Why it matters |
|---|---|---|
| `LLM_*` vars changed for CraftX mid-project | `.env.example` now uses CraftX non-secrets (`CRAFTX_ENDPOINT`, `CRAFTX_MODEL`, `LLM_BASE_URL` with CraftX base) while the key stays only in git-ignored `.env` as `LLM_API_KEY`. Adapter defaults to the CraftX base URL and `gpt oss 120b` when no explicit `LLM_BASE_URL`/`LLM_MODEL` is set. | API keys never reach the client or Git; the adapter works with CraftX and any other OpenAI-compatible endpoint without code changes or hardcoded URLs. |
| Port collisions with the existing Enterprise RAG stack | API moved to host `8001` (RAG owns `8000`); Postgres to host `5433` (RAG owns `5432`); all host ports localhost-bound; pgAdmin profile-gated (`--profile dev-tools`). | Two Docker projects coexist safely on one machine; no RAG container/volume was modified or removed. |
| `gh` not on the agent's PATH after you authenticated | Created the empty public repo (`Ai-Operation_Agent`) from your own terminal, then only wired the remote (`git remote add origin`). | Keeps auth inside your user session and never pastes a token into agent chat. |
| Host `alembic upgrade head` / `python scripts/seed.py` hangs on Windows | Live DB work runs inside the Compose network (`docker compose run --rm api …`) and seed now runs `alembic upgrade head` first. | Migrations and seeding are reliable and idempotent regardless of shell behavior. |
| Initial `alembic` config hid real failures | Added `connect_timeout`, disabled offline mode, removed `get_current_heads` debug calls, rebuilt the image, and used descriptive migration names. | Real migration errors surface instead of hanging. |
| Test scaffolding assumptions | Kept all test fixtures synthetic (`.example` domains), used `FakeModelAdapter` so no paid-model key is needed, and scoped `search_database` to known entities/filters with bound LIKE queries. | Tests stay deterministic and SQL injection stays impossible from model text. |

## Configuration and external model APIs

Use `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` from environment variables — read server-side by `ModelConfig.from_env()` and the `OpenAICompatibleAdapter` (`httpx` + `Authorization: Bearer …`), never by the frontend or committed config. The task documents never carry CraftX specifics, so treat any `CRAFTX_*` keys as non-secret discovery values only; the real key stays `LLM_API_KEY` in git-ignored `.env` and is never returned in logs or errors.

## Safety guarantees

- The model never receives a general-purpose database connection or unrestricted SQL execution capability.
- Tool names are selected from an allowlisted registry and every tool input is validated server-side.
- `create_ticket` and `send_report` must pause for explicit human approval before any state-changing action executes.
- The default demo integrations use synthetic records and mock delivery. No real email or external ticketing system is contacted by default.
- Runs have a maximum step count, timeouts, bounded retries, and a clear terminal state.
- Secrets, full credentials, and unnecessary sensitive data must not appear in logs or Git.

## Development workflow

Read `AGENTS.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/RULES.md`, `TASKS.md`, `docs/TEST_PLAN.md`, and `docs/SECURITY.md` before implementation. Work one task at a time: **read → understand → plan → implement → test → review → fix → commit → update documentation**. Use vertical slices and do not ask the coding agent to generate the entire application in one prompt.

## Project documentation

- Product goals and acceptance criteria: [`docs/PRD.md`](docs/PRD.md)
- System design and data flow: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- UI design system: [`docs/DESIGN.md`](docs/DESIGN.md)
- AI coding constraints: [`docs/RULES.md`](docs/RULES.md) and [`AGENTS.md`](AGENTS.md)
- Ordered implementation work: [`TASKS.md`](TASKS.md)
- Test and evaluation requirements: [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md)
- Security boundaries: [`docs/SECURITY.md`](docs/SECURITY.md)
- Architectural decisions: [`docs/DECISIONS.md`](docs/DECISIONS.md)
- Current project state: [`docs/MEMORY.md`](docs/MEMORY.md)
- Official technical links: [`docs/TECHNICAL_REFERENCES.md`](docs/TECHNICAL_REFERENCES.md)

## Release checklist

- [ ] All mandatory tests pass; no known critical/high-severity issue remains.
- [ ] Human approval is enforced server-side for both action tools.
- [ ] Step limits, timeout, retry, fallback, and failure termination are tested.
- [ ] Evaluation report includes the dataset version, model/provider configuration (without secrets), results, and failure cases.
- [ ] `docker compose up --build` works from a clean checkout.
- [ ] README has verified setup steps, screenshots, architecture diagram, known limitations, and demo instructions.
- [ ] No real credentials, customer data, or private provider responses are committed.
