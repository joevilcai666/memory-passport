# Memory Passport complete runtime and product validation

Date: 2026-07-22 (Asia/Shanghai)

Repository: `https://github.com/joevilcai666/memory-passport.git`

Validated commit: `774be0d9d5fc720bd2d667c5e6db4fb3a4e13420` (`main`)
HMS submodule: `vendor/hms` at `aa2035b4074ecb394d76243e59ae537e014a7ac7`

## Executive verdict

The repository can be installed, built, and run locally. The default Docker backend is healthy, its complete container test suite passes, and an independent 95-case live HTTP matrix passes. The production frontend also builds and all product routes render and hydrate.

The product is **not currently complete end-to-end in a normal browser**. The frontend cannot reach the running backend because the FastAPI service does not allow the required CORS preflight. It falls back to seed data, after which many workflows show optimistic or simulated success without persistence. This affects Quickstart, memory edits/deletes, delete-all, policies, device binding, migration, audit, exports, and several console operations.

Practical answer:

- Backend/demo API: **YES — runnable and thoroughly passing.**
- Frontend rendering and local interactions: **YES — production build works.**
- Frontend ↔ backend product loop: **NO — blocked by CORS and prototype/local-only handlers.**
- Real HMS with live LLM/embedding providers: **CONFIGURATION VALIDATED, LIVE INFERENCE NOT TESTED** because real provider credentials were not supplied.
- Public TLS deployment: **CONFIGURATION VALIDATED, LIVE CERTIFICATE/DNS NOT TESTED** because no public domain/DNS was supplied.

## Remediation status

Implementation design: `docs/specs/2026-07-22-validation-remediation-design.md`

TDD plan: `docs/plans/2026-07-22-validation-remediation-implementation.md`

Remediation baseline: `artifacts/remediation-2026-07-22/baseline.txt`

| # | Issue | Acceptance evidence | Focused test | Status | Commit | Runtime proof |
|---|---|---|---|---|---|---|
| 1 | Browser CORS preflight blocked | Allowed local origin receives valid preflight; unlisted origin does not | `backend/tests/test_cors.py` | open | — | baseline currently returns `401` before route dispatch |
| 2 | False-positive frontend success | Failed/skipped requests never mutate state or show success; successful state survives reload | API-client, store, component, browser tests | open | — | API and Postgres assertions pending |
| 3 | Windows CRLF breaks shell entrypoints | Autocrlf-enabled fresh clone retains LF and passes `bash -n` | `scripts/verify-line-endings.ps1` + Windows CI | open | — | fresh-clone proof pending |
| 4 | Restore can omit pgvector and swallow failure | Restore exits zero only with vector, owner access, and exact row parity | `scripts/verify-restore.sh` | open | — | destructive round trip pending |
| 5 | Consent action toggles the wrong direction | Explicit true/false is idempotent and enforced by ingest/retrieve | `backend/tests/test_consent.py` + component test | open | — | API/DB proof pending |
| 6 | Migration selection/count defects | Selection does not collapse bucket; counts derive from preview/execute responses | migration component/store tests | open | — | browser persistence proof pending |
| 7 | Removed Debugger route is linked | No tracked link targets the removed route; Users Trace Sheet opens | Quickstart component/source tests | open | — | browser navigation proof pending |
| 8 | Major actions are no-ops | V0.1 actions call persisted endpoints or are not active controls | console/C-side API, store, component tests | open | — | full visible-control matrix pending |
| 9 | Documentation/product copy drift | All commands, branches, routes, engine claims, and browser-key limits match runtime | documentation source check | open | — | clean-clone walkthrough pending |
| 10 | Development hydration warning | Development and production sessions hydrate with zero React/console errors | browser matrix | open | — | controlled-browser proof pending |

Historical evidence below describes commit `774be0d`. The remediation table is
updated only when current focused tests and runtime evidence prove an item.

## What the product is

Memory Passport is a user-owned portable memory layer for AI companions and robots. It exposes:

- a B-side Next.js operator console under `/console/*`;
- a C-side embedded user experience under `/app/*`;
- a FastAPI control/data plane with tenant-scoped bearer authentication;
- policy-controlled memory ingest/retrieve/edit/delete;
- device registration, binding, wipe, and generation migration;
- audit logs, usage aggregates, model-neutral export, and user deletion;
- an HMS-compatible memory-engine boundary.

