# AI Operations Agent — Complete Antigravity Prompt Sequence

These prompts are designed to be pasted into Google Antigravity **one at a time**, in order. They implement the requirements in `Agent.md` and the project context files (`AGENTS.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/RULES.md`, `docs/SECURITY.md`, `docs/TEST_PLAN.md`, and `TASKS.md`).

## How to use the prompts

1. Extract the project documentation ZIP into the project root and open that exact folder in Antigravity.
2. Use **Planning / `/plan`** for Prompt 0 and the final audits. Use the normal **Agent** workflow for implementation prompts. If the IDE presents a plan for a multi-file task, review it before allowing implementation.
3. Paste **one prompt per turn**. Do not send the next prompt until the current task's checks pass and you have reviewed the changes.
4. Keep model credentials in `.env` only. Never paste your API key into prompts or commit it. The initial model adapter targets an OpenAI-compatible chat endpoint; a provider URL or API key alone does not prove compatibility.
5. Use synthetic records and mock action adapters. Do not enable real email delivery or third-party ticketing for this MVP.
6. If a prompt cannot be completed because a dependency or external service is unavailable, ask Antigravity to state the exact blocker and leave the task incomplete. Do not accept fake test results.

## Global execution contract

Every prompt below assumes the following:

- Read `AGENTS.md` and the relevant sections of the project documentation before modifying files.
- Complete only the named task and its acceptance criteria. Do not silently expand scope, replace the stack, or refactor unrelated code.
- Inspect the current repository first. Preserve existing work; do not overwrite files blindly.
- Do not expose, print, log, or commit secrets. Do not run destructive commands against a database or repository without explicit approval.
- Add or update tests and actually run the relevant commands. Never claim a command passed unless it ran and its result was observed.
- Keep ticket creation and report sending as **approval-gated mock/local actions**. No model-generated argument or frontend interaction can bypass server-side validation and approval.
- After the task, report: **(1)** files changed, **(2)** implementation summary, **(3)** commands actually run and their results, **(4)** acceptance criteria met/not met, **(5)** remaining issues, and **(6)** suggested next task. Update `TASKS.md` and `docs/MEMORY.md` accurately. Do not mark a task complete unless evidence supports it.
- Do not create a Git commit automatically. Show the diff and let the developer review it first.

---

# Prompt 0 — Inspect the repository and create the implementation plan

**Recommended mode:** Planning / `/plan` (read-only first)

```text
We are building the AI Operations Agent described in this repository. Before changing any files, read:
- AGENTS.md
- docs/PRD.md
- docs/ARCHITECTURE.md
- docs/DESIGN.md
- docs/RULES.md
- docs/SECURITY.md
- docs/TEST_PLAN.md
- docs/DECISIONS.md
- docs/MEMORY.md
- docs/TECHNICAL_REFERENCES.md
- TASKS.md
- README.md

Inspect the current repository and identify existing code, dependencies, environment files, migrations, tests, and any uncommitted work. Do not overwrite existing work and do not write application code yet.

Return:
1. A concise summary of the requirements and safety invariants.
2. The detected repository state and any discrepancies between files.
3. The implementation plan for TASK-001 only.
4. The files you expect TASK-001 to create or modify.
5. The exact checks you will run to verify TASK-001.
6. Any assumption that must be resolved before implementation.

Do not implement TASK-001 until you have presented the plan. Preserve the planned stack unless a concrete compatibility issue is found; if so, explain it and propose the smallest change before proceeding.
```

# Prompt 1 — TASK-001: Repository foundation, app scaffolds, Docker Compose

**Recommended mode:** Agent; review the plan before accepting multi-file edits.

```text
Implement TASK-001 from TASKS.md only: repository and local development foundation.

Before editing, inspect the repository and read AGENTS.md plus docs/ARCHITECTURE.md, docs/RULES.md, docs/SECURITY.md, and docs/DECISIONS.md.

Create a clean, maintainable monorepo layout consistent with the architecture, using:
- apps/api: Python, FastAPI, Pydantic, dependency management, pytest, lint/format/type-check configuration.
- apps/web: Next.js, TypeScript, Tailwind CSS, and consistent package scripts.
- PostgreSQL, Redis, API, web, and pgAdmin in Docker Compose. pgAdmin must be local-development-only or behind a Compose profile, and its port must bind to localhost.
- Root Dockerfiles/Compose files or infra/ files, whichever best matches the documented layout.
- .gitignore, .env.example, environment/config validation, health endpoints, and useful setup scripts if needed.

Use compatible, currently supported dependency versions based on official documentation and package compatibility. Do not guess API details for a library. Keep the backend and frontend independent but make `docker compose up --build` the intended local entry point. Add health checks and make database-dependent startup/migrations handle readiness correctly. Do not put secrets in any source file. Ensure `.env.example` contains placeholders only. Do not add real external integrations.

Create only the scaffolding needed for the current task. Do not implement agent tools, graph logic, operational UI features, or production deployment yet. Do not overwrite any existing files without comparing their content first.

Verification:
- Run relevant Python dependency/config checks and backend tests that exist.
- Run frontend install/type/lint/build checks that are available without concealing failures.
- Validate Docker Compose configuration if Docker is available.
- If a check cannot run, report why; do not claim it passed.
- Update TASKS.md and docs/MEMORY.md accurately.

Stop after TASK-001. Report changed files, actual commands/results, acceptance status, and remaining issues. Do not commit.
```

