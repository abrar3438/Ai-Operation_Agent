# Product Requirements Document — AI Operations Agent

## 1. Product summary

AI Operations Agent is a controlled operations assistant for a fictional support/operations team. It accepts a natural-language request, determines whether it needs a permitted tool, calls the tool with validated arguments, examines results, and returns a grounded response. Actions that change system state—creating a ticket or sending a report—must pause for human approval before execution.

## 2. Problem

Operations tasks commonly require people to query customer/order records, locate internal instructions, perform straightforward calculations, and prepare tickets or reports. Uncontrolled LLM tool execution can select the wrong tool, invent arguments, repeat actions, leak sensitive data, or claim success when an external operation failed. The project demonstrates a bounded agent architecture that makes these decisions inspectable and testable.

## 3. Target users

- **Primary:** Support/operations analyst using an internal assistant to look up records and prepare routine operational work.
- **Reviewer:** Team lead/operator who reviews proposed ticket/report actions before they execute.
- **Developer/maintainer:** AI engineer who needs to inspect traces, evaluate tool behavior, diagnose failures, and change model providers safely.

## 4. Desired outcomes

1. Complete supported read-only tasks with reliable tool selection and accurate use of tool output.
2. Prevent unapproved side effects.
3. Make each run explainable through a sequence of tool events, timing, outcomes, and errors.
4. Quantify behavior using a repeatable evaluation set, not only a hand-picked successful demo.
5. Run locally with reproducible setup and synthetic data; be safe to demonstrate publicly when deployed behind appropriate access controls.

## 5. Core capabilities

### 5.1 Read-only tools

- `get_customer(customer_id or supported search fields)`: retrieve a synthetic customer record using repository-level filters.
- `get_order(order_id or supported filters)`: retrieve order information.
- `search_database(query intent and schema-bound filters)`: search approved structured records. It must not expose raw arbitrary SQL execution.
- `search_documents(query)`: search the local synthetic knowledge corpus and return excerpts plus stable source identifiers.
- `calculate(operation, operands)`: calculate using a constrained list of deterministic operations; never evaluate arbitrary code.

### 5.2 Approval-gated action tools

- `create_ticket(validated ticket fields)`: create a pending action request; execution occurs only after explicit approval.
- `send_report(validated report payload/recipients or local demo destination)`: create a pending report-send request; delivery occurs only after explicit approval.
- Default implementations are mock/local adapters. The MVP does not send real email or create tickets in third-party systems.

### 5.3 Agent orchestration

- Structured request, tool-call, tool-result, and final response schemas.
- Explicit LangGraph state and nodes, with tool routing limited to registered tools.
- Controlled re-reasoning after results, plus deterministic terminal handling.
- Maximum steps/tool calls and output-size limits.
- Bounded retries and timeouts for transient failures.
- Human approval pauses and resumes the workflow using persisted state/checkpointing.
- Tool/provider fallback that never silently treats an error as success.

### 5.4 Operations interface

- **Assistant console:** enter a request, see the response, tool activity, sources, and approval requirement.
- **Run history:** browse recent runs by status/time and open a run.
- **Run detail/trace:** inspect ordered events, tool outcomes, duration, errors, and relevant sanitized inputs/outputs.
- **Approval inbox:** review proposed ticket/report actions and approve or reject them.
- **Evaluation view:** show latest evaluation result, key metrics, and failing scenarios.
- **Status/health display:** surface API/database/cache/provider readiness without revealing secrets.

### 5.5 Reliability and observability

- PostgreSQL persists application records, approvals, execution events, and evaluation metadata.
- Redis caches only eligible deterministic read-only results.
- Structured logs and per-run correlation identifiers.
- An evaluation harness with versioned synthetic scenarios and a report.
- Fault-injection and stress cases for invalid input, tool errors, provider errors, loops, duplicate requests, timeouts, and cache/database outages.

## 6. MVP and exclusions

### Included in MVP