The default evaluator mode is credential-free:

`Next.js UI → FastAPI Memory Passport → deterministic HMS-compatible demo service → PostgreSQL/pgvector`

It validates orchestration and lifecycle behavior, but it is not live semantic LLM/embedding inference. The real overlay adds the vendored HMS API and worker and requires LLM, light-LLM, and embedding credentials.

## Environment installed inside this folder

- Node.js runtime discovered from the local Codex workspace runtime.
- pnpm 10.34.5 through Corepack; cache kept under `node_modules/.cache/corepack`.
- 453 frontend packages installed with the frozen lockfile.
- Python 3.11.9 virtual environment at `backend/.venv`.
- 42 compatible Python packages in the final environment check.
- Docker Desktop / Engine 29.6.1.
- `.env` created from `.env.example` and kept ignored.
- Runtime/cache material kept under ignored project paths (`node_modules`, `backend/.venv`, `.zcode`, `backups`).

No product source code was modified. The only tracked-area additions are this report and the test plan; test artifacts are under `artifacts/validation-2026-07-22`.

## How to run it now

The final Docker state is the clean Luna seed: 1 tenant, 1 app, 4 users, 4 devices, 1 policy, 6 rules, 42 memories, 1 preview migration, and 8 audit rows. All three default services are healthy.

Backend stack:

```powershell
docker compose up -d --wait --remove-orphans
docker compose exec -T mp-backend alembic upgrade head
docker compose exec -T mp-backend python -m app.seed.run_seed
```

Frontend development mode:

```powershell
$env:COREPACK_HOME = (Resolve-Path 'node_modules\.cache\corepack').Path
& 'D:\software_data\NodeJS\corepack.cmd' pnpm@10 dev
```

Frontend release mode:

```powershell
$env:COREPACK_HOME = (Resolve-Path 'node_modules\.cache\corepack').Path
& 'D:\software_data\NodeJS\corepack.cmd' pnpm@10 build
& 'D:\software_data\NodeJS\corepack.cmd' pnpm@10 start
```

Local endpoints:

- Frontend: `http://127.0.0.1:3000`
- Backend health: `http://127.0.0.1:8000/v1/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Demo HMS health/API: `http://127.0.0.1:18080`

Important: until CORS is fixed, the frontend will show the offline Luna dataset even while the backend is green.

## Fresh verification results

| Layer | Command/scope | Result |
|---|---|---|
| Frontend lint | `pnpm lint` | PASS, zero errors. |
| Frontend release build | `pnpm build` | PASS; Next.js 16.2.10, TypeScript PASS, 19 generated routes including `_not-found`. |
| Backend lint | `ruff check backend/app backend/tests` | PASS. |
| Python dependencies | `uv pip check --python backend/.venv/Scripts/python.exe` | PASS; 42 packages compatible. |
| Host backend tests | Service-independent host run | 152 passed, 10 service-dependent skipped. |
| Full container tests | `docker compose exec -T mp-backend pytest -q` | PASS; 162/162 (72 + 72 + 18), no skips/failures. |
| Independent live API matrix | `live_api_matrix.py` | PASS; 95/95, 0 failed, run `matrix-f536361b49`. |
| Documented local demo | `scripts/demo.sh` | PASS; complete health/ingest/retrieve/edit/export/delete/audit/usage flow. |
| Default service health | Compose health checks + `/v1/health` | PASS; PostgreSQL, HMS demo, and MP backend all healthy; `memory_engine=demo`. |
| Seed idempotence | Seed executed twice | PASS; counts stayed exactly at the expected Luna dataset. |
| Frontend browser sweep | All 18 product route families, desktop and 390×844 mobile | Routes render; local UI interactions PASS; browser/backend integration FAIL. |

The independent live matrix covers:

