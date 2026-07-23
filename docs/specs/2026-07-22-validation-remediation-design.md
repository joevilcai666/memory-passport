# Memory Passport V0.1 Validation Remediation Design

## Objective

Resolve every defect confirmed by the 2026-07-22 full-product validation,
replace false-positive UI behavior with backend-authoritative behavior, and
prove the repaired frontend and backend together. The repaired checkout must
remain locally runnable on Windows and Linux with the credential-free demo HMS
stack.

The implementation boundary is the current V0.1 PRD. Billing, webhooks,
hosted identity, and complete team RBAC remain P1. Existing V0.1 controls must
either perform the action they advertise or clearly report that the backend is
unavailable; no control may claim success after a failed or skipped request.

## Confirmed Problems and Required Outcomes

| Priority | Confirmed problem | Required outcome |
|---|---|---|
| Blocker | Browser API preflight receives `405` | Configurable origin allowlist returns a valid CORS preflight for authenticated API calls. |
| Blocker | Store mutations and Quickstart tests report success without backend confirmation | Server-backed actions are asynchronous, surface errors, and update state only from successful responses. Offline seed data remains a read-only demo fallback. |
| High | Windows checkout can convert shell entrypoints to CRLF and break containers | Repository attributes force LF for shell entrypoints and a Windows CI check proves it. |
| High | Restore swallows `pg_restore` errors and can omit pgvector | Restore creates `vector` with the privileged role, restores the remaining archive as the database owner, verifies extension/schema/data, and exits nonzero on failure. |
| High | Consent `Turn on` toggles and can turn memory off | Consent sets the requested boolean idempotently through a tenant-scoped backend endpoint. |
| Medium | Migration selection bubbles and completion counts are hard-coded | Selection has valid non-nested controls and completion derives moved/skipped counts from the executed migration response. |
| Medium | Quickstart links to a removed Debugger route | Links target the PRD-authoritative Users/Trace Sheet experience. |
| Medium | Major user controls are prototypes or no-ops | Existing backend operations are wired; missing V0.1 app/key, consent, feedback, and team operations gain persisted endpoints. P1 controls are removed or explicitly disabled. |
| Low | Documentation and landing copy contradict the running implementation | README, evaluator instructions, and landing copy describe the demo and real-HMS modes accurately and reference existing branches/routes. |
| Warning | Development hydration was unreliable in controlled browsers | Invalid nested interaction markup is removed and both development and production browser sessions must hydrate and execute actions without console or React hydration errors. |

## Chosen Approach

Use an incremental V0.1 end-to-end closure rather than a UI-only patch or a
production identity rewrite. The backend remains FastAPI plus tenant API-key
authentication. The frontend continues to use the typed API client and
Zustand store. Each behavior is implemented behind the existing architecture,
with small additions where the PRD already exposes a control but no endpoint
exists.

This historical design was superseded during implementation: the browser now
uses a same-origin `/api/mp` gateway, and the evaluator API key remains in the
Next.js server runtime. A hosted operator session and RBAC layer remains
required before public production deployment.

## Backend Design

### CORS

`Settings` gains `cors_allowed_origins`, parsed from a comma-separated
`MP_CORS_ALLOWED_ORIGINS` value. Defaults cover only
`http://localhost:3000` and `http://127.0.0.1:3000`. `CORSMiddleware` allows
the authenticated methods and headers used by the API. Wildcard origins are
not combined with credentials. A route test sends the exact browser preflight
and asserts the allow-origin, allow-methods, and allow-headers response.

### Console Provisioning and API Keys

The existing `Tenant`, `App`, and `ApiKey` models remain authoritative. The
provisioning router adds tenant-scoped app list/detail endpoints and API-key
list/create/rotate endpoints.

- Key list responses never return the full secret. They return identity,
  label, environment, timestamps, and a masked suffix.
- Create and rotate return a full key exactly once.
- Rotation creates the replacement before deleting the old key in one
  transaction. The caller cannot accidentally revoke the only credential used
  for the in-flight request without receiving the replacement.
- Cross-tenant app and key IDs return `404` and write nothing.
- App and key mutations emit audit records.

### Consent

`PATCH /v1/users/{user_id}/consent` accepts an explicit `memory_enabled`
boolean. It is idempotent, tenant-scoped, and records an audit entry only when
state changes. Turning memory off prevents subsequent ingest/retrieve for the
user while preserving existing memories for later re-enablement; full deletion
continues to use the existing delete-user operation.

### Trace Feedback

Retrieval feedback is stored against an existing tenant-scoped
`RetrievalTrace`. A migration adds nullable structured feedback data with the
category (`useful`, `not_useful`, `wrong_memory`, or `should_not_use`), optional
memory ID, actor, and timestamp. `POST /v1/debug/traces/{trace_id}/feedback`
upserts one feedback decision per trace and memory. It rejects a memory that
was not in the trace projection. Feedback is returned by the trace endpoint so
the UI reflects persisted truth.

### Team and Invites

V0.1 gains tenant-scoped `TeamMember` and `TeamInvite` records. The API lists
members and pending invites and creates a time-limited invite with a hashed
token. The plaintext invite token is returned once in an acceptance URL. An
accept endpoint consumes a valid token once and creates the member. Owner,
Admin, and Support are the accepted roles. This implements the visible V0.1
team surface but does not introduce hosted login or authorization by team role;
tenant API-key authentication remains the console security boundary.

