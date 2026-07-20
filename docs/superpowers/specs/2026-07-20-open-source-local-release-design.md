# Memory Passport V0.1 Open-Source Local Release Design

## Objective

Finish every open GitHub issue in `joevilcai666/memory-passport` and make the
V0.1 open-source release practical for a prospective customer to clone, run,
exercise, and validate locally without GitHub Actions or paid model credentials.
The same checkout must also support the real vendored HMS inference path when
the operator supplies valid model and embedding credentials.

## Scope

The release covers open issues #2 through #10. Issues #2, #3, #4, and #5 have
implementation commits on the `HMS` branch but remain open; they must be
revalidated against their acceptance criteria before closure. Issues #6 through
#10 require implementation:

- #6: memory CRUD, version chains, tombstones, state-machine enforcement, and
  HMS mutation propagation.
- #7: persisted policies, V0.1 portability constraints, and authoritative
  ingest/retrieve enforcement.
- #8: Luna v1-to-v2 migration preview, execution, retries, warnings, and
  rollback.
- #9: tenant-scoped audit-log queries and five-dimensional usage reporting.
- #10: asynchronous model-neutral exports and full user deletion.

The release also includes the local-operability work needed to make those
features testable by someone unfamiliar with the repository. It does not add
GitHub Actions, hosted infrastructure, billing, authentication beyond the
existing API-key model, or P1/P2 product features.

## Runtime Architecture

### Stable Memory-Engine Boundary

Memory Passport continues to use the existing HMS HTTP contract through
`HmsClient`. Both local modes expose the same bank, retain, recall, list,
update, and delete operations. Business services do not branch on the selected
mode.

### Default Deterministic Mode

The default Compose stack runs a small HMS-compatible deterministic service.
It persists banks and memory units in its own Postgres tables and implements
the exact subset of the pinned HMS HTTP API consumed by Memory Passport. Retain
creates stable memory units without an external model call; recall performs a
deterministic text-ranked lookup. This keeps the MP-to-HMS network boundary,
bank lifecycle, mappings, mutation propagation, exports, deletion, and
migration behavior observable in a no-credential environment.

The deterministic engine is a local evaluation implementation, not a claim of
semantic parity with model-backed HMS. API responses and documentation label
the active engine mode so users can distinguish it from real inference.

### Real HMS Mode

A Compose overlay replaces the deterministic service with the vendored HMS API
and worker pinned by the repository submodule. The operator supplies real LLM,
retain-LLM, and embedding provider settings. Memory Passport continues to call
the same URL and contract, so switching mode requires configuration and a stack
restart rather than code changes.

Real mode validates configuration before startup. Placeholder credentials or
missing required provider fields fail with a concise actionable error. The
health endpoint reports the active engine mode and upstream status without
returning secrets.

## Domain Changes

### Memory CRUD (#6)

`GET /v1/memories` uses tenant-scoped filtering and pagination. Deleted rows
are excluded unless `include_deleted=true`.

Content edits create a new active record, archive the previous record, set
`version = previous.version + 1`, and preserve `supersedes`. Status-only changes
use an explicit transition table. Illegal transitions return `409` with the
source and target states. Delete is a tombstone. All mutations update or remove
the mapped HMS unit before committing MP state and emit the required audit
entry. An HMS failure rolls back the MP transaction and returns a mapped `502`.

### Policy Enforcement (#7)

`POST /v1/policies` upserts one policy per `(app_id, agent_id)` after validating
that both belong to the caller's tenant. `cross_brand_app=true` always returns
`422` and writes nothing. New policies default to sensitivity masking. Mutable
portability axes write one `policy.changed` audit entry.

Ingest resolves live auto-write rules for every event. A matching `block` rule
creates neither an HMS unit nor an MP record. Retrieve resolves live result caps
and sensitivity projection settings for every request.

### Migration Wedge (#8)

Preview considers non-deleted, non-archived memories in the source relationship
and applies the prototype rule exactly:

- `portable && confidence >= 0.7` is recommended.
- `portable && confidence < 0.7` needs review.
- `device_local` is not moved.

Execution records selected, skipped, and failed IDs and moves successful MP
memory device links without changing the HMS bank (`bank_id == user_id`). A
mixture of successes and failures produces `completed_with_warnings`; zero
successes produces retryable `failed`. Removing old-device access unbinds the
source device, while keeping access leaves it bound. Rollback restores memory
links and device bindings and moves the migration to an explicit `rolled_back`
state. Started, completed, and rollback events are auditable; the public audit
action union is extended consistently in the frontend and backend.

### Audit and Usage (#9)