- Local single-operator demo built with synthetic data.
- FastAPI backend, LangGraph agent, PostgreSQL, Redis, Next.js UI, and Docker Compose.
- Configurable model provider adapter; initial adapter supports a documented OpenAI-compatible chat endpoint.
- All seven named tools, graph limits, retries/timeouts/validation, action approval, trace view, and evaluation report.
- Mock integrations by default.

### Explicitly out of scope for MVP

- Autonomous actions without approval.
- Real customer data, production customer accounts, or multi-tenant SaaS.
- Real outbound email or a live third-party ticketing integration.
- Arbitrary SQL, shell, filesystem, or internet access delegated to the model.
- Multi-agent swarms, autonomous code execution, or unrestricted web browsing.
- Billing, mobile apps, enterprise SSO, Kubernetes, and advanced distributed scaling.
- Claims of production compliance or guaranteed correctness without evidence.

## 7. Key user journeys

### Journey A — Read-only question
1. Operator asks for a customer/order detail.
2. API validates request and starts a graph run.
3. Agent calls the correct read-only tool with validated arguments.
4. Tool returns structured data; agent produces a concise answer based on that data.
5. UI displays the answer and trace. If no record exists, the agent says so rather than inventing one.

### Journey B — Action needs approval
1. Operator asks to create a ticket or send a report.
2. Agent drafts an action request with validated fields.
3. Backend stores the proposal as pending and pauses the graph.
4. Approval inbox shows the action details and expected consequence.
5. Authorized operator approves or rejects. Only approval allows the action adapter to run.
6. The result and reviewer decision are recorded and visible in the run trace.

### Journey C — Failure
1. A tool/provider times out or returns invalid output.
2. A bounded retry may occur only for a retryable error.
3. If retries are exhausted, the run finishes with a clear safe failure/fallback response.
4. The trace records failure category, attempts, and duration without secret leakage.

### Journey D — Evaluation
1. Maintainer runs the versioned scenario suite.
2. The runner captures tool choice, schema validity, action policy, answer constraints, timing, and terminal status.
3. The report shows results and failures by scenario; it does not label the model successful based only on fluent language.

## 8. Success metrics

The evaluation harness should calculate these metrics and report actual measured values:

- Task completion rate for supported scenarios.
- Correct tool-selection rate.
- Tool argument/schema validation pass rate.
- Approval-policy compliance rate (must be 100% on safety test cases).
- Duplicate side-effect prevention rate (must be 100% on retry/idempotency test cases).
- Document answer citation/source-reference validity.
- Tool/provider error and safe-fallback rates.
- Median and p95 run latency, separated into model and tool time where feasible.
- Run termination rate under the configured step budget.

Do not hardcode target results as achieved facts. Store the baseline and actual measurements in each evaluation report. Any release-blocking safety metric failure must block release regardless of average task score.

## 9. Non-functional requirements

- **Security:** secrets from environment only; validate all input; restrict tool registry; redact sensitive log fields; bind local admin ports to localhost.
- **Reliability:** finite retries, timeouts, explicit terminal states, idempotent approval/action transitions.
- **Maintainability:** provider adapter and tools are separated from graph and API code; migrations are versioned; configuration is typed.
- **Testability:** core graph/tool tests work with fakes and do not require live model calls.
- **Usability:** responsive operator interface with loading, error, empty, success, and pending-approval states.
- **Reproducibility:** local services and setup are documented and containerized.

## 10. Acceptance criteria

The MVP is accepted only when:

1. A clean local setup can start the documented services.
2. A read-only customer/order/document/calculation workflow returns a result grounded in tool output or a clear no-result response.
3. No arbitrary tool name, arbitrary SQL, or invalid tool schema can execute.
4. Ticket/report proposals remain pending until an authorized approval occurs.
5. A rejected proposal produces no side effect; repeated approvals/retries do not duplicate the action.
6. Tool errors/timeouts/provider failures terminate within set limits and show a clear status.
7. Redis is optional for correctness; when unavailable, eligible reads still work without caching.
8. A developer can inspect a run trace and reproduce evaluation results.
9. Release documentation describes setup, features, limitations, failure cases, and actual test/evaluation results honestly.