# Prompt 2 — TASK-002: PostgreSQL schema, migrations, and synthetic seed data

```text
Implement TASK-002 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/SECURITY.md, docs/RULES.md, and docs/TEST_PLAN.md first.

Design the initial relational schema and SQLAlchemy models/repositories needed for this project. Use Alembic migrations, database constraints, useful indexes, created/updated timestamps, explicit statuses, and foreign keys where appropriate. Cover these domain areas as appropriate to the architecture: customers, orders, searchable internal documents/source metadata, tickets, report jobs, approval requests, agent runs, tool events, and evaluation run/results metadata.

Add reproducible, entirely synthetic seed data and a documented command to seed a fresh development database. Seeding twice must not create duplicates or produce destructive side effects. Separate credentials from seed data. Keep action statuses explicit (for example pending, approved, rejected, executed, failed, expired where appropriate) and enforce valid state values at the application boundary and, where suitable, at the database layer.

Do not add live integrations or arbitrary SQL. Do not drop/overwrite any existing database. If a database is running, use a clearly identified development database and do not run destructive reset commands.

Add tests for model constraints and seed idempotency where possible. Verify the migration chain on a clean development database if Docker/database access is available; otherwise run static/unit checks and clearly list the unverified integration step. Update TASKS.md, docs/MEMORY.md, and docs/DECISIONS.md if schema choices require recording.

Stop after TASK-002. Report files changed, checks actually run, migration status, and any remaining manual setup. Do not commit.
```

# Prompt 3 — TASK-003: Model adapter, typed contracts, and first read-only tools

```text
Implement TASK-003 from TASKS.md only. Read AGENTS.md and the architecture, rules, security, and test-plan documents first.

Create a small model-provider adapter interface that isolates provider-specific HTTP/request/response logic from the agent. Configure provider name, base URL, model, API key, timeout, retry limits, and generation settings via validated environment/configuration. The initial adapter supports a documented OpenAI-compatible chat endpoint only; do not assume every provider or API key is compatible. Never return keys or raw authorization details in logs/errors. Keep live provider calls optional in tests.

Define Pydantic/typed contracts for agent requests, normalized intents if needed, tool calls, tool results, final answer, run status, and structured errors. Validate all untrusted input/output.

Implement the first tools:
- `get_customer`: retrieve synthetic customer information through a repository.
- `get_order`: retrieve synthetic order information through a repository.
- `search_database`: support a small, schema-bound set of approved filters/queries, never arbitrary SQL from model text.

Use dependency injection and a fake model adapter for deterministic tests. Unit tests must not require a paid model API key. Include malformed input, missing record, unknown filter, provider error, and invalid model-response tests.

Do not build the LangGraph yet and do not implement ticket/report actions yet. Update TASKS.md and docs/MEMORY.md truthfully. Stop after TASK-003 and report exact test results. Do not commit.
```

# Prompt 4 — TASK-004: LangGraph baseline workflow and bounded tool registry

```text
Implement TASK-004 from TASKS.md only. First inspect the existing implementation and read AGENTS.md, docs/ARCHITECTURE.md, docs/RULES.md, and docs/SECURITY.md.

Build the baseline LangGraph workflow with explicit typed state and focused nodes for request normalization, tool selection/planning, tool dispatch, result handling, and final response. Reuse the provider adapter and schemas from TASK-003; do not duplicate provider code or place the whole workflow in one giant function.

Create a strict allowlisted tool registry. Before dispatch, validate tool name and arguments; validate tool outputs before adding them to graph state. Never give the model arbitrary SQL, shell, general filesystem access, or unrestricted network access. Add configurable maximum graph steps and tool calls, and ensure every path reaches a defined terminal result or a deliberate persisted approval pause. Use a fake model in tests so core workflow tests are deterministic.

Add tests for a customer lookup, an order lookup, an unknown tool attempt, invalid tool arguments, malformed tool output, and an attempted loop that must stop at the configured budget. Define a checkpointing interface/strategy suitable for later approval pause/resume; do not invent support that the installed package version does not provide. Record any package-version limitation and verify it against official docs.

Do not add the document search/calculator tools or approval UI in this task. Update TASKS.md and docs/MEMORY.md. Stop after TASK-004 and report test outcomes. Do not commit.
```

