# Memory Passport V0.1 Validation Remediation Implementation Plan

> Execute sequentially with red-green-refactor. Do not change production code
> for a behavior until its focused test has failed for the expected reason.

**Goal:** Resolve every issue in `docs/validation-report-2026-07-22.md`, replace
false-positive frontend actions with backend-authoritative behavior, and prove
the repaired product through unit, integration, browser, Windows, and restore
validation.

**Design:** `docs/specs/2026-07-22-validation-remediation-design.md`

**Architecture:** Keep FastAPI, SQLAlchemy/Alembic, tenant API-key auth, typed
frontend API client, and the single Zustand store. Add only V0.1 contracts.
Offline seed data remains available for rendering but is read-only.

**Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL/pgvector,
pytest/respx, Next.js 16, React 19, TypeScript, Zustand, Vitest, Testing Library,
Docker Compose.

---

## Task 1: Freeze the Defect Matrix and Baseline

**Files:**

- Modify: `docs/validation-report-2026-07-22.md`
- Create: `artifacts/remediation-2026-07-22/baseline.txt`

1. Add a remediation table with one row for each of the ten report findings.
   Columns: issue, acceptance evidence, focused test, status, commit, runtime
   proof. Initial status is `open`.
2. Record `git rev-parse HEAD`, Compose status, health JSON, authenticated
   memory total, current preflight status, frontend URL status, and current
   pytest/lint/build summaries in the baseline artifact.
3. Confirm the preflight is red:

   ```powershell
   curl.exe -i -X OPTIONS http://127.0.0.1:8000/v1/memories `
     -H "Origin: http://127.0.0.1:3000" `
     -H "Access-Control-Request-Method: GET" `
     -H "Access-Control-Request-Headers: authorization"
   ```

   Expected: `405 Method Not Allowed`; record it as the blocker reproduction.

4. Commit only the remediation table and baseline artifact.

## Task 2: Add the Exact CORS Contract

**Files:**

- Create: `backend/tests/test_cors.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `backend/README.md`

1. Write a test that sends `OPTIONS /v1/memories` with origin
   `http://127.0.0.1:3000`, requested method `GET`, and requested header
   `authorization`. Assert `200`, the exact allow-origin value, allowed method,
   and allowed header.
2. Add tests that an unlisted origin gets no allow-origin header and that
   `Settings` trims/deduplicates comma-separated origins.
3. Run the focused test and confirm failure because the app returns `405`.

   ```powershell
   Set-Location backend
   .\.venv\Scripts\python.exe -m pytest tests/test_cors.py -q
   ```

4. Add `cors_allowed_origins` and a parsed origin-list property to `Settings`.
   Configure `CORSMiddleware` before auth middleware with only the required
   methods and `Authorization`/`Content-Type` headers.
5. Document and pass `MP_CORS_ALLOWED_ORIGINS` in local configuration.
6. Re-run `test_cors.py`, then `test_auth.py` and `test_health.py`.
7. Restart `mp-backend` and repeat the real preflight. Expected: `200` and
   `access-control-allow-origin: http://127.0.0.1:3000`.
8. Commit as `fix: allow configured browser API origins`.

## Task 3: Make Windows Checkouts and Restore Deterministic

**Files:**