- health, Swagger, and all 26 documented OpenAPI operations;
- missing/bad/bare/Bearer authentication behavior;
- app, agent, user, relationship, and idempotent provisioning;
- device register/bind/unbind/wipe and wrong/duplicate/missing cases;
- policy validation, block/confirm/auto-write paths;
- candidate and active ingest;
- scoped retrieval, wiped-device exclusion, and debug trace;
- memory filters, pagination, versioned edit, state transitions, tombstones;
- migration preview, idempotence, execute, old-device removal, lookup, rollback;
- audit logs and usage;
- export polling, token validation, model-neutral format, one-shot download;
- delete-user cascade and post-delete empty retrieval.

Cross-tenant isolation is covered by the 162-test suite. The live matrix did not provision a second tenant because there is no public second-tenant creation endpoint.

## Frontend coverage summary

All release routes were exercised:

- landing: `/`;
- operator: `/console`, `/console/quickstart`, `/console/apps`, `/console/apps/new`, `/console/apps/app_luna`, `/console/memory/policy`, `/console/memory/users`, `/console/devices`, `/console/settings`;
- user: `/app/consent`, `/app/memory`, `/app/memory/mem_001`, `/app/memory/delete`, `/app/devices`, `/app/devices/bind`, `/app/migrate`, `/app/migrate/complete`;
- invalid/missing: standard not-found and the product-linked `/console/memory/debugger`.

Detailed interaction evidence is in `artifacts/validation-2026-07-22/frontend-functional-results.md`.

## Confirmed issues

### 1. BLOCKER — frontend cannot call the backend from a browser

Evidence:

- `src/lib/api-client.ts` targets `http://127.0.0.1:8000` and adds `Authorization` to every request.
- The FastAPI app contains no `CORSMiddleware` configuration.
- Browser preflight:

```text
OPTIONS /v1/health
Origin: http://127.0.0.1:3000
Access-Control-Request-Headers: authorization

HTTP/1.1 405 Method Not Allowed
Allow: GET
```

- The UI then shows `Backend offline — showing demo data`.

Impact: the README says the console is wired to the real backend, but a normal browser cannot establish that loop.

### 2. BLOCKER — multiple workflows produce false-positive success

Confirmed browser/UI result versus backend truth:

- Quickstart announces a created memory and successful retrieval; backend remains at 42 records and has no `mem_quickstart`.
- UI edit of `mem_001` shows version 2; backend remains original version 1.
- UI archive/delete of `mem_030` changes the row; backend remains active.
- Delete-all shows zero memories; backend remains at 42.
- Policy UI shows changed axes/limits; database policy remains unchanged.
- Migration completion shows 33 moved; database migration remains preview with zero selected.

The store intentionally skips backend calls after the CORS-blocked ping, so these are not merely delayed writes.

### 3. HIGH — Windows default checkout breaks Docker initialization

The repository has shell scripts stored as LF but no `.gitattributes`. This machine has global `core.autocrlf=true`, so a normal checkout converted five `.sh` files to CRLF. The documented Compose flow then failed with:

```text
/usr/bin/env: ‘bash\r’: No such file or directory
```

The database init script did not create the `mp` and `hms` roles, and HMS became unhealthy. I set repository-local `core.autocrlf=false` and normalized the shell-script working copies to LF. Git reports no source diff, but a fresh Windows user can hit the same failure until the repository adds line-ending policy.

### 4. HIGH — backup passes, restore is only partial for pgvector

Backup succeeded and created:

- `backups/20260722T033250Z/memory_passport.dump` — 71,180 bytes;
- `backups/20260722T033250Z/hms.dump` — 5,186 bytes.

Restore preserved the tested MP/HMS data counts and health returned green, but `pg_restore` under the non-superuser `mp`/`hms` roles could not create the `vector` extension. It logged permission-denied and missing-extension-comment errors, downgraded the restore failure to a warning, and continued. Health does not verify that pgvector was restored. A restore must not be considered complete from the current script's final message alone.

### 5. HIGH — consent `Turn on` can turn memory off

The seeded user starts with memory enabled. `/app/consent` always calls `toggleMemoryEnabled()` rather than setting true. Clicking `Turn on` produced a success toast but navigated to Memory Center showing `Paused`.

### 6. MEDIUM — migration UI has selection and count defects

- `Select all` is a button nested inside another role=button header; its click bubbles and collapses the recommendation bucket.
- Completion uses `Math.max(0, 38 - movedCount)` although the preview displays 39 total items. Moving 33 while leaving five device-local and one portable deselected reports 5 skipped instead of 6.