# Prompt 5 — TASK-005: Document search and safe calculator

```text
Implement TASK-005 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/RULES.md, docs/SECURITY.md, and docs/TEST_PLAN.md.

Add `search_documents(query)` over a small synthetic internal knowledge corpus. Each result must include a stable source identifier and a concise excerpt/metadata sufficient for the final answer to reference. Use a simple deterministic local search implementation unless the current architecture already documents a specific search backend; do not introduce an external vector database without documenting and justifying the change.

Add `calculate(operation, operands)` with a strict allowlist of deterministic operations and typed numeric operands. Do not call eval/exec, parse arbitrary code, invoke a shell, or let the model submit executable expressions. Handle unsupported operations, missing operands, division-by-zero, invalid types, and numeric limits as structured errors.

Register both tools with the existing allowlisted registry and include tool schemas/descriptions. Add unit and graph integration tests for relevant results, no results, citation/source references, valid arithmetic, invalid input, unsupported operations, and safe failures. Ensure the final response never invents document sources and states when the corpus lacks an answer.

Do not build action tools in this task. Update TASKS.md and docs/MEMORY.md, run relevant tests, and stop. Report actual results; do not commit.
```

# Prompt 6 — TASK-006: Pending action proposals for ticket creation and report sending

```text
Implement TASK-006 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/SECURITY.md, docs/RULES.md, and docs/TEST_PLAN.md before editing.

Implement `create_ticket` and `send_report` as proposal tools only. An LLM tool call must create a validated, durable pending action request; it must not execute the ticket/report side effect. Persist the proposed action type, validated arguments, requesting run, idempotency key, creation time, pending status, and enough sanitized context for a reviewer to understand the proposal.

Use mocked/local action adapters only. No outbound email, no external ticket service, and no unapproved network side effects. Ensure duplicate graph retries or repeat tool calls with the same idempotency key do not create duplicate proposals. Keep the server-side action executor separate from the proposal creator so the later approval service can control it.

Add tests proving that calling either tool only creates a pending proposal, malformed payloads are rejected, and idempotency prevents duplicates. No approval endpoint or UI is required in this task. If persistent idempotency needs schema changes, add a proper migration rather than mutating tables manually.

Update TASKS.md, docs/MEMORY.md, docs/SECURITY.md or docs/DECISIONS.md only if necessary. Stop after TASK-006 and provide actual test results. Do not commit.
```

# Prompt 7 — TASK-007: State, memory boundaries, checkpointing, and budgets

```text
Implement TASK-007 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/RULES.md, and docs/SECURITY.md.

Make graph state explicit and typed. Document and implement what is retained within a run versus what is persisted durably in PostgreSQL. Keep transient reasoning/control state separate from operational records, action proposals, tool events, and any user-visible conversation history. Avoid storing hidden chain-of-thought; store actionable structured state, observations, source IDs, selected tool metadata, and terminal status instead.

Enforce configured maximum steps, tool-call count, input size, output size, and reasonable retained-context limits. Ensure checkpoint/state persistence can pause and resume an approval-gated workflow using supported APIs from the installed LangGraph/checkpointer versions. Checkpoint records must not contain API keys or unnecessary private payloads. If reliable checkpoint persistence is not available, fail closed for action execution and document the limitation.

Add tests for budget enforcement, state serialization, pause/resume behavior where supported, and secret-free stored state. Update docs/ARCHITECTURE.md, docs/MEMORY.md, TASKS.md, and docs/DECISIONS.md as needed. Stop after TASK-007. Report what is verified versus not verified. Do not commit.
```

# Prompt 8 — TASK-008: Timeouts, bounded retries, validation, and safe failures

```text
Implement TASK-008 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/RULES.md, docs/SECURITY.md, and docs/TEST_PLAN.md.

Add per-model and per-tool timeouts using the existing configuration. Implement bounded retries with backoff only for explicitly classified transient failures. Do not retry invalid input, authorization/policy rejection, missing records, or other permanent failures by default. Prevent nested retry loops from multiplying attempts beyond the documented budget.

Validate tool arguments and outputs at the boundary. Create a consistent typed error taxonomy for validation, not found, timeout, provider unavailable, rate limited/transient, authorization/policy, and internal errors. Add safe user-facing fallback responses that clearly state when the task could not be completed; never claim success after a failure or convert a safety rejection into a successful result.

Test timeout behavior, retry count/backoff using fakes, retry exhaustion, permanent-failure no-retry, invalid output schema, provider failure, and graph termination. Keep tests deterministic and fast. Update TASKS.md and docs/MEMORY.md. Stop after TASK-008; report actual commands and outcomes. Do not commit.
```