- Create: `.gitattributes`
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/restore.sh`
- Create: `scripts/verify-line-endings.ps1`
- Create: `scripts/verify-restore.sh`
- Modify: `README.md`
- Modify: `docs/local-evaluation.md`

### Line endings

1. Write `verify-line-endings.ps1` to inspect every tracked `*.sh`, Dockerfile,
   and configured entrypoint and exit nonzero if CRLF is present.
2. Run it against a temporary autocrlf-enabled clone before attributes are
   added and capture the expected failure.
3. Add repository attributes forcing LF for shell scripts and Dockerfiles while
   leaving normal text files platform-neutral.
4. Add a `windows-latest` CI job that sets `core.autocrlf=true`, checks out,
   runs the verifier, and runs `bash -n` on every tracked shell script.
5. Recreate the temporary clone and confirm both checks pass.

### Restore

6. Run `scripts/backup.sh`; record MP/HMS row counts and vector extension
   presence. Execute the current restore once and capture its nonzero
   `pg_restore`/vector warning as the focused red reproduction.
7. Change restore to:
   - use a `mktemp` list per archive with a cleanup trap;
   - recreate the DB and create `vector` as the Postgres administrator;
   - filter only `EXTENSION ... vector` and its extension comment from the
     archive list;
   - restore the remaining entries with `--use-list`, `--no-owner`, and
     `--role=<db-owner>`;
   - never catch and ignore a nonzero `pg_restore`;
   - verify vector, expected tables/schemas, owner access, and row counts.
8. Implement `verify-restore.sh` to perform backup, destructive confirmed
   restore, extension checks, and before/after row-count parity for both DBs.
9. Run the verifier against the live stack. Expected: exit `0`, zero restore
   warnings, vector present, exact row-count parity, health returns to green.
10. Commit as `fix: make checkout and restore portable`.

## Task 4: Add the V0.1 Console Persistence Schema

**Files:**

- Create: `backend/tests/test_console_schema.py`
- Create: `backend/app/models/team.py`
- Modify: `backend/app/models/retrieval_trace.py`
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/services/ids.py`
- Create: `backend/alembic/versions/0010_validation_remediation.py`
- Modify: `backend/app/seed/data.py`
- Modify: `backend/app/seed/run_seed.py`
- Modify: `backend/tests/test_migrations.py`
- Modify: `backend/tests/test_seed.py`

1. Write model tests for `TeamMember`, `TeamInvite`, retrieval feedback JSON,
   invite uniqueness, token-hash uniqueness, and required timestamps.
2. Extend migration tests to require a clean upgrade/downgrade through `0010`
   and seed tests to require the canonical Luna team rows.
3. Run the focused tests; confirm import/table/column failures.
4. Add audit enum values for API-key creation/rotation, consent change,
   retrieval feedback, team invite, and team join.
5. Add opaque IDs for team members and invites.
6. Add the two team models and nullable retrieval feedback field. Register all
   models in `app.models`.
7. Write `0010` to add Postgres audit enum literals, both team tables, indexes,
   constraints, and the JSONB feedback column. Downgrade removes tables/column;
   enum values remain documented as Postgres-safe irreversible literals.
8. Seed the three Luna team members idempotently.
9. Run focused SQLite tests, then Compose-backed migration and seed tests.
10. Commit as `feat: persist console team and feedback data`.

## Task 5: Implement App, API-Key, and Policy Reads

**Files:**

- Create: `backend/tests/test_console_apps.py`
- Modify: `backend/app/schemas/provisioning.py`
- Modify: `backend/app/services/provisioning.py`
- Modify: `backend/app/api/v1/apps.py`
- Modify: `backend/app/api/v1/policies.py`
- Modify: `backend/app/services/policies.py`

1. Write route tests for:
   - tenant-scoped `GET /v1/apps` and `GET /v1/apps/{id}`;
   - masked keys in list/detail responses;
   - full secret returned only by key create/rotate;
   - new key persistence and audit;
   - rotation invalidating the old key and preserving the replacement;
   - cross-tenant app/key IDs returning `404`;
   - `GET /v1/policies?app_id=&agent_id=` returning the persisted policy or
     `404` without a write.
2. Run the new tests and confirm `405`/`404` failures on absent routes.
3. Add masked response schemas separate from the existing one-time
   `ApiKeyResponse`.
4. Add tenant-scoped service lookups, lists, key creation, and atomic rotation.
5. Add the routes and audits. The route returns the replacement key before the
   old credential can be needed again.
6. Add the side-effect-free policy read route.
7. Run focused tests plus existing provisioning, policy, auth, and aggregate
   suites.
8. Commit as `feat: expose live apps keys and policies`.

## Task 6: Implement Idempotent Consent and Enforce It

**Files:**

