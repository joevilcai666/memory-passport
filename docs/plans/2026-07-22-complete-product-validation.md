# Memory Passport Complete Product Validation Plan

**Goal:** Reproduce a clean local installation inside this repository, run every shipped release gate, exercise every backend API family and every frontend route/action, and report successes, failures, and unverified external boundaries with reproducible evidence.

**Architecture:** The default local system is a Next.js 16 browser client on port 3000, a FastAPI Memory Passport service on port 8000, a deterministic HMS-compatible service on port 18080, and PostgreSQL/pgvector in Docker. Frontend state hydrates from the FastAPI service and falls back to seeded demo state only when the service is unavailable. The optional real-HMS overlay replaces the deterministic service with the pinned `vendor/hms` API and worker and requires external LLM, retain-LLM, and embedding credentials.

**Tech Stack:** Node.js 22+ and pnpm 10+; Next.js 16.2.10, React 19.2.4, TypeScript, ESLint; Python 3.11, uv, FastAPI, SQLAlchemy, Alembic, pytest, ruff; Docker Compose, PostgreSQL 16/pgvector; browser-driven UI verification.

**Execution mode:** Inline in the current task. No product source edits or commits are planned. Local-only configuration, dependency directories, logs, screenshots, and the final report remain inside this repository.

## Task 1: Freeze the source and local boundary

**Files:**
- Inspect: `.git`, `.gitmodules`, `AGENTS.md`, `README.md`, `.env.example`
- Create locally: `.env`, `.zcode/runtime/`, `node_modules/.cache/corepack/`, `artifacts/validation-2026-07-22/`

**Steps:**

1. Record `git rev-parse HEAD`, branch, remote, and `git status --short` in the validation log.
2. Initialize the pinned `vendor/hms` submodule with `git submodule update --init --recursive` and verify its SHA with `git submodule status`.
3. Copy `.env.example` to ignored `.env` without changing the demo credentials.
4. Create `.zcode/runtime/uv-cache`, `.zcode/runtime/pnpm-store`, `.zcode/runtime/npm-cache`, and `.zcode/runtime/tmp`; keep the Corepack payload in ignored `node_modules/.cache/corepack`; direct install caches there.
5. Record Docker, Compose, Node, pnpm, Python 3.11, uv, Git, and curl versions.

**Expected:** The main checkout and HMS submodule have fixed SHAs; `.env` selects `MP_MEMORY_ENGINE_MODE=demo`; all generated state is repository-local except Docker Desktop's managed engine storage.

## Task 2: Install frontend and backend environments

**Files:**
- Generate: `node_modules/`, `backend/.venv/`
- Do not modify: `pnpm-lock.yaml`, `backend/pyproject.toml`

**Steps:**

1. Run `pnpm install --frozen-lockfile --store-dir .zcode/runtime/pnpm-store` from the repository root.
2. Verify `pnpm-lock.yaml` is unchanged with `git diff --exit-code -- pnpm-lock.yaml`.
3. Run `uv venv --python 3.11 backend/.venv` with `UV_CACHE_DIR=.zcode/runtime/uv-cache`.
4. Run `uv pip install --python backend/.venv/Scripts/python.exe -e "backend[dev]"` with the same cache directory.
5. Run `backend/.venv/Scripts/python.exe -m pip check` when pip is available; otherwise use `uv pip check --python backend/.venv/Scripts/python.exe`.

**Expected:** Frozen frontend install succeeds, Python resolves to 3.11, editable backend dependencies are consistent, and manifests/lockfiles remain unchanged.

## Task 3: Run the repository release gates

**Files:**
- Inspect: `package.json`, `.github/workflows/ci.yml`, `backend/pyproject.toml`
- Capture: `artifacts/validation-2026-07-22/static-and-unit.log`

**Steps:**

1. Run `pnpm lint`; expect exit code 0 with no ESLint errors.
2. Run `pnpm build`; expect every Next.js route to compile and TypeScript checks to pass.
3. Run `backend/.venv/Scripts/ruff.exe check backend/app backend/tests`; expect `All checks passed!`.
4. From `backend`, run `.venv/Scripts/python.exe -m pytest -m "not postgres and not hms and not compose" -ra -q`; record collected, passed, skipped, deselected, failed, and duration counts.
5. Run the complete host suite once to confirm dependency-marked tests skip or pass honestly.

**Expected:** The CI-equivalent frontend and backend gates pass. Any failure is preserved verbatim and diagnosed before continuing.