# Prompt 9 — TASK-009: Deterministic scenario harness and versioned fixtures

```text
Implement TASK-009 from TASKS.md only. Read AGENTS.md, docs/TEST_PLAN.md, docs/ARCHITECTURE.md, docs/RULES.md, and the existing tests/evaluation fixtures.

Create a versioned synthetic scenario set for normal read-only queries, ambiguous or incomplete requests, missing records, document no-results, calculations, unsupported actions, unknown tools, invalid model output, tool failures, provider failures, retry exhaustion, and loop/step-limit cases. Each case should define the user request, expected permitted tool behavior, expected terminal state/response constraints, whether approval is required, and the relevant safety assertions.

Implement a deterministic runner using fake model/provider adapters and controlled fake tools. Capture actual tool selection, schema validation, terminal status, approval requirement, fallback category, and any source references. Keep fixture data synthetic, safe to commit, and versioned. Do not fabricate passing results; the runner must execute the cases.

Add tests for runner correctness and malformed fixtures. Provide a clear command to run the scenario suite locally and in CI. Update docs/TEST_PLAN.md, TASKS.md, and docs/MEMORY.md. Stop after TASK-009 and report the measured scenario count and actual results. Do not commit.
```

# Prompt 10 — TASK-010: Human approval inbox API and pause/resume lifecycle

```text
Implement TASK-010 from TASKS.md only. This task is security-critical. Read AGENTS.md, docs/ARCHITECTURE.md, docs/SECURITY.md, docs/RULES.md, and docs/TEST_PLAN.md carefully before editing.

Implement the backend lifecycle for approval-gated `create_ticket` and `send_report` proposals. The agent must pause after persisting a pending proposal. Add API endpoints/services to list pending proposals, fetch a proposal, approve it, or reject it. Enforce authorization and approval policy on the server; do not rely on UI button visibility. For this local single-operator MVP, implement the simplest documented development authorization boundary and make its limitations explicit—do not falsely claim production-grade authentication.

At approval time, revalidate the stored payload, requester/run relationship, current proposal status, expiry (if configured), and permission to decide. Use an atomic, idempotent state transition and durable audit event. Only an authorized approval can invoke the mocked action executor. Rejection must never invoke it. Repeated/late decisions and duplicate requests must not duplicate side effects. Resume the paused graph only through a persisted checkpoint/thread identifier when supported; if checkpoint recovery cannot be guaranteed, fail closed and do not execute.

Add integration tests for pending → approved → executed, pending → rejected → not executed, duplicate approval, approve-after-reject, reject-after-approve, expired/malformed proposal, unauthorized decision, persistence/checkpoint failure, and action executor failure. Ensure the trace accurately records the decision and execution outcome.

Do not configure real email or live ticketing. Update docs/SECURITY.md, docs/ARCHITECTURE.md, docs/TEST_PLAN.md, TASKS.md, and docs/MEMORY.md. Stop after TASK-010 and report evidence for every safety case. Do not commit.
```

# Prompt 11 — TASK-011: Tool routing, clarification, and fallback behavior

```text
Implement TASK-011 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/RULES.md, docs/SECURITY.md, and existing scenario fixtures.

Harden tool routing so it can only dispatch registered tools with validated typed arguments and server-side policy checks. Define behavior for: no suitable tool, unknown tool name, malformed arguments, missing required input, unavailable tool, empty tool result, insufficient document evidence, and a tool result that cannot answer the request.

When required user information is missing, return a concise clarifying question rather than guessing IDs, recipients, amounts, or other operational facts. A fallback response must not turn an unknown/failed tool into an asserted success. Read-only fallback options may be used only if explicitly registered, permitted, and relevant. Action proposals must continue to require approval.

Extend scenario tests and routing tests to assert correct tool choice, unknown-tool rejection, clarification behavior, no invented result, and safe failure. Update docs/MEMORY.md, TASKS.md, and docs/TEST_PLAN.md. Stop after TASK-011. Report actual test results and do not commit.
```

# Prompt 12 — TASK-012: Redis cache for eligible read-only operations

```text
Implement TASK-012 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/RULES.md, docs/SECURITY.md, and docs/TEST_PLAN.md.

Add a small Redis cache service with explicit TTLs, namespaced keys, and documented cache-key construction. Cache only approved deterministic read-only calls, such as eligible customer/order lookups or document queries when correctness can be maintained. Include all meaningful query parameters and a schema/data version in keys. Do not cache action proposals, approvals, authorization decisions, failures as successes, or any write-capable action.

Redis must be an optimization rather than a correctness dependency. If Redis is unavailable or times out, degrade to the underlying safe read service when healthy. Do not skip validation or permissions on cache hits. Avoid placing secrets or unnecessary sensitive values in keys/logs. Document invalidation behavior and TTL configuration.

Add tests for cache hit/miss, expiry, parameter separation, stale/versioned key separation, cache outage fallback, and proof that action tools are never cached. Use fakes or a test Redis service, as appropriate. Update TASKS.md and docs/MEMORY.md. Stop after TASK-012 and report actual checks. Do not commit.
```