- Create: `backend/tests/test_consent.py`
- Modify: `backend/app/schemas/provisioning.py`
- Modify: `backend/app/services/provisioning.py`
- Modify: `backend/app/api/v1/users.py`
- Modify: `backend/app/services/ingest.py`
- Modify: `backend/app/services/retrieve.py`

1. Write tests that `PATCH /v1/users/{id}/consent` sets explicit true/false,
   repeating the same value is idempotent, only a state change writes an audit,
   and cross-tenant users return `404`.
2. Write ingest/retrieve tests proving disabled users cannot create or retrieve
   memories and HMS is not called. Use the existing public error conventions.
3. Run tests and confirm route absence plus missing enforcement.
4. Add request schema, tenant-scoped service method, route, and audit.
5. Check consent before HMS in ingest/retrieve. Return `409 memory_disabled`
   with a clear message.
6. Run focused tests and the full ingest/retrieve/data-ops suites.
7. Commit as `feat: persist and enforce memory consent`.

## Task 7: Implement Trace Feedback and Team Invites

**Files:**

- Create: `backend/tests/test_trace_feedback.py`
- Create: `backend/tests/test_team.py`
- Create: `backend/app/schemas/team.py`
- Modify: `backend/app/schemas/retrieve.py`
- Create: `backend/app/services/team.py`
- Modify: `backend/app/services/retrieve.py`
- Create: `backend/app/api/v1/team.py`
- Modify: `backend/app/api/v1/debug.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/auth/__init__.py`

### Feedback

1. Test accepted categories, projected-memory validation, upsert behavior,
   persisted trace response, audit, and tenant isolation.
2. Confirm the absent endpoint fails.
3. Add feedback schemas/service/route and return feedback from trace reads.

### Team

4. Test authenticated member/pending-invite lists, invite email normalization,
   allowed roles, hashed token storage, plaintext token returned once, expiry,
   already-used rejection, public preview/accept, one created member, and
   cross-tenant isolation.
5. Confirm absent routes/models fail.
6. Implement authenticated `/v1/team` and `/v1/team/invites`, plus public
   `/v1/public/team-invites/{token}` preview/accept routes. Only the public
   prefix bypasses API-key auth.
7. Store only SHA-256 token hashes, compare constant-time, consume atomically,
   and audit invite/join events.
8. Run both focused suites plus auth, aggregates, migrations, and seed tests.
9. Commit as `feat: persist feedback and team invitations`.

## Task 8: Establish Frontend Red-Green Testing and Typed Contracts

**Files:**

- Modify: `package.json`
- Modify: `pnpm-lock.yaml`
- Create: `vitest.config.ts`
- Create: `src/test/setup.ts`
- Create: `src/lib/api-client.test.ts`
- Modify: `src/lib/types.ts`
- Modify: `src/lib/api-client.ts`
- Modify: `.github/workflows/ci.yml`

1. Install pinned-compatible Vitest, jsdom, Testing Library React,
   `@testing-library/jest-dom`, and user-event dev dependencies. Add `test` and
   `test:watch` scripts.
2. Configure jsdom, the `@/` alias, jest-dom, cleanup, fetch mocks, clipboard,
   and deterministic timers.
3. Write red API-client tests for every added endpoint and existing unexposed
   operation: apps/keys, policy read, consent, export poll/download, delete
   user, devices, feedback, team, ingest, retrieve, memory CRUD, and migration.
4. Test structured `ApiError` parsing and runtime replacement of the current
   evaluator key after rotating that same credential.
5. Run `pnpm test -- src/lib/api-client.test.ts` and confirm missing-method
   failures.
6. Add domain types and typed client methods. Download uses authenticated fetch
   to a Blob rather than unauthenticated browser navigation.
7. Re-run focused tests, `pnpm lint`, and `pnpm build`.
8. Add `pnpm test --run` to Linux CI.
9. Commit as `test: add frontend contract coverage`.

## Task 9: Make the Store Backend-Authoritative

**Files:**

- Create: `src/store/memory-store.test.ts`
- Modify: `src/store/memory-store.ts`
- Modify: `src/components/store-hydrator.tsx`

