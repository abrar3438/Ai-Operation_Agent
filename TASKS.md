# Implementation Tasks — AI Operations Agent

**Rule:** Complete one task at a time. Do not mark a task complete until its acceptance criteria are met and the relevant checks actually pass. This plan follows the Day 36–49 sequence in the supplied `Agent.md`, while adding the minimum setup and UI work required to deliver a usable project.

## Phase 0 — Project bootstrap (complete before feature work)

### TASK-001 — Repository and local development foundation
- [x] Inspect the repository and confirm whether it is empty or already contains code.
- [x] Create the agreed API/frontend layout without overwriting unrelated files.
- [x] Add Python project/dependency management, formatting/lint/type-check commands, and test scaffolding.
- [x] Add Next.js + TypeScript + Tailwind app scaffold and consistent scripts.
- [x] Add `.gitignore`, `.env.example`, and configuration validation.
- [x] Add Dockerfiles and Compose services for API, web, PostgreSQL, Redis, and pgAdmin (pgAdmin must be local-development-only or profile-gated).
- [x] Add health checks and make service startup wait for database readiness where needed.
- **Acceptance:** Clean setup instructions are documented; no secrets are committed; service configuration has safe local defaults; tests/lint/type checks can be invoked.

### TASK-002 — Database schema and synthetic operational dataset
- [x] Design and migrate tables for customers, orders, documents/chunks or searchable document metadata, tickets, report jobs, approval requests, agent runs, tool events, and evaluation results as needed.
- [x] Add constraints, indexes, created/updated timestamps, and explicit action status fields.
- [x] Add reproducible synthetic seed data and reset-safe seed behavior.
- [x] Keep credentials/configuration separate from seed data.
- **Acceptance:** Migrations run from a clean database; seed can run twice without duplicates or destructive side effects; no real user/customer data is used.

## Phase 1 — Days 36–38: tools, structured output, graph, and read-only capabilities

### TASK-003 — Model adapter and structured response contracts (Day 36)
- [ ] Build one model adapter configured by environment variables; keep provider-specific code isolated.
- [ ] Validate required config at startup and fail with actionable, secret-safe errors.
- [ ] Define typed schemas for agent request, tool calls, tool results, run status, and final answer.
- [ ] Add the initial tools: `get_customer`, `get_order`, and safe `search_database` over predefined repositories/filters.
- [ ] Add deterministic tests using a fake model adapter so core tests do not require paid API calls.
- **Acceptance:** The adapter is configurable; malformed inputs are rejected; the model cannot call arbitrary functions or execute arbitrary SQL; tests run without an external model key.

### TASK-004 — LangGraph baseline workflow (Day 37)
- [ ] Define typed graph state and explicit nodes for request normalization, reasoning/tool selection, tool execution, result handling, and final response.
- [ ] Register tools through an allowlist; validate every call before dispatch.
- [ ] Add a configurable maximum number of graph/tool steps and reliable terminal status.
- [ ] Add checkpointing/persistence strategy suitable for pausing and resuming approval workflows.
- **Acceptance:** A basic customer/order question flows through the graph, tool outputs enter state in a typed form, and runaway tool-call loops terminate safely.

### TASK-005 — Document search and calculator tools (Day 38)
- [ ] Implement `search_documents` against a small synthetic internal knowledge corpus with source identifiers/snippets.
- [ ] Implement `calculate` using constrained deterministic operations; do not evaluate arbitrary Python or shell expressions.
- [ ] Return source references for document results and typed failures for unsupported requests.
- [ ] Add unit and integration tests for relevant, empty, malformed, and unavailable results.
- **Acceptance:** Document-based answers can cite returned source identifiers; calculations use a safe allowlisted grammar/operation set; errors do not crash the graph.

## Phase 2 — Days 39–41: action proposals, state, and reliability

### TASK-006 — Ticket and report action proposals (Day 39)
- [ ] Implement schemas and handlers for `create_ticket` and `send_report` as **pending action proposals**, not immediate external side effects.
- [ ] Persist action intent, validated arguments, requesting run, and pending status.
- [ ] Add idempotency keys so a resumed/retried graph cannot create duplicate action proposals.
- [ ] Keep adapters mocked/local; no real email delivery or external ticket provider by default.
- **Acceptance:** Calling an action tool only creates a pending approval item. Tests prove that no ticket/report is executed before approval.

### TASK-007 — State, conversation context, memory, and step limits (Day 40)
- [ ] Define which context is retained per run and what is persisted across runs.
- [ ] Keep short-term graph state separate from durable operational records and any optional user-visible conversation history.
- [ ] Set maximum graph steps, maximum tool invocations, context size limits, and output-size limits.
- [ ] Ensure checkpoint state does not contain API keys or unnecessary private payloads.
- **Acceptance:** State survives a configured graph pause/restart where supported; run limits are enforced and clearly recorded; memory behavior is documented and tested.

### TASK-008 — Validation, timeouts, retries, and failure handling (Day 41)
- [ ] Add per-tool and model timeouts.
- [ ] Retry only transient failures with bounded attempts and backoff.
- [ ] Separate retryable errors from invalid input, authorization failures, missing records, and permanent provider errors.
- [ ] Validate tool input and output; add safe fallback responses when the model/tool path fails.
- **Acceptance:** Tests cover timeout, retry exhaustion, invalid schema, permanent failure, and fallback behavior; no infinite retry is possible.