# Prompt 13 — TASK-013: Run tracing, structured logs, and run-detail API

```text
Implement TASK-013 from TASKS.md only. Read AGENTS.md, docs/ARCHITECTURE.md, docs/DESIGN.md, docs/SECURITY.md, docs/RULES.md, and docs/TEST_PLAN.md.

Add correlation IDs for each agent run and unique IDs for tool events. Persist chronological trace events containing graph stage, registered tool name when relevant, sanitized input summary, outcome, duration, retry count, and structured error category. Store only the minimum useful data; redact keys, authorization headers, secrets, and unnecessary personal payloads. Do not store hidden chain-of-thought or raw provider request headers.

Expose API endpoints for recent run history and run details, including status, timestamps/duration, tool-call count, final response, source references, approval events, and trace timeline. Apply pagination and safe filtering; validate all query parameters. Ensure database errors or missing run IDs produce predictable API responses.

Add tests for trace ordering, run correlation, pagination/filter validation, missing runs, redaction, and event persistence during both successful and failed runs. Do not build the frontend trace UI yet. Update docs/ARCHITECTURE.md, docs/SECURITY.md, TASKS.md, and docs/MEMORY.md. Stop after TASK-013 and report actual test results. Do not commit.
```

# Prompt 14 — TASK-014: Evaluation metrics and honest report artifacts

```text
Implement TASK-014 from TASKS.md only. Read AGENTS.md, docs/TEST_PLAN.md, docs/ARCHITECTURE.md, docs/SECURITY.md, and the existing scenario harness.

Build a versioned evaluation runner and report output (machine-readable JSON plus a human-readable summary). Measure at least: task completion for supported cases, correct tool selection, tool argument/schema validity, approval-policy compliance, duplicate-action prevention, document citation/source-reference validity, error/fallback rate, latency (median and p95 where sample size permits), and termination within the configured budget.

Record the scenario dataset version, timestamp, non-secret model/provider label and model name/version where available, run counts, metric denominators, failures, and known limitations. Separate safety-policy metrics from answer quality. Do not hardcode target values as achieved, count an unexecuted case as a pass, or call a scenario successful based only on fluent text. Safety test violations must be clearly highlighted as release blockers.

Add tests using deterministic fake providers so the evaluation works without an external API key. Provide a command to run evaluations and save reports under an appropriate ignored/generated location; commit only synthetic fixture data, not secrets or sensitive logs. Update docs/TEST_PLAN.md, TASKS.md, and docs/MEMORY.md. Stop after TASK-014 and report measured metrics from the actual run. Do not commit.
```

# Prompt 15 — Backend API integration and end-to-end request lifecycle

```text
Review the existing backend and implement only the missing integration required to expose the completed services as a coherent FastAPI application. Read AGENTS.md, docs/PRD.md, docs/ARCHITECTURE.md, docs/RULES.md, docs/SECURITY.md, and TASKS.md first. Do not duplicate already working endpoints or rewrite modules just for style.

Ensure the API exposes validated endpoints for:
- Submitting an agent request and returning a run ID/status/result or waiting-for-approval state.
- Checking an individual run and listing recent runs.
- Reading a run detail and sanitized event trace.
- Listing and deciding approval requests using the secure approval lifecycle from TASK-010.
- Running/reading evaluation results where the evaluation services exist.
- Health/readiness status for API, PostgreSQL, Redis, and model-provider configuration without exposing secrets.

Use consistent response/error contracts, request IDs, pagination where useful, and server-side validation. Keep routers thin and domain logic in services. Do not expose debugging details, raw exceptions, stack traces, provider keys, arbitrary repository queries, or an endpoint that directly bypasses the approval lifecycle. Make demo-mode limitations explicit.

Add API integration tests for the read-only flow, pending approval flow, approval/rejection, history/detail, evaluation endpoint behavior, health/readiness with optional dependencies, and invalid inputs. If an API area is not implemented yet, do not fake it; report it as a blocker and leave the endpoint absent or explicitly unavailable. Update docs and stop. Do not commit.
```

# Prompt 16 — Frontend foundation and shared design system