Audit reads are tenant-scoped, newest-first, paginated, filterable by actor,
action, target, and ISO-8601 time bounds, and have no side effects.

A `UsageEvent` table records memory writes, reads, updates, and deletes with
tenant, user, operation, and timestamp. This avoids parsing human-readable
audit details. Usage returns:

- distinct active users from usage events;
- operation counts grouped by ingest, retrieve, update, and delete;
- active structured-memory row count as the documented V0.1 storage unit;
- device-bound transitions in the time window;
- migration executions in the time window.

The endpoint defaults to the previous 30 days, accepts explicit ISO-8601
bounds, and creates no audit or usage rows itself.

### Export and User Deletion (#10)

An `ExportJob` row stores tenant, user, status, timestamps, artifact path,
download token hash, token expiry, and a sanitized failure message.
`POST /v1/exports` commits a pending job and schedules a FastAPI background task.
The task opens its own database session, serializes the user's non-deleted and
tombstoned MP records into a versioned model-neutral JSON bundle, writes it to
a mounted export directory, marks the job complete, and writes exactly one
`memory.exported` audit entry. The bundle contains semantic text and structured
MP fields but no embeddings or HMS/provider payloads.

Status polling is tenant-scoped. Completed jobs expose a short-lived,
single-job download URL backed by a high-entropy token. The download endpoint
verifies the token hash and expiry. Export files are ignored by Git and survive
backend container restarts through a local volume.

User deletion tombstones all MP memories, deletes the user's HMS bank, marks
the passport as deleted, and writes exactly one summary audit row. Per-memory
audit hooks are bypassed for this bulk operation. An HMS failure rolls the MP
transaction back. Retrieval checks passport state before calling HMS and
returns zero memories for a deleted passport. Tenant-mismatched requests are
rejected with `403` as required by issue #10 and cannot change cross-tenant data.

## Local Developer and Evaluator Experience

The documented default path is:

1. Clone recursively.
2. Copy the checked-in example environment file.
3. Run `make demo`.
4. Open API docs and execute the supplied curl walkthrough.
5. Run `make check` for frontend lint/build plus backend unit and integration
   tests against the running deterministic stack.

`make demo` builds the default stack, waits for health, migrates, seeds the Luna
dataset idempotently, and runs a small end-to-end flow. Commands use the modern
`docker compose` plugin. Destructive cleanup remains a separate, clearly named
target.

The real-HMS guide documents the required variables and one explicit command
using the real overlay. It also documents expected inference cost and that real
provider calls may send test content to the configured provider.

Root ESLint ignores `vendor/hms` and other generated/runtime paths. Next.js
must type-check and build against the expanded audit-action union. Pytest marks
service-backed suites explicitly and skips them cleanly when their declared
dependencies are unavailable; `make check` in the running stack executes them
rather than relying on accidental host services.

## Error and Transaction Semantics

- Every resource lookup is tenant-scoped before mutation.
- Invalid input is `422`; illegal domain transitions are `409`; missing
  in-tenant resources are `404`; upstream HMS failures are `502`.
- MP database mutations that depend on HMS success commit only after the HMS
  operation succeeds.
- Background export failures persist `failed` status and a sanitized message.
- Read-aggregate endpoints are side-effect free.
- Secrets, provider responses, embeddings, and stack traces are never included
  in exports or public errors.

## Verification Strategy

Implementation follows red-green-refactor for every behavior change. Tests are
layered as follows:

- Fast SQLite service/route tests for validation, state machines, tenant
  isolation, filtering, pagination, aggregation, and exact response shapes.
- Contract tests against the deterministic HMS HTTP service for bank, retain,
  recall, mutation, and delete behavior.
- Compose-backed integration tests for every acceptance criterion in issues
  #2 through #10, including export download, deletion non-retrievability, Luna
  migration, and live policy enforcement.
- A real-HMS configuration smoke test that validates configuration and health
  without asserting nondeterministic model output. A documented manual command
  exercises real retain/recall when credentials are supplied.
- Fresh `pnpm lint`, `pnpm build`, backend Ruff, backend pytest, Compose health,
  seed, and curl walkthrough evidence before publication.

No GitHub Actions workflow is added. Local commands and their expected results
are the authoritative release gate.

## GitHub Completion and Publication

Each issue is checked against its own acceptance list. Existing issues #2–#5
and #3 are not closed merely because commits exist; they close only after the
new release gate proves their behavior. Issues #6–#10 close after their focused
tests and the full integration gate pass. Final publication commits all scoped
files on the current `HMS` branch and pushes it to `origin/HMS`.