## Task 4: Build and validate the default Compose stack

**Files:**
- Exercise: `docker-compose.yml`, `backend/Dockerfile`, Alembic migrations, seed data, `scripts/demo.sh`
- Capture: `artifacts/validation-2026-07-22/compose.log`, service logs, health JSON

**Steps:**

1. Render `docker compose config` and confirm loopback bindings for 8000 and 18080.
2. Build and start with `docker compose up -d --wait --remove-orphans`.
3. Verify all three services are healthy with `docker compose ps` and `GET /v1/health` returning `mp`, `hms`, and `db` as `ok` plus `memory_engine=demo`.
4. Run `docker compose exec -T mp-backend alembic upgrade head`.
5. Run `docker compose exec -T mp-backend python -m app.seed.run_seed` twice to verify idempotence.
6. Run `docker compose exec -T mp-backend pytest -ra -q` so PostgreSQL/HMS/Compose-marked coverage executes against live services.
7. Run the customer demo script through Git Bash and verify its final success line plus health, ingest, retrieve, versioned edit, export/download, delete, audit, and usage assertions.

**Expected:** Clean images build, services reach healthy state, migrations and repeated seed succeed, the service-backed pytest suite passes, and the demo journey passes over HTTP.

## Task 5: Exercise every backend capability over the running HTTP boundary

**Files:**
- Exercise: all routers under `backend/app/api/`
- Create: `artifacts/validation-2026-07-22/api-functional-results.json`

**Steps:**

1. Health and schema: call public health, OpenAPI JSON, and Swagger HTML; verify health needs no auth and business endpoints do.
2. Authentication: test missing token, wrong scheme, unknown key, seeded bearer key, and accepted bare-token behavior.
3. Provisioning: create app, agent, disposable user, relationship; verify generated identifiers/timestamps, idempotent user creation, tenant isolation, and audit entries.
4. Devices: register, reject missing/wrong pairing code, bind, reject duplicate bind, unbind, reject duplicate unbind, rebind, wipe, and confirm wiped-device retrieval exclusion.
5. Ingest: cover allowed S1 auto-write, S2 candidate, S3 block, duplicate event behavior, source/provenance fields, and HMS-backed mapping.
6. Retrieve/debug: cover query results, trace lookup, policy cap, sensitivity masking toggle, device-only scope for bound/non-device/wiped callers, cross-tenant denial, usage and audit effects.
7. Memory CRUD: cover all seven documented filters, pagination, deleted opt-in, content versioning/supersedes chain, legal state changes, illegal 409 transition, tombstone deletion, and retrieval exclusion.
8. Policy: create/update all fields, live ingest block, retrieve cap/masking, reject `cross_brand_app=true` with 422 and no write, then restore the seed policy.
9. Migration: preview three buckets, idempotent preview, execute selected memories with old access `keep`, lookup, rollback, repeat with `remove`, and verify HMS bank identity is unchanged.
10. Aggregates: query audit action/resource filters, pagination, inclusive `since`/`until`, invalid reversed window, and all five usage dimensions without write side effects.
11. Export: create, poll to completion, download once, validate `memory-passport/v1`, confirm no embedding/provider/API-key data, then verify wrong token and one-shot token rejection.
12. Delete user: operate only on a disposable user; verify HMS bank deletion, MP tombstones, mapping removal, passport revoke, empty auditable retrieval, and cross-tenant 403.

**Expected:** Every API family has at least one live success call and its important validation/auth/isolation/failure path. Destructive calls use disposable records only.

## Task 6: Validate optional deployment/configuration surfaces

**Files:**
- Exercise: `docker-compose.real.yml`, `docker-compose.tls.yml`, `scripts/validate-real-hms-env.sh`, backup/restore scripts
- Capture: `artifacts/validation-2026-07-22/deployment-surfaces.log`

**Steps:**

1. With placeholder keys, run the real-HMS validator and verify it fails closed with a credential-specific error.
2. Render the real-HMS Compose overlay with syntactically non-placeholder temporary values without starting paid-provider calls; verify API and worker services resolve the pinned submodule.
3. Render the TLS overlay with a local test domain and verify Caddy/backend routing configuration; do not claim public certificate issuance without DNS.
4. Create a backup of both seeded databases, inspect the dump files, restore into the same disposable local stack, rerun health/seed checks, and record data-count consistency.