```text
Implement the frontend foundation specified by docs/DESIGN.md. Read AGENTS.md, docs/PRD.md, docs/DESIGN.md, docs/ARCHITECTURE.md, docs/RULES.md, and docs/SECURITY.md before editing.

In apps/web, create the responsive application shell and reusable components appropriate to the design: AppShell, navigation, PageHeader, StatusBadge, MetricCard, DataTable, EmptyState, ErrorState, LoadingSkeleton, RunTimeline, ToolEventRow, SourceReference, ApprovalDecisionPanel, and ConfirmDialog where relevant. Use Next.js + TypeScript + Tailwind; follow the existing scaffold and reuse rather than duplicate components.

Design target: professional, calm operations console; neutral surfaces, restrained blue accent, consistent typography/spacing/borders; avoid flashy gradients, glassmorphism, oversized landing-page hero sections, or inconsistent card styles. Navigation should provide Assistant, Runs, Approvals, Evaluations, and System Status. Include responsive navigation and keyboard-visible focus styles. Use semantic HTML and accessible labels. Do not build fake backend functionality or invented evaluation metrics.

Add frontend lint/type-check and component tests if the scaffold supports them. Do not connect every page to the backend yet; provide clear shared API client/types scaffolding without hardcoded fake successes. Run available checks and update TASKS.md/docs/MEMORY.md. Stop after this task and report actual results. Do not commit.
```

# Prompt 17 — Assistant console: submit requests and show honest run states

```text
Implement the Assistant console page according to docs/PRD.md and docs/DESIGN.md. Read AGENTS.md and the existing frontend API client/types first.

Build a usable request composer with visible character limit, validation, disabled/loading state, error handling, and submit behavior wired to the actual backend API. Render the returned run status and final response. Distinguish running, waiting for approval, succeeded, failed, and cancelled states when those states are supported by the API. Show source references when provided by document search and a sanitized tool activity timeline when available. If the request requires approval, show “Approval required” and link to the proposal; never imply the action has already happened.

Do not mock success in production UI code. In development, a clearly labelled fixture/story may be used only if it is separate from the real app behavior and cannot be mistaken for a real result. Handle network errors, empty responses, missing sources, and retryable failures. Follow accessibility and responsive rules, including keyboard use at mobile widths.

Add component/integration tests for submission, pending approval, success, failure, source references, and API outage. Run frontend lint/type-check/tests/build that exist. Update docs/MEMORY.md and TASKS.md accurately. Stop after this task; do not commit.
```

# Prompt 18 — Run history and run-detail trace UI

```text
Implement the Runs history and run-detail pages using the real API endpoints. Read AGENTS.md, docs/DESIGN.md, docs/ARCHITECTURE.md, and the frontend API client/types first.

Run history must support practical search/filtering by status, time range, and run ID where the backend supports it, with pagination, loading skeletons, empty/no-filter-results states, and retryable error states. Display run ID, request preview, status, start time/duration, and tool-call count.

Run detail must show status and terminal reason, final response, source references, and an ordered trace timeline. Each trace event should display stage/tool, result/outcome, duration, retry count when available, and collapsible sanitized details. Highlight retries/failures without hiding ordinary events. Show provider/model labels only, never secret values. Handle missing run IDs and stale links cleanly.

Do not invent unavailable data fields or metrics. Add tests for filters, pagination, loading/error/empty states, trace ordering, and missing-run behavior. Verify responsive behavior at approximately 375px, tablet, and desktop widths. Run available checks, update TASKS.md/docs/MEMORY.md, and stop. Do not commit.
```

# Prompt 19 — Approval inbox UI with guarded decisions

```text
Implement the Approvals inbox/detail interface using the existing approval API. This UI must preserve the server-side safety rules; read AGENTS.md, docs/DESIGN.md, docs/SECURITY.md, docs/ARCHITECTURE.md, and the backend approval contract first.

Show pending proposals with action type, short business reason, related run ID, creation time, and current status. The detail view must show the proposed effect and validated/sanitized parameters clearly before decision. Approve and Reject must be separate, explicit actions; show a confirmation dialog for consequential decisions. Disable controls while a request is in progress and for already-decided/expired proposals. Do not use optimistic updates to claim approval or execution: update the UI only after the API confirms the decision and report execution outcome separately from reviewer decision.

Handle 401/403 or equivalent authorization failures, expired proposals, duplicate decisions, and backend errors with clear messages. UI safeguards are not security controls; do not add any client-side bypass or direct action endpoint. Ensure keyboard focus and status labels do not rely on color alone.

Add tests for approve, reject, pending, already-decided, expired, permission failure, network failure, and confirmed execution/failure statuses. Update docs/MEMORY.md and TASKS.md; run actual checks and stop. Do not commit.
```

# Prompt 20 — Evaluation dashboard and system status page

