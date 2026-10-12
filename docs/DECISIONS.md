# Architecture Decision Records — AI Operations Agent

Status labels are planning defaults. If implementation reveals a better option, add a new ADR or update the status with a reason; do not silently change the stack.

## ADR-001 — Use Python and FastAPI for the backend

**Status:** Accepted for planning

**Decision:** Build the API and agent runtime in Python with FastAPI and Pydantic.

**Reason:** The project is centered on AI orchestration, typed tool interfaces, evaluation scripts, and Python libraries. FastAPI exposes a documented HTTP boundary while keeping agent logic separate from routes.

**Consequences:** Python dependency/version compatibility must be tested and locked. Routes stay thin; tools/services/graph have separate modules.

## ADR-002 — Use LangGraph for explicit agent control flow

**Status:** Accepted for planning

**Decision:** Represent tool selection/execution, state updates, approval pauses, retries/fallback paths, and terminal handling as an explicit graph workflow.

**Reason:** The project requirements emphasize state, termination, tracing, retry control, and human approval rather than a single opaque prompt loop.

**Consequences:** Graph state and node transitions need tests. Checkpointing must be configured for durable approval resume. Follow the official documentation for the selected installed version.

## ADR-003 — PostgreSQL is the source of truth

**Status:** Accepted for planning

**Decision:** Use PostgreSQL for synthetic operational records, action/approval records, run metadata, sanitized events, and evaluation metadata. Use SQLAlchemy/Alembic for access and schema migrations.

**Reason:** The project requires durable state, auditable transitions, structured queries, and a credible local development story.

**Consequences:** Migrations and repository/service layers are required. Keep app credentials least-privileged and local ports bound to localhost by default.

## ADR-004 — Human approval is a server-side policy gate

**Status:** Accepted; release-blocking

**Decision:** `create_ticket` and `send_report` create pending proposals; a durable, authorized approval is required before execution. Rejection means no side effect.

**Reason:** These actions change external or persisted state and are the key safety demonstration of the project.

**Consequences:** Requires approval state transitions, idempotency, durable checkpointing, audit events, and tests for bypass/duplicates. The frontend cannot enforce policy by itself.

## ADR-005 — Use synthetic data and mocked integrations by default

**Status:** Accepted for MVP

**Decision:** Provide synthetic customers, orders, documents, mock ticket creation, and mock report delivery. Do not connect real external services in the MVP.

**Reason:** Enables reproducible testing and safe public demonstration without exposing real customer data or sending accidental messages.

**Consequences:** README must state this limitation. Real adapters require a separately scoped decision, credentials, sandbox testing, and explicit enablement.

## ADR-006 — Isolate model provider behind an adapter

**Status:** Accepted for planning

**Decision:** Configure model provider/base URL/model/key through environment variables and keep provider-specific behavior behind an internal interface. The first adapter targets a documented OpenAI-compatible chat API.

**Reason:** Makes it possible to change models/provider endpoints without rewriting tools and graph logic, while staying honest about compatibility.

**Consequences:** Do not assume any platform's key is compatible with every endpoint. Additional providers need a tested adapter and documented configuration.

## ADR-007 — Use a separate Next.js frontend

**Status:** Accepted for planning

**Decision:** Use Next.js + TypeScript + Tailwind for the operator console and FastAPI for the agent backend.

**Reason:** Allows a responsive portfolio-quality interface while keeping LangGraph and Python service dependencies in a backend runtime.

**Consequences:** Maintain typed HTTP contracts and CORS configuration. The frontend never accesses the database or model key directly.

## ADR-008 — Use Redis only as an optional read cache

**Status:** Accepted for planning

**Decision:** Use Redis for safe TTL-based caching of eligible deterministic read-only operations. It is not the system of record and is not used to store approval authority.

**Reason:** The roadmap includes caching, and it is a useful production engineering concept when narrowly scoped.

**Consequences:** Cache outage must degrade gracefully. Cache keys and invalidation require tests; actions/approvals never use cache as their authority.

## ADR-009 — Keep admin tooling local-development-only

**Status:** Accepted for planning

**Decision:** Include pgAdmin in the local Compose setup, but bind it to localhost and/or gate it behind a development profile.

**Reason:** Helpful for learning/debugging the PostgreSQL schema, but inappropriate to expose publicly in a demo deployment.

**Consequences:** README must label pgAdmin as local-only. Production deployments must omit it.

## ADR-011 — Disposable local database credentials for TASK-001

**Status:** Accepted for local development only; non-deployable

**Decision:** Use `postgres`/`postgres` with database `agentdb` on host port `5433` for the local development database, per the operator's explicit requirement.

**Reason:** The operator previously hit repeated connection failures and chose one simple, memorable local credential set to stabilize setup. It runs only on `127.0.0.1`-bound local containers with synthetic data.

**Consequences:** This intentionally deviates from ADR-003 least-privilege guidance for the disposable dev database only. Never use these credentials outside local development, never ship them in a deployment design, and prefer least-privilege app credentials before any shared/preview deployment.

## ADR-012 — Evaluate with a versioned scenario set

**Status:** Accepted for planning

**Decision:** Keep synthetic scenario fixtures in the repository and produce explicit reports for tool selection, correctness constraints, policy compliance, errors, and latency.

**Reason:** A few successful manual demos do not establish reliability; repeatable, inspectable tests provide stronger evidence.

**Consequences:** Report actual results and dataset version; do not hardcode target metrics as measured performance.

## ADR-013 — Defer document chunks table

**Status:** Accepted for MVP

**Decision:** Store the synthetic knowledge corpus in a single `documents` table (title, content, tags, stable `source_id`) with truncated-index search instead of a normalized `documents` + `document_chunks` pair.

**Reason:** The MVP corpus is five short synthetic documents; chunking adds schema and retrieval complexity with no measurable benefit at this scale. TASK-005 can introduce chunking with its own migration if real retrieval needs it.

**Consequences:** `search_documents` queries one table via bounded LIKE with a 50-row cap. Citation behavior still returns stable `source_id` values.

## ADR-014 — Fresh-entry convention for the append-only tool-call buffer

**Status:** Accepted for implementation

**Decision:** Keep `pending_tool_calls` on the compiled append reducer (`operator.add` → `BinaryOperatorAggregate` in `langgraph 1.2.14`) and gate all dispatch/routers on fresh entries (`fresh: True` = placed by the immediately-preceding planning step; consumed entries are rewritten `fresh: False` in place).

**Reason:** Installed-package verification, not assumption: inspecting `StateGraph(GraphState).channels` shows `pending_tool_calls` as `BinaryOperatorAggregate` while every other channel is `LastValue`, so full-list writes merge rather than replace in this version. The fresh-entry convention is the smallest change that preserves TASK-004/006 semantics (unknown-tool/invalid-args/malformed-output guards, single-consumption, loop budgets) without hand-rolled reducers or inventing unsupported checkpointer APIs.

**Consequences:** Resume audits `tool_results`, not the control buffer. If a future LangGraph version changes Pydantic reducer handling, re-verify the compiled channels and update this ADR before changing the convention.