## Phase 3 — Days 42–44: scenario coverage, human approval, routing/fallback

### TASK-009 — Scenario test harness (Day 42)
- [ ] Create a deterministic scenario runner covering normal requests, ambiguous requests, missing records, unsupported actions, tool errors, and model failures.
- [ ] Capture expected behavior, selected tool(s), terminal result, and whether approval was required.
- [ ] Keep scenario fixtures synthetic and versioned.
- **Acceptance:** Scenario suite runs repeatably in CI/local development using fake providers; results are easy to inspect.

### TASK-010 — Human-in-the-loop approval and rejection (Day 43)
- [ ] Implement an approval inbox in the API and web console.
- [ ] Pause the graph before any ticket/report side effect and persist the checkpoint/thread identifier.
- [ ] Implement approve/reject endpoints with server-side authorization checks, state-transition validation, audit events, and idempotency.
- [ ] Resume the workflow only after a valid approval; rejection must terminate that action without execution.
- [ ] Prevent approval of expired, already-decided, malformed, or unrelated requests.
- **Acceptance:** End-to-end tests prove pending → approved → executed and pending → rejected → not executed; no direct API path bypasses approval.

### TASK-011 — Tool router and fallback behavior (Day 44)
- [ ] Route only among registered and permitted tools using typed arguments.
- [ ] Handle no suitable tool, malformed tool request, unknown tool, tool unavailable, and tool result not sufficient.
- [ ] Ask a clarifying question when required information is missing rather than guessing.
- [ ] Add fallback behavior that never converts an unsafe failure into a successful action.
- **Acceptance:** Routing test cases document expected tool choice/fallback and prove unknown tools are blocked.

## Phase 4 — Days 45–47: caching, tracing, and evaluation

### TASK-012 — Redis caching (Day 45)
- [ ] Add a cache service with TTLs and explicit cache-key construction.
- [ ] Cache only approved deterministic read-only operations, starting with safe lookups/searches where appropriate.
- [ ] Include relevant query parameters/data version in cache keys; document invalidation behavior.
- [ ] Make Redis outages degrade gracefully without bypassing safety controls.
- **Acceptance:** Tests verify hit/miss/expiration, correct cache separation, and no caching of action tools or approvals.

### TASK-013 — Run traces, structured logs, and tool execution history (Day 46)
- [ ] Assign run, trace, and tool-event IDs.
- [ ] Persist graph stage, tool name, safe/redacted input summary, duration, outcome, retry count, and errors.
- [ ] Add run-detail API and UI with chronological trace/timeline view.
- [ ] Redact secrets and unnecessary personal information; make tracing configurable.
- **Acceptance:** A failed run can be inspected from the UI/API; logs do not include API keys or unredacted sensitive values.

### TASK-014 — Evaluation dataset and metrics (Day 47)
- [ ] Create versioned evaluation cases with user request, expected tool behavior, expected approval behavior, and expected answer/constraints.
- [ ] Implement the evaluation runner and report artifact (JSON plus human-readable summary).
- [ ] Measure task success, correct tool selection, argument/schema validity, approval-policy compliance, grounded document citation behavior, latency, and error/fallback rate.
- [ ] Record model/provider name and model version where available, without secrets.
- **Acceptance:** Metrics are calculated reproducibly; evaluation report describes dataset version and known limitations; policy violations are counted separately from answer quality.

## Phase 5 — Day 48: robustness and security testing

### TASK-015 — Stress, fault-injection, and security pass (Day 48)
- [ ] Exercise timeout, invalid input, failing tool, unavailable database/cache, provider outage, malformed model response, duplicate request, and graph-loop cases.
- [ ] Verify step limits, bounded retries, idempotency, approval enforcement, redaction, and graceful shutdown.
- [ ] Run lint, type checks, unit tests, integration tests, frontend checks, and Playwright smoke tests that are available.
- [ ] Document remaining defects and fix release blockers before proceeding.
- **Acceptance:** Critical safety/reliability cases pass and remaining known issues are explicitly listed.

## Phase 6 — Day 49: portfolio release

### TASK-016 — Release polish, demo, and documentation (Day 49)
- [ ] Finish the operations UI: chat/run console, run history, trace detail, approval inbox, and evaluation summary.
- [ ] Add loading, empty, error, and responsive states; keyboard accessibility.
- [ ] Add verified setup/run/test instructions, architecture diagram, screenshots or demo GIF placeholder, evaluation example, failure cases, and limitations to README.
- [ ] Run clean-checkout Docker Compose verification and production build checks.
- [ ] Review secrets, database exposure, CORS, and demo safety before any deployment.
- [ ] Create a release tag only after checks are green; prepare GitHub repository description and demo script.
- **Acceptance:** The project can be started from documented instructions, demonstrates the core user flows, reports honest evaluation results, and contains no committed secrets.

## Definition of done for every task

- [ ] Requirements and existing implementation inspected first.
- [ ] Scope stayed limited to the selected task.
- [ ] Tests added/updated and actually run.
- [ ] Lint/type-check/build checks run where applicable.
- [ ] Security and approval implications reviewed.
- [ ] `TASKS.md`, `docs/MEMORY.md`, README, and decision records updated as needed.
- [ ] A descriptive Git commit is created by the developer after reviewing the diff.
