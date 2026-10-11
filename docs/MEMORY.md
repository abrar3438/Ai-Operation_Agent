# Project Memory — AI Operations Agent

## Current status

**TASK-001 complete: repository and local development foundation implemented (not committed).** Backend scaffold (`apps/api` with FastAPI, typed config, health endpoints, DB/Redis clients, Alembic, pytest), frontend scaffold (`apps/web` with Next.js 16.4.0 + React 19 + Tailwind 4 + strict TS), Compose stack (`docker-compose.yml` with API, web, PostgreSQL 16, Redis 7, profile-gated pgAdmin), environment template, and Dockerfiles. See README for verified setup/ports. Do not start TASK-002 until TASK-001 is reviewed.

## Completed in this documentation pass

- [x] Project problem, target users, MVP, non-goals, and acceptance criteria.
- [x] Planned stack and component boundaries.
- [x] Tool contracts for `get_customer`, `get_order`, `search_database`, `search_documents`, `calculate`, `create_ticket`, and `send_report`.
- [x] Human approval requirement for action tools.
- [x] Task plan mapped to the Day 36–49 source sequence.
- [x] Development, UI, test, and security rules.
- [x] Environment variable template and ignore rules.
- [x] Antigravity root instructions in `AGENTS.md`.

## Not implemented/verified yet

- No agent tools, LangGraph workflow, approvals, caching behavior, evaluation runner, or feature UI exists (later tasks).
- Live DB/migration verification (`alembic upgrade head`, `SELECT current_database(), current_user`) and `docker compose up` health checks have run successfully (see TASK-001 verification below).
- Provider/model compatibility has not been tested; use only a provider endpoint that matches the adapter contract once implemented.
- No evaluation score, latency result, deployment URL, or passing integration/E2E result exists yet.

## TASK-001 record (2026-10-11)

- Repo was documentation-only and not a Git repository; ran `git init` (no commit).
- Stack pinned: Python 3.12 (`requires-python >=3.12,<3.14`), backend managed by `uv` (`pyproject.toml`, `uv.lock`), frontend `npm` (Next 16.4.0, React 19.3.0, Tailwind 4.3.3, TypeScript 5, ESLint 9, Node 20 image).
- Backend: `src/app/{main,config,logging}.py`, `api/v1/health.py` (`/health/live`, `/health/ready` with required Postgres + optional Redis), `db/session.py` (`ping_ready`), `cache/redis_client.py` (`ping_ready`), `alembic.ini` + `alembic/env.py` (baseline only), `scripts/wait_for_deps.py`, tests `test_config.py` + `test_health.py`.
- Frontend: App Router scaffold, `typecheck` script, `output: "standalone"`, DESIGN.md tokens in `globals.css`, placeholder console page, Dockerfile + `.dockerignore`.
- Compose: service `postgres` (image `postgres:16-alpine`, container `agent-postgres`, `127.0.0.1:5433:5432`, healthcheck, new volume `agent_pgdata`), `redis` (`redis:7-alpine`), `api` (host `8001`), `web` (host `3000`), `pgadmin` (`dev-tools` profile, `127.0.0.1:5050`).
- DB values per user decision: `agentdb` / `postgres` / `postgres`; container URL `@postgres:5432`, host URL `@localhost:5433`.
- Enterprise RAG (`rag-api` on host 8000, `rag-postgres` on host 5432, its volumes) left untouched; conflicts resolved in the implementation plan.
- Residual risk accepted: `postgres`/`postgres` superuser is a disposable-local-only dev choice, recorded in ADR-011. The prior ADR-010 was renumbered to ADR-012 to keep ADR numbering unique.

## TASK-001 verification (2026-10-11, all observed passing)