The token-bearing acceptance endpoint is the only new route exempted from
tenant API-key middleware. A matching `/invite/[token]` frontend route shows
the invited email and role, collects a display name, and consumes the token.
Expired, already-used, and unknown tokens render explicit failures and never
create a member.

### Restore Integrity

The restore script recreates each database, creates `vector` as the Postgres
administrator, filters only the archive entries that would recreate or comment
on the already-created extension, and restores all application objects as the
database owner. Temporary list files use `mktemp` and are removed by a trap.

After each database restore the script verifies:

1. the `vector` extension exists;
2. expected application schemas/tables exist;
3. an owner-role query can access them;
4. `pg_restore` returned zero.

Any failed check stops the script with a nonzero status. Success is not printed
until both databases pass.

## Frontend Design

### Backend-Authoritative Store

The API client exposes typed methods for every server-backed action. Store
actions return promises. UI callers await them and show success only after
resolution. Errors preserve the previous state and are converted into concise
actionable toasts.

Hydration may use seed records only when the health/read request fails. The
store records `dataMode: "live" | "offline-demo"`. In offline-demo mode,
server-backed writes reject with a standard unavailable error; they never
mutate seed state. Pages display the mode so a rendered demo cannot be mistaken
for persisted data.

### Existing Operations

- Quickstart creates/synchronizes the test user, performs a real ingest, and
  performs a real retrieve. Checklist state advances only from successful API
  responses.
- Memory edit, status transition, single delete, policy changes, migration,
  export, and delete-all call their existing backend endpoints and replace
  local state with returned data.
- Delete-all uses the existing atomic delete-user operation rather than a loop
  of optimistic deletes.
- Device binding follows register then bind using the returned pairing data;
  no timers simulate completion.
- App creation uses `POST /v1/apps`; the returned one-time key is displayed
  before navigation.

### Newly Backed Operations

- App pages hydrate from app/key list endpoints; new-key and rotate-key actions
  show the one-time replacement secret and refresh the masked list.
- Consent explicitly calls `setMemoryConsent(true)` or
  `setMemoryConsent(false)`.
- Team invitation copies the actual backend-issued URL and renders pending
  status.
- Trace feedback posts the selected category and renders the persisted choice.
- Clipboard success is reported only after `navigator.clipboard.writeText`
  resolves; failure is visible.

### UI Corrections

- The migration bucket header is a non-button disclosure containing a separate
  selection button, with propagation deliberately controlled.
- Selected, moved, skipped, and failed counts come from the live preview and
  execution responses. No dataset-size constant remains.
- All removed Debugger links point to `/console/memory/users`; clicking a row
  opens the existing Trace Sheet.
- Hard-coded production readiness, fake recent migrations, and fake device
  health are either derived from backend data or labelled sample data.
- P1 actions with no V0.1 contract are not rendered as active controls.

## Error and Transaction Rules

- A successful toast means a corresponding API request completed successfully.
- A server failure leaves visible client data unchanged and presents the API
  error code or a network-unavailable message.
- Backend lookups are tenant-scoped before mutation.
- Multi-row operations commit atomically or return an error.
- Full secrets and invite tokens are shown once and are never returned by list
  endpoints or written to logs.
- Offline demo mode never accepts a write.

## Test Strategy

Implementation follows red-green-refactor. Every production behavior begins
with a focused failing test that demonstrates the confirmed defect.

### Backend Tests

- Exact CORS preflight contract.
- App/key list, create, rotation, one-time secret behavior, audit, and tenant
  isolation.
- Idempotent consent plus ingest/retrieve enforcement.
- Trace feedback validation, persistence, update, and tenant isolation.
- Team invite creation, expiry, one-time acceptance, role validation, and
  tenant isolation.
- Existing backend suite remains green on SQLite and in Compose/Postgres.

### Frontend Tests

Add Vitest, jsdom, Testing Library, and user-event. Test the API client, store,
and critical controls with mocked HTTP responses:

- failed writes do not mutate state or advance Quickstart;
- successful writes update state from response data;
- offline-demo mode rejects writes;
- consent is idempotent;
- migration selection does not collapse its bucket and counts are dynamic;
- clipboard, app creation, key rotation, export, feedback, and invite success
  require resolved side effects;
- removed routes are absent from rendered links.

### Runtime and Browser Tests

Run the existing lint/build/Ruff/pytest gates, the Compose suite, and the demo
walkthrough. Add an integration script that exercises every new endpoint and
checks Postgres state. Browser verification runs against both `next dev` and
`next start`, with the real backend, and asserts:

- no failed preflights, console errors, or hydration errors;
- Quickstart writes and retrieves real records;
- CRUD, consent, policy, migration, export, device binding, app/key, feedback,
  and team actions survive a reload;
- destructive actions are verified against API and database state.

Restore verification uses a backup containing MP and HMS data, restores into
the running local stack, and proves vector availability plus row-count parity.
A Windows CI job checks a fresh autocrlf-enabled checkout for LF shell scripts.

## Documentation and Completion Evidence

The validation report becomes a living remediation matrix. Each issue records
the fixing commit, focused red/green test, full-suite result, and runtime proof.
README and evaluator documentation describe the checked-out `main` branch,
the deterministic demo engine, the credentialed real-HMS overlay, browser key
limitations, and working routes only.

Completion requires all focused tests, full frontend/backend suites, Compose
health, demo script, browser matrix, Windows line-ending gate, backup/restore
round trip, and a final source search for dead routes and success-only stubs.
No issue is closed solely because code was written.
