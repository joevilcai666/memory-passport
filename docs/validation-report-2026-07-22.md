# Memory Passport complete local validation report

Date: 2026-07-22 (Asia/Shanghai)

Repository: `https://github.com/joevilcai666/memory-passport.git`

Local validation branch: `fix/validation-remediation-2026-07-22`

## Executive verdict

The complete default local product now runs end to end.

- Backend: **yes**. FastAPI, PostgreSQL/pgvector, and the deterministic HMS-compatible evaluator are healthy. The container suite passes 196/196 and the real HTTP matrix passes 120/120.
- Frontend: **yes**. The Next.js production build passes, all 18 fixed routes render without runtime/hydration errors, and B-side/C-side browser actions persist through the backend.
- Frontend to backend integration: **yes for local evaluation**. Allowed local CORS origins work; an unlisted origin is rejected.
- Backup/restore: **yes**. Exact row parity, pgvector, vector data, owner access, and post-restore health were verified.
- Windows checkout/run path: **yes**. A fresh `core.autocrlf=true` clone retained LF for Linux entrypoints and all shell scripts parsed.

This is not yet a production-hosted operator-authentication deployment. Browser calls now use a same-origin server gateway and tenant API keys remain on that server, but the deployed console still needs a signed-in operator session and RBAC. Real HMS provider inference and public TLS were not exercised because no provider credentials, domain, or DNS target were supplied.

## Final release-gate results

| Layer | Result | Evidence |
|---|---:|---|
| Frontend unit/component/store | PASS | 21 files, 104/104 tests |
| Frontend lint | PASS | ESLint, zero errors |
| Frontend production build | PASS | Next.js 16.2.10, TypeScript pass, 19 generated routes including `_not-found` |
| Backend lint | PASS | Ruff on `backend/app`, `backend/tests`, and the live matrix |
| Python environment | PASS | `pip check`: no broken requirements |
| Host backend tests | PASS | 185 passed; 11 service-dependent tests skipped as designed |
| Container backend tests | PASS | 196/196, no skips/failures |
| Live API matrix | PASS | 120/120, run `matrix-f56a5bc0ab` |
| CORS | PASS | `http://localhost:3000` preflight 200; unlisted origin 400 |
| Direct database assertions | PASS | app persistence, deleted passport, migration rollback, consumed invite, trace feedback |
| Browser route sweep | PASS | 18/18 fixed routes; no runtime, hydration, or server error text |
| Dynamic invite route | PASS | real token previewed, accepted once, and persisted |
| Offline frontend | PASS | read-only demo fallback; all tested writes disabled |
| Official demo | PASS | health, ingest, retrieve, edit, export, delete, audit, usage |
| Backup/restore | PASS | MP/HMS row parity and pgvector/vector checks |
| Product-claim source check | PASS | documented routes, branches, runtime claims, and security boundary |
| Windows line endings | PASS | 8 Linux entrypoints LF; 6 shell scripts pass `bash -n` in fresh autocrlf clone |

Machine-readable HTTP evidence is in `artifacts/remediation-2026-07-22/api-results.json`. Browser and restore evidence are in the same directory.

## Remediation ledger

| # | Original problem | Resolution | Final status |
|---:|---|---|---|
| 1 | Browser CORS preflight blocked | Added configured origin allowlist and preflight tests; allowed origin succeeds and an unlisted origin is blocked. | Verified |
| 2 | Frontend could claim success without persistence | Store/API/component actions now await real responses, use response bodies as truth, reject offline writes, and preserve state on failure. | Verified |
| 3 | Windows CRLF broke Linux entrypoints | Added repository line-ending policy and an explicit verifier; fresh Windows clone passed. | Verified |
| 4 | Restore could omit pgvector or swallow failure | Restore now pre-creates/verifies vector support, preserves ownership, fails on incomplete work, and checks exact row parity. | Verified |
| 5 | Consent `Turn on` toggled the wrong direction | Consent uses explicit idempotent true/false endpoints and is enforced by backend ingest/retrieve behavior. | Verified |
| 6 | Migration selection/counts could diverge | Selection no longer collapses its bucket; moved/skipped/failed counts come from preview/execute results. | Verified |
| 7 | Quickstart linked a removed debugger route | Dead link removed; trace exploration uses the implemented Users/Trace flow. | Verified |
| 8 | Major controls were no-ops or local simulations | Apps/keys, Quickstart, policy, users, feedback, team, consent, memory, export, device, migration, and delete-all are backed by real APIs. | Verified |
| 9 | Product documentation drifted from runtime | Branch, HMS mode, device bind, tenant/security, and failure-state claims were aligned and source-checked. | Verified |
| 10 | Development hydration behavior was uncertain | Controlled development and production route sweeps rendered without hydration/runtime errors; production was re-swept after final fixes. | Verified |
| 11 | Windows `demo.sh` hit the WindowsApps Python stub | Demo now prefers the repository virtualenv, validates fallback interpreters, and supports `MP_DEMO_PYTHON`. | Verified |
| 12 | Versioned edit left the old row in the UI | Store replaces the source ID with the server-returned new version ID. | Verified |
| 13 | Archived/reviewed records could not be deleted | Every non-deleted lifecycle state can tombstone; already-deleted remains illegal. | Verified |
| 14 | Tombstoned rows remained in the live UI list | Successful delete removes the row locally, matching the backend default list. | Verified |