```text
Implement the Evaluations and System Status pages using the actual backend API contracts. Read AGENTS.md, docs/DESIGN.md, docs/TEST_PLAN.md, docs/ARCHITECTURE.md, and the existing frontend types first.

Evaluation view: display the latest report's dataset version, run time, provider/model label, task completion, correct tool selection, schema validity, approval-policy compliance, duplicate-action prevention, citation validity, latency, error/fallback rates, and failing cases where present. Separate answer-quality indicators from safety metrics. If no report exists, show a useful empty state with the command or instruction to run evaluation; do not display fake sample scores as measured results.

System Status view: show API, PostgreSQL, Redis, and provider-configuration readiness as the backend exposes them. It may show a provider as “not configured”; never show an API key, secret environment value, raw connection string, or stack trace. Distinguish optional Redis degradation from required dependency failure.

Add tests for no evaluation, populated evaluation, safety failure highlighting, partial/unavailable health data, and no secret rendering. Ensure responsive layout and accessible chart/table labels. Run actual frontend checks and update docs/MEMORY.md/TASKS.md. Stop after this task. Do not commit.
```

# Prompt 21 — TASK-015: End-to-end flows, fault injection, and security stress tests

```text
Implement TASK-015 from TASKS.md. Read AGENTS.md, docs/TEST_PLAN.md, docs/SECURITY.md, docs/RULES.md, docs/ARCHITECTURE.md, and current test results first.

Expand unit, integration, and Playwright end-to-end coverage for the core journeys:
1. Ask a customer/order question and see a result grounded in synthetic database data.
2. Ask an internal-document question and see valid source references (or an honest no-result answer).
3. Perform a valid calculation and reject an unsupported operation safely.
4. Propose a ticket/report, see it pending, approve it, and verify the mock adapter executes once.
5. Reject a proposal and verify no action side effect occurs.
6. Inspect the run history and trace.
7. Run evaluations and inspect actual results.
8. Exercise invalid input, malformed model output, wrong tool, timeout, retry exhaustion, provider failure, database/Redis outage, duplicate request/approval, and an attempted graph loop.

Verify that all write-capable actions are approval-gated on the server, Redis outage does not bypass validation, secrets are redacted, graph budgets terminate, and no side effects are repeated on retries. Use synthetic fixtures and test doubles. Avoid real external email/ticket services or production data. Run the project's actual lint, type-check, unit, integration, frontend, and E2E commands where available; state clearly which could not run and why.

Fix release-blocking failures within this task without unrelated refactoring. Document any remaining issue and exact reproduction steps. Update docs/TEST_PLAN.md, docs/SECURITY.md, TASKS.md, and docs/MEMORY.md. Stop and report evidence. Do not commit.
```

# Prompt 22 — Focused security and architecture audit (report first, then fix blockers)

**Recommended mode:** Planning / `/plan` for the initial audit report.

```text
Perform a focused security and architecture audit of the repository against AGENTS.md, docs/PRD.md, docs/ARCHITECTURE.md, docs/RULES.md, docs/SECURITY.md, docs/TEST_PLAN.md, and TASKS.md. Do not change code in the first pass.

Review at least:
- Secret handling, .env and Git ignore coverage, logs and exception redaction.
- CORS, exposed ports, pgAdmin local-only/profile status, database permissions, SQL/query boundaries.
- Pydantic validation and request-size limits.
- Tool allowlist and prevention of arbitrary SQL, shell, filesystem, and unrestricted network access.
- Model-generated argument trust boundaries.
- Approval authorization, atomic state transitions, idempotency, checkpoint durability, expiry, and rejection-without-side-effect.
- Retry/timeout/step budgets and safe terminal paths.
- Redis cache eligibility, keys, TTL, outage behavior, and validation on cache hits.
- Frontend secret leaks, misleading success indicators, unsafe optimistic approval updates, accessibility, and error detail exposure.
- Dependencies, container configuration, tests, and documentation truthfulness.

Return findings ranked Critical/High/Medium/Low with exact file/line evidence, exploit or failure scenario, impact, and smallest recommended fix. Separate confirmed defects from unverified risks. Do not claim compliance/certification.

After presenting findings, implement only Critical/High release blockers in this task, add regression tests, run them, and re-report any issues that remain. Update docs/SECURITY.md, docs/TEST_PLAN.md, TASKS.md, and docs/MEMORY.md. Do not commit.
```

# Prompt 23 — Clean local Docker Compose verification and developer experience

```text
Verify and improve the local development experience without changing product scope. Read AGENTS.md, docs/ARCHITECTURE.md, docs/SECURITY.md, README.md, .env.example, and the current Compose configuration.

Check the stack includes API, web, PostgreSQL, Redis, and pgAdmin in a local-only/profile-gated configuration. Validate service names, internal connection URLs, health checks, startup order/readiness, persistent development volumes where appropriate, safe default ports, environment variable wiring, and container build contexts. Bind pgAdmin to localhost and ensure it is not exposed as a public deployment service. Do not bake credentials into images or compose files; use placeholders/environment interpolation and safe examples.

Verify from a clean development setup as safely as possible. Do not delete existing volumes or data without explicit approval. If a true clean-database test requires destructive actions, create a separate disposable test database/volume and explain the steps rather than destroying user data. Confirm database migrations and synthetic seeding commands are documented and repeatable. Check that Redis can be unavailable without breaking otherwise eligible read-only paths.

Run Docker Compose config validation and container/build/health checks if Docker is available. If unavailable, perform static validation and list what remains unverified; do not claim successful container startup. Update README.md, docs/MEMORY.md, TASKS.md, and docs/SECURITY.md. Stop after this task and do not commit.
```