1. Reset the Zustand store between tests and write red tests for:
   - live versus offline-demo hydration;
   - every failed mutation preserving prior state;
   - offline writes rejecting without local mutation;
   - Quickstart advancing only after real user/ingest/retrieve responses;
   - policy/migration state coming from response bodies;
   - delete-all using one atomic delete-user request;
   - idempotent consent;
   - app/key/team/feedback/device/export actions returning usable results.
2. Run the store test and confirm current optimistic/fake behavior fails.
3. Add `dataMode` and a standard unavailable error. Convert server-backed
   actions to `Promise` results and remove fire-and-forget calls.
4. On hydrate, fetch independent live resources with explicit failure rules;
   enter live mode only when the core health and memory reads succeed.
5. Update state only with successful response data. Do not append local test
   memories or hard-code completed migrations.
6. Re-run store/API-client tests, lint, and build.
7. Commit as `fix: make frontend state follow backend truth`.

## Task 10: Wire the B-Side Console

**Files:**

- Create: `src/app/console/apps/new/page.test.tsx`
- Create: `src/app/console/apps/[id]/page.test.tsx`
- Create: `src/app/console/quickstart/page.test.tsx`
- Create: `src/app/console/settings/page.test.tsx`
- Create: `src/components/memory/MemoryTraceSheet.test.tsx`
- Modify: `src/app/console/apps/new/page.tsx`
- Modify: `src/app/console/apps/[id]/page.tsx`
- Modify: `src/app/console/apps/page.tsx`
- Modify: `src/app/console/quickstart/page.tsx`
- Modify: `src/app/console/settings/page.tsx`
- Modify: `src/components/memory/MemoryTraceSheet.tsx`
- Modify: `src/app/console/devices/page.tsx`
- Modify: `src/app/console/page.tsx`

1. Write user-event tests proving:
   - App creation awaits the API, displays the one-time key, and does not
     navigate on error;
   - key copy awaits clipboard, new-key/rotation refresh lists, and failures
     do not claim success;
   - Quickstart buttons await real calls and removed Debugger links are absent;
   - invite copies a real issued URL and renders pending state;
   - feedback persists and re-renders selected state;
   - integration/health cards reflect store data rather than all-true constants.
2. Run focused tests and observe current false positives.
3. Wire pages exclusively through store actions. Add loading/disabled states,
   one-time-secret dialogs, and error toasts.
4. Replace every `/console/memory/debugger` link with
   `/console/memory/users`.
5. Remove fake recent migration rows and hard-coded readiness, or visibly label
   remaining visual examples as sample data.
6. Re-run component/store tests, lint, and build.
7. Commit as `fix: wire console actions to live services`.

## Task 11: Wire the C-Side and Correct Migration UI

**Files:**

- Create: `src/app/app/consent/page.test.tsx`
- Create: `src/app/app/devices/bind/page.test.tsx`
- Create: `src/app/app/migrate/page.test.tsx`
- Create: `src/app/app/migrate/complete/page.test.tsx`
- Create: `src/app/app/memory/page.test.tsx`
- Create: `src/app/invite/[token]/page.test.tsx`
- Modify: `src/app/app/consent/page.tsx`
- Modify: `src/app/app/devices/bind/page.tsx`
- Modify: `src/app/app/migrate/page.tsx`
- Modify: `src/app/app/migrate/complete/page.tsx`
- Modify: `src/app/app/memory/page.tsx`
- Modify: `src/app/app/memory/[id]/page.tsx`
- Modify: `src/app/app/memory/delete/page.tsx`
- Create: `src/app/invite/[token]/page.tsx`

1. Write red component tests for explicit consent, register/bind response use,
   migration selection without disclosure bubbling, dynamic moved/skipped/
   failed counts, export Blob download, atomic delete-all, and invite
   preview/accept error states.
2. Confirm current toggle/timer/hard-coded/no-op behavior fails.
3. Await store actions in every handler; success toasts/navigation occur only
   after resolution. Preserve the previous UI on errors.