**Expected:** Misconfigured real mode is rejected, both overlays render, backup/restore is operational locally, and external provider inference/public DNS remain explicitly bounded if credentials or DNS are unavailable.

## Task 7: Start the frontend and test every browser route/action

**Files:**
- Exercise: all `src/app/**/page.tsx` routes and shared components/store/API client
- Capture: browser screenshots and `artifacts/validation-2026-07-22/frontend-functional-results.md`

**Steps:**

1. Start `pnpm dev` on 127.0.0.1:3000 with the demo backend online; confirm no backend-offline fallback warning and no uncaught browser/terminal error.
2. Landing `/`: verify navigation to B-side console and C-side app plus theme switching.
3. Console overview `/console`: verify KPI values, activity chart, alerts, sidebar navigation, and hydration from live audit/usage APIs.
4. Apps `/console/apps`, `/console/apps/new`, `/console/apps/app_luna`: verify list/detail, product type/environment/region controls, branding switch, navigation, API-key reveal/copy, and identify any prototype-only actions.
5. Quickstart `/console/quickstart`: send a live event, retrieve it, verify visible success/result and corresponding backend memory/audit record.
6. Memory users `/console/memory/users`: switch users and filters, open trace sheet, archive and delete disposable memory, verify backend persistence, and identify prototype-only inline edit.
7. Policy `/console/memory/policy`: toggle each active rule/portability setting, max-result select, sensitivity switch, verify API persistence, and verify deferred/forbidden controls remain disabled.
8. Console devices/settings `/console/devices`, `/console/settings`: verify tables, menus, migration links, webhook copy/control feedback, and label prototype-only or non-persistent controls accurately.
9. Consent `/app/consent`: enable memory and navigate to the memory center.
10. Memory center `/app/memory` and detail `/app/memory/{id}`: filters, pause, export feedback, detail display, edit/version, archive/delete dialogs, and live persistence.
11. Delete flow `/app/memory/delete`: type the required confirmation, verify guarded disabled state, cancel, then delete only a disposable user and verify completion/navigation.
12. Devices `/app/devices` and `/app/devices/bind`: scan/pair interaction, bind against live API where wired, and validate completion feedback.
13. Migration `/app/migrate` and `/app/migrate/complete`: recommended selection, per-item toggles, keep/remove old access, live move, result summary, and follow-up navigation.
14. Visit an invalid route and invalid memory/app identifiers; record 404 or in-app not-found behavior.
15. Resize to desktop and narrow mobile view; verify key routes remain navigable without clipping or horizontal overflow.

**Expected:** All 17 routes render. Every visible interactive control is clicked or intentionally documented as disabled/prototype-only; live mutations are verified against the backend, not only by toasts.

## Task 8: Diagnose failures, rerun critical paths, and report

**Files:**
- Create: `docs/validation-report-2026-07-22.md`
- Capture: final git status, Compose status/logs, frontend log, screenshots, JSON evidence

**Steps:**

1. For each failure, preserve the exact command/request, expected result, actual result, response/status, and relevant logs; determine whether it is environment, documentation, test, integration, or product behavior.
2. Do not patch product code unless the user separately authorizes fixes; configuration-only corrections may be applied locally and recorded.
3. Rerun health, CI-equivalent gates, service-backed pytest, demo journey, and frontend quickstart/mutation paths after any environment correction.
4. Write a feature-by-feature table with status `PASS`, `PARTIAL`, `FAIL`, or `BLOCKED`, evidence, and limitations.
5. State practical run verdicts separately for default demo, frontend/backend integration, production overlays, and real paid-provider HMS inference.
6. Verify the report paths exist, the commands in the report match logs, and `git diff` contains no unintended product source change.

**Expected:** The final report is reproducible, distinguishes shipped behavior from prototype UI and external-credential boundaries, and never upgrades a partial or blocked check into a pass.

## Self-review

- **Spec coverage:** clone/setup, frontend, backend, every enumerated API family, every 17 frontend routes, deployment overlays, persistence, failure paths, evidence, and honest limitations each have an explicit task.
- **Placeholder scan:** no `TBD`, `TODO`, deferred implementation instruction, or unspecified test step is present.
- **Type/interface consistency (superseded implementation):** frontend live checks now use the same-origin `/api/mp` gateway with server-only `MP_API_URL`/`MP_API_KEY`; backend HTTP checks use the same `/v1` contract; real HMS uses the same MP boundary and is reported separately.