### 7. MEDIUM — Quickstart links to a nonexistent debugger

`/console/memory/debugger` is linked from the Quickstart next-steps and completion callout but is not a generated route. It returns the standard 404.

### 8. MEDIUM — major console/user actions are prototypes or no-ops

- Create app only routes to Quickstart and does not create an app.
- New key and Roll key have no handlers; the production key is a masked placeholder.
- Memory export, migration report export, migration retry, trace feedback, and device binding are toast/local simulations.
- Invite member says a link was copied but writes nothing to the clipboard.
- Quickstart retrieve only flips local state; it never calls `api.retrieveMemories`.
- Integration badges and several dashboard/device KPIs are hard-coded or seeded.

### 9. LOW — documentation and product-copy drift

- README/evaluation instructions reference checking out an `HMS` branch, but the remote currently exposes `main` only.
- The Makefile assumes Unix paths/tools; native Windows has no `make` here, so PowerShell users must run the underlying commands.
- The landing footer says `Prototype · seeded with the Luna dataset · no real backend`, despite this repository containing and running a real FastAPI backend.

### 10. WARN — unresolved `next dev` hydration behavior in controlled browsers

Both controlled browsers initially received the `next dev` server-rendered page but did not attach client interactions. An isolated browser control page executed inline/external scripts and click handlers, while `next start` hydrated normally. This is not a production-build failure, but the development/Turbopack path should be reproduced outside the controlled browser before relying on it.

## Backup, real-HMS, and TLS boundaries

| Area | Result | Boundary |
|---|---|---|
| Backup | PASS | Both databases dumped with nonzero artifacts. |
| Restore | PARTIAL | Data returned and health was green, but pgvector extension restoration failed under non-superuser roles. |
| Real-HMS credential validation | PASS fail-closed | Default `.env` is rejected with a precise missing-credential error; a non-placeholder validation environment passes. |
| Real-HMS Compose render | PASS | `postgres`, `hms-api`, `hms-worker`, `mp-backend`; MP mode renders as `real`. |
| Real-HMS live inference | NOT RUN | No real LLM/light-LLM/embedding provider credentials were supplied. |
| TLS Compose render | PASS | Caddy renders with 80/443, and backend host publication is removed behind the proxy. |
| Public HTTPS | NOT RUN | No controlled public domain, DNS, or certificate issuance target was supplied. |
| Physical QR/camera/hardware | NOT RUN | The current browser UI is a timer-based simulation; backend device APIs were tested directly. |

## Workspace and source integrity

- Clone origin and commit were verified.
- HMS submodule was initialized and pinned.
- Product source files were not changed.
- `.env`, virtualenv, dependency caches, Docker data, and backup artifacts remain ignored.
- The repository-local line-ending setting and LF normalization are environment fixes; `git diff` reports no product source changes.
- Expected untracked deliverables are `docs/plans`, this validation report, and `artifacts/validation-2026-07-22`.

## Recommended release order

1. Add explicit CORS policy for the supported frontend origins and test preflight/authenticated browser requests.
2. Make Quickstart, edit/delete, delete-all, policy, migration, export, invite, key management, device binding, and feedback report backend truth rather than optimistic demo truth.
3. Add frontend end-to-end tests that assert both UI state and database/API state.
4. Add `.gitattributes` enforcing LF for shell/entrypoint scripts and validate a fresh Windows clone in CI.
5. Make restore create/verify pgvector with the required privilege or restore into a database where the extension is pre-created, and fail nonzero when restore is incomplete.
6. Fix consent idempotence, migration skipped-count logic, nested interactive markup, and the broken debugger route.
7. Only then treat real-HMS provider validation and public TLS as release gates.

## Evidence files

- `docs/plans/2026-07-22-complete-product-validation.md`
- `artifacts/validation-2026-07-22/live_api_matrix.py`
- `artifacts/validation-2026-07-22/live_api_results.json`
- `artifacts/validation-2026-07-22/frontend-functional-results.md`
- `backups/20260722T033250Z/memory_passport.dump`
- `backups/20260722T033250Z/hms.dump`