## Functional coverage

### Backend and data plane

The 120-case live matrix and 196-test container suite cover:

- public health, Swagger, and all 37 current OpenAPI operations;
- missing, malformed, unknown, bare-token, and Bearer authentication;
- apps, one-time API keys, key rotation/revocation, agents, users, relationships, and idempotent provisioning;
- explicit memory consent on/off;
- device register, pair, bind, duplicate conflict, unbind, wipe, and wiped-device denial;
- policy create/update, cross-brand validation, block, confirm, auto-write, masking, and retrieval limits;
- memory ingest, candidate activation, scoped retrieval, debug trace, and persistent trace feedback;
- filters, pagination, versioned edits, complete legal/illegal state transitions, archived deletion, and tombstones;
- migration preview, selection buckets, execute, old-device access, retry/rollback, and lookup;
- audit filters, usage aggregates, team invite lifecycle, export/token/download, and delete-user cascade;
- tenant isolation and HMS rollback/error behavior through automated tests.

### Browser product journeys

The production browser pass executed real writes for:

- app creation and one-time API-key display;
- Quickstart event ingest and retrieval;
- policy save and restore;
- team invite creation, public preview, acceptance, and one-time consumption;
- console memory edit, archive, and delete;
- consent off/on;
- explicit memory add and JSON export;
- device registration and binding;
- migration of 35 portable memories with 5 skipped and 0 failed;
- report-as-wrong, single delete, and atomic delete-all.

When the backend was stopped, Memory Center and the console remained readable but mutations were disabled and no success was claimed.

## Backup and restore

`scripts/verify-restore.sh` completed a destructive round trip and returned exit 0.

```text
before: mp=1,3,6,12,51,3,3,2,85;hms=6,4;vector=1,1
after:  mp=1,3,6,12,51,3,3,2,85;hms=6,4;vector=1,1
```

It verified database recreation, exact MP/HMS row parity, pgvector presence, queryable vector data, owner access, and healthy services.

## Final local state

After destructive browser/API tests, the project Docker volume was removed and recreated. The final intended state is the clean Luna evaluator seed:

- 1 tenant, 1 app, 2 API keys;
- 4 users, 2 agents, 4 devices, 1 relationship;
- 1 policy, 6 auto-write rules, 42 memories;
- 1 migration, 3 team members, 8 audit logs;
- 4/4 HMS banks;
- PostgreSQL, HMS evaluator, and MP backend healthy.

Local endpoints:

- Frontend: `http://localhost:3000`
- Backend health: `http://127.0.0.1:8000/v1/health`
- Swagger: `http://127.0.0.1:8000/docs`
- HMS evaluator: `http://127.0.0.1:18080`

## Remaining production boundaries

These are outside the completed local evaluator acceptance and must not be represented as already validated:

1. **Production operator authentication is not implemented.** A same-origin BFF now keeps tenant keys server-side and production fails closed by default, but a deployed UI still needs signed-in user authentication and server-side authorization.
2. **Console role enforcement is not a production RBAC boundary.** Team Owner/Admin/Support records and invite lifecycle persist, but API authorization is tenant-key based rather than signed-in human-role based.
3. **Real HMS inference was not run.** The overlay/configuration boundary exists and fails closed on missing credentials, but real LLM/light-LLM/embedding calls require supplied provider keys.
4. **Public HTTPS was not run.** TLS Compose configuration exists, but no real domain, DNS, or certificate issuance target was available.
5. **Physical camera/QR/hardware was not run.** The current local flow intentionally registers a test device and binds its one-time code; no physical robot or camera was supplied.
6. **No GitHub push was performed.** The integrated work remains local on `codex/issues-20-35-36` pending review.

## Reproduce locally

```powershell
docker compose up -d --wait
docker compose exec -T mp-backend python -m app.seed.run_seed
.\node_modules\.bin\vitest.CMD run
.\node_modules\.bin\eslint.CMD .
.\node_modules\.bin\next.CMD build
.\backend\.venv\Scripts\python.exe -m ruff check backend/app backend/tests scripts/live-api-matrix.py
.\backend\.venv\Scripts\python.exe -m pip check
.\backend\.venv\Scripts\python.exe -m pytest -q backend/tests
docker compose exec -T mp-backend pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate-remediation.ps1
```

Operational checks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-product-claims.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-line-endings.ps1
& 'D:\software_data\Git\bin\bash.exe' scripts/demo.sh
& 'D:\software_data\Git\bin\bash.exe' scripts/verify-restore.sh
```

## Evidence index

- `artifacts/remediation-2026-07-22/api-results.json`
- `artifacts/remediation-2026-07-22/browser-results.md`
- `artifacts/remediation-2026-07-22/restore-results.txt`
- `docs/issue-acceptance.md`
- `docs/specs/2026-07-22-validation-remediation-design.md`
- `docs/plans/2026-07-22-validation-remediation-implementation.md`