# Prompt 24 — TASK-016: Portfolio-ready README, demo guide, and release notes

```text
Implement TASK-016 from TASKS.md only. Read AGENTS.md, README.md, docs/PRD.md, docs/ARCHITECTURE.md, docs/TEST_PLAN.md, docs/SECURITY.md, docs/DECISIONS.md, and docs/MEMORY.md.

Polish the README for a public AI engineering portfolio while staying truthful to the implemented product. Include:
- Clear project problem statement and feature list.
- Architecture diagram that matches real code and data flow.
- Verified stack and prerequisites.
- Local setup steps, environment-variable instructions, Docker Compose services, API docs URL, and pgAdmin local-development note.
- Database migration and synthetic seed commands.
- Test, lint, type-check, E2E, scenario evaluation, and report commands.
- Model provider configuration requirements, including the limitation that the initial adapter needs an OpenAI-compatible chat API and that providers may differ in API compatibility.
- A short demo walkthrough for read-only lookup, document search/calculation, pending action approval/rejection, trace inspection, and evaluation.
- Actual evaluation numbers only when generated by real runs, with dataset version, failures, and limitations.
- Security boundaries, mock integration behavior, known limitations, and future improvement areas.
- Screenshot/diagram/demo-GIF placeholders clearly marked as placeholders until real artifacts exist.

Do not claim production deployment, real third-party integrations, authentication, reliability percentages, or compliance unless they were actually implemented and verified. Remove stale planning language only where the corresponding feature is genuinely complete. Update docs/MEMORY.md and TASKS.md accurately. Run Markdown/link or repository checks if available. Stop after TASK-016 and do not commit.
```

# Prompt 25 — Final release readiness audit

**Recommended mode:** Planning / `/plan` for the review, then Agent only for clearly scoped fixes.

```text
Perform the final release-readiness audit for AI Operations Agent. Read AGENTS.md, docs/PRD.md, docs/ARCHITECTURE.md, docs/DESIGN.md, docs/RULES.md, docs/SECURITY.md, docs/TEST_PLAN.md, docs/DECISIONS.md, docs/MEMORY.md, TASKS.md, and README.md.

Do not assume any task is complete because its checkbox says so. Verify the repository and run available checks. Inspect Git status and do not discard or overwrite uncommitted user changes.

Check each acceptance criterion in docs/PRD.md and each mandatory checklist item in TASKS.md. At minimum, verify:
- clean local startup instructions and Docker Compose configuration;
- migrations and repeatable synthetic seeding;
- all five read-only tools/operations and both pending action-proposal tools;
- registered-tool allowlist, typed validation, graph budgets, timeouts, bounded retry and safe fallback;
- approval pending/approve/reject lifecycle, idempotency, checkpoint/persistence failure behavior, and proof no action executes before approval;
- Redis cache scope and graceful degradation;
- trace/run history, redaction, and actual evaluation report outputs;
- frontend pages and honest loading/error/empty/pending/success states;
- unit/integration/E2E/security tests, frontend checks, and build;
- no committed secrets, live integrations accidentally enabled, or misleading README claims.

First provide a release matrix with PASS / FAIL / NOT VERIFIED and exact supporting commands or test names. Then fix only clear release-blocking defects, add regression tests, rerun affected checks, and update documentation. Do not fabricate missing tests or results. Do not create a Git release tag or commit. End with the exact command sequence a developer should use to start and demo the project and a concise list of known limitations.
```

---

## Optional debugging prompt — diagnose before changing code

Use this only when a task fails; replace the bracketed details with the real output.

```text
Do not modify code yet. Diagnose this failure using the repository and the relevant project docs.

TASK: [TASK-### and intended behavior]
EXPECTED: [what should happen]
ACTUAL: [what happened]
ERROR / TEST OUTPUT: [paste the exact error, with secrets removed]
REPRODUCTION STEPS: [steps]
CONSTRAINTS: Preserve the existing architecture and database schema unless the root cause proves a schema change is required. Do not refactor unrelated files and do not replace real test failures with mocks just to make tests pass.

Report the root cause, affected files, smallest safe fix, regression test, and commands to verify it. Wait until the diagnosis is clear; then implement only that fix, run the relevant checks, and update docs/MEMORY.md.
```