4. Replace the migration nested button pattern and derive counts from preview
   and execution data. Remove the `38 - movedCount` constant.
5. Implement the invite acceptance screen and explicit expired/used/unknown
   states.
6. Re-run focused tests, all frontend tests, lint, and build.
7. Commit as `fix: persist user memory and migration actions`.

## Task 12: Correct Documentation, Copy, and Hydration

**Files:**

- Modify: `README.md`
- Modify: `CUSTOMER_QUICKSTART.zh-CN.md`
- Modify: `B2B_CUSTOMER_GUIDE.zh-CN.md`
- Modify: `docs/local-evaluation.md`
- Modify: `docs/real-hms.md`
- Modify: `src/app/page.tsx`
- Modify: `CLAUDE.md`

1. Write a source check that fails on removed Debugger routes, nonexistent HMS
   branch instructions, the landing claim that no backend exists, and active
   buttons whose handler contains only a toast/timer.
2. Update docs to use the real `main` branch/submodule workflow and distinguish
   deterministic demo HMS from credentialed real HMS.
3. State that the browser key is evaluator-only and production requires a
   server-side session/BFF boundary.
4. Update landing/footer copy to describe the running backend accurately.
5. Read the relevant Next.js 16 App Router and hydration guides under
   `node_modules/next/dist/docs/` before any hydration-specific edit.
6. Run `pnpm dev` in a fresh process and inspect console/network/UI in the
   controlled browser. Fix only reproducible source causes. Repeat with
   `pnpm build && pnpm start`.
7. Run the source check, all frontend tests, lint, and build.
8. Commit as `docs: align product claims with live behavior`.

## Task 13: Full Runtime Verification and Completion Audit

**Files:**

- Create: `scripts/validate-remediation.ps1`
- Create: `artifacts/remediation-2026-07-22/api-results.json`
- Create: `artifacts/remediation-2026-07-22/browser-results.md`
- Create: `artifacts/remediation-2026-07-22/restore-results.txt`
- Modify: `docs/validation-report-2026-07-22.md`
- Modify: `docs/issue-acceptance.md`

1. Build a repeatable PowerShell live matrix covering health/auth/CORS,
   provisioning, app/key, user/consent, device, relationship, ingest, retrieve,
   trace/feedback, CRUD, policy, migration/rollback, usage/audit, export,
   delete-user, and team invites. Each mutation is followed by a GET and direct
   Postgres assertion where applicable.
2. Run from a clean seeded stack:

   ```powershell
   pnpm test --run
   pnpm lint
   pnpm build
   Set-Location backend
   .\.venv\Scripts\python.exe -m ruff check app tests
   .\.venv\Scripts\python.exe -m pip check
   .\.venv\Scripts\python.exe -m pytest -q
   Set-Location ..
   docker compose up -d --build --wait
   docker compose exec -T mp-backend pytest -q
   bash scripts/demo.sh
   powershell -ExecutionPolicy Bypass -File scripts/validate-remediation.ps1
   bash scripts/verify-restore.sh
   ```

3. Exercise every visible B-side and C-side control in both Next development
   and production modes. Record network status, persisted reload result, API/
   DB evidence, console errors, and hydration errors.
4. Test a backend-down session: read-only demo data renders, every write is
   blocked, and no success toast appears.
5. Verify a temporary autocrlf-enabled fresh clone with the Windows line-ending
   script and shell syntax checks.
6. Search tracked frontend source for dead internal routes, un-awaited store
   writes, success-only toast handlers, and timer-simulated mutations. Inspect
   every match; zero unexplained product-action stubs are allowed.
7. Update each validation-report row with exact commands, outputs, commits, and
   evidence paths. Retain honest limitations for real HMS provider calls, TLS,
   hosted auth/BFF, and P1 RBAC.
8. Re-run `git diff --check`, inspect the complete diff and status, and perform
   a requirement-by-requirement audit against the design and original report.
9. Commit final validation evidence as `test: verify full remediation matrix`.

The goal is complete only when all report rows are `verified`, all listed gates
pass from current state, and the browser/API/database evidence agrees.