- Backend (`apps/api`): `uv sync`; `uv run ruff check .` (passed after fixing B008/import-order with `Annotated` deps and long lines); `uv run ruff format --check .` (17 files); `uv run mypy src` (11 files, no issues); `uv run pytest` (**10 passed**; one upstream anyio deprecation warning only).
- Frontend (`apps/web`): `npm run typecheck`, `npm run lint`, `npm run build` all passed (Next 16.4.0 production build, `/` prerendered).
- Compose: `docker compose config` clean (API host `8001`, Postgres `127.0.0.1:5433:5432`, new volumes `ai-operations-agent_agent_pgdata`/`ai-operations-agent_agent_redisdata`); `--profile dev-tools` config shows pgAdmin `127.0.0.1:5050` only under profile.
- Live stack: `postgres` + `redis` healthy; `psql -c "SELECT current_database(), current_user;"` → `agentdb | postgres`; API image built and `agent-api` healthy on `127.0.0.1:8001`; `/health/live` → `{"status":"ok"}`; `/health/ready` → `ok` with postgres ok + redis ok; `alembic current`/`alembic upgrade head` ran against the live DB (baseline, no revisions); web image built, `agent-web` served the placeholder page (verified via HTTP).
- `docker compose down` (no `-v`); `docker volume ls` confirms all RAG and agent volumes intact.
- Fix during verification: generated missing `uv.lock` and removed it from `apps/api/.dockerignore` so the API image builds reproducibly with `--frozen`.

## TASK-002 record (2026-10-11)

- Schema: 10 tables (`customers`, `orders`, `documents`, `tickets`, `report_jobs`, `approval_requests`, `agent_runs`, `tool_events`, `evaluation_runs`, `evaluation_case_results`) with UUID PKs, created/updated timestamps, unique business keys, FKs (`orders.customer_id`, `tickets.customer_id` → `customers.customer_id`), status check constraints on every stateful table, non-negative order totals, and lookup indexes. Approval transitions limited at DB level to `pending → approved/rejected/expired` states; terminal re-decision rejected in service code.
- Code: `src/app/db/{models,schemas,repositories,seed_data}.py`, `scripts/seed.py` (idempotent upsert, waits for DB, applies migrations first, `--database-url` override), migration `7f3a1c9d2b44`, `tests/test_schema.py` (6 tests: table contract, unique keys, approval check constraint, order lookup/not-found, seed idempotency, approval idempotency + decision rules).
- Seed fixtures are 100% synthetic (`.example` domains); credentials stay in env/compose, never in fixtures.
- Migration `7f3a1c9d2b44` applied to live `agentdb` via the API image (`docker compose run --rm api alembic upgrade head`); `alembic_version` confirms the revision.
- Seed ran twice via the API image: `5 customers, 6 orders, 5 documents`, counts unchanged on rerun; `approval_requests` untouched.
- Fixed during verification: host `alembic`/`seed.py` hang on this Windows shell (no output/cancellation signal through the tool), so long DB commands run inside Compose; added `connect_timeout` + migration-first seed; renamed prior ADR-010 to ADR-012 when adding ADR-011.
- Checks: `uv run pytest` **16 passed**; `ruff check` clean; `ruff format --check` clean; `mypy src` clean (15 files).
- Schema choice recorded in `docs/DECISIONS.md` as ADR-013 (single `documents` table; chunking deferred to TASK-005 if needed).

## Current task

**Next:** `TASK-003 — Model adapter and structured response contracts (Day 36)`.

## Key invariants that must not change casually

1. The LLM may request tools but backend code owns tool allowlisting, schema validation, authorization, and execution.
2. `create_ticket` and `send_report` remain pending until an authorized approval is durably recorded.
3. Default data/integrations are synthetic/mock; no real email or external ticket service is called.
4. Graph execution is bounded by step/tool budgets, timeouts, and bounded retries.
5. Redis is optional cache only; PostgreSQL is the system of record.
6. Model provider keys live only server-side in environment/secrets, never in source or browser code.
7. Evaluation values must be measured by the runner and reported honestly.

## Documentation maintenance

After each completed task, update this file with what actually changed, tests run and outcomes, known issues, and the exact next unchecked task. Mark tasks only after their acceptance criteria pass. Record architectural changes in `docs/DECISIONS.md`.
