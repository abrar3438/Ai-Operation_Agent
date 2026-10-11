# Test Plan — AI Operations Agent

## 1. Test strategy

Test at several levels. Unit tests should be fast and independent of paid model APIs; integration tests use a disposable PostgreSQL/Redis or controlled test doubles; evaluation tests use a versioned scenario set; Playwright tests verify critical operator journeys. Record commands and actual outcomes in task reports. Do not mark tests passed unless they were run.

## 2. Backend unit tests

### Model adapter and schemas
- Valid/invalid configuration is handled with clear, secret-safe errors.
- Supported provider response maps to the internal response type.
- Missing/malformed/extra tool arguments are rejected according to schema.
- Provider timeout, rate limit, connection failure, and invalid response map to explicit categories.
- Logs and errors do not expose keys or authorization headers.

### Tool registry and read-only tools
- Known tool names dispatch to the matching handler.
- Unknown/disallowed tools are blocked before execution.
- `get_customer` and `get_order` return valid records and typed not-found results.
- `search_database` accepts only approved entities/filters and cannot run arbitrary SQL.
- `search_documents` returns source identifiers that correspond to indexed documents; empty search results are handled honestly.
- `calculate` supports its allowlisted operations and rejects arbitrary expressions, unsupported operations, NaN/infinite values when disallowed, and invalid operand types.
- Tool exceptions produce typed errors rather than unhandled crashes.

### Graph/state/budgets
- Basic read-only request follows the expected graph path.
- Results are represented as structured state.
- Maximum step/tool-call budgets terminate runaway loops.
- Every graph path either terminates or pauses durably for approval.
- Missing fields cause a clarification or safe failure rather than guessed arguments.
- Model/tool errors cannot produce a false success response.
- Checkpoint/resume preserves the correct run and pending approval identity.

### Approval and actions (release-blocking)
- Action tool call creates a pending proposal and does not execute a side effect.
- Rejecting a pending proposal creates no ticket/report.
- Approving valid proposal revalidates the payload and executes once.
- Duplicate approval, duplicate request, graph resume, and transient action failure cannot create duplicate actions.
- Already-decided, expired, malformed, or unrelated approval IDs are rejected.
- A failed database/checkpoint write fails closed: action must not execute.
- Only an authorized operator can decide an approval.
- State transitions outside the allowed transition model are rejected.

### Retry, timeout, and fallback
- Transient failures retry no more than the configured limit.
- Invalid input and authorization/policy errors are not retried as transient.
- Tool and model timeouts stop the relevant work within the configured budget.
- Retry exhaustion creates a failure event and safe user-facing message.
- Unknown tool, unsupported request, provider failure, Redis outage, and database failure have explicit behavior.

### Cache
- Hit, miss, TTL expiry, and key separation work as expected.
- Relevant data version/filter is reflected in the key.
- No action tool or approval result is cached.
- Redis outage bypasses caching where safe and does not reduce policy checks.

## 3. Database/integration tests

- Migrations succeed on a clean database.
- Synthetic seed operation is reproducible and repeat-safe.
- Repositories enforce record relationships and query filters.
- Approval/action state changes are atomic where required.
- Event/run records are consistently associated with run IDs.
- Pagination and filters do not expose unrelated or unauthorized records.
- PostgreSQL unavailable/read-only/transaction failure is handled safely.

## 4. Frontend tests

- API client handles success, validation errors, unauthorized/forbidden responses, timeout, and network failure.
- Assistant console displays running, success, waiting-for-approval, and failure states.
- Run history filters and opens the correct run.
- Trace view shows ordered events and sanitized details.
- Approval inbox allows a decision only for pending items and reflects server-confirmed state.
- Evaluation view distinguishes missing evaluations from measured zero scores.
- Components have accessible labels, keyboard focus, and state text not conveyed only through color.
- Main pages render at 375px, 768px, and 1440px widths without blocking controls or unreadable content.

## 5. Playwright end-to-end scenarios

1. Submit a read-only customer/order question and inspect the resulting run detail.
2. Search documents and verify a returned source reference is displayed.
3. Submit a request that produces a ticket proposal; verify it appears pending and no ticket exists yet.
4. Reject the proposal; verify the ticket is not created.
5. Submit a second proposal, approve it, and verify exactly one ticket/report result is recorded.
6. Open run history and trace; verify event chronology, status, and timing.
7. Run an evaluation from the UI/API or use the documented command and inspect the measured report.
8. Simulate a provider/tool failure in a test environment and verify the safe failure state is visible.

## 6. Evaluation suite

Maintain versioned synthetic cases that cover:
- Clear customer lookup.
- Clear order lookup.
- Missing customer/order.
- Ambiguous request requiring clarification.
- Document question with known source.
- Question not supported by the knowledge corpus.
- Valid/invalid calculations.
- Correct tool selection among similar tools.
- Unregistered tool proposal.
- Ticket/report request that pauses for approval.
- Rejected approval and duplicate decision.
- Malformed tool arguments.
- Tool timeout, tool error, provider error, and retry exhaustion.
- Step budget exhaustion / repeated tool-call behavior.
- Prompt injection inside user-provided text or retrieved documents attempting to bypass policy.

Metrics to compute: task success, tool-selection accuracy, argument schema validity, required-source-reference validity, safe terminal status, approval compliance, duplicate-action prevention, latency, retry count, and fallback/error rate. Safety failures must be independently counted and treated as release blockers; do not hide them inside a high overall score.

## 7. Performance and stress tests

- Repeated read-only requests under concurrency with a mix of cache hits/misses.
- Slow model response, slow tool, timeout, retry, and cancelled request.
- Duplicate action proposal request and approval submissions.
- Long but valid request and oversized invalid request.
- Redis unavailable and PostgreSQL unavailable.
- Malformed/oversized model tool-call payload.
- Many graph continuation attempts to verify the maximum step limit.

Choose explicit expected thresholds when the initial local baseline is measured; do not invent numeric performance achievements ahead of that measurement.

## 8. Release quality gates

Release is blocked if any of these fail:
- Approval bypass or action executes without approved state.
- Duplicate action occurs under retry/resume.
- Secret appears in logs, frontend bundle, or version control.
- Arbitrary SQL/tool execution is possible through model output.
- Step budget can be bypassed or graph loops indefinitely.
- Clean-checkout setup/migrations are broken.
- Required smoke tests fail.

Before release, document any non-critical tests that remain unimplemented, unrun, or flaky.
