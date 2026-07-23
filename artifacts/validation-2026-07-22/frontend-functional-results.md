# Memory Passport frontend functional results

Validation date: 2026-07-22 (Asia/Shanghai)

Release surface tested: `next build` + `next start` on `http://127.0.0.1:3001`, backed by the healthy default Compose stack on `http://127.0.0.1:8000`.

## Bottom line

- All 18 product route families render in the production build, including both dynamic detail routes.
- Local React interactions work: navigation, dropdowns, tabs, theme, filters, search, selects, dialogs, trace drawer, checkbox/radio flows, mobile navigation, and migration animations.
- The web application is **not connected to its running backend in a normal browser**. Every API request carries `Authorization`, which requires a CORS preflight; the FastAPI app has no CORS middleware and answers the preflight with `405 Method Not Allowed`.
- The Zustand store therefore marks the backend unreachable and deliberately falls back to the Luna seed data. Most mutations then remain optimistic/local-only.
- Several screens report success even though no backend call occurred. Quickstart is the clearest false positive: it reports ingest and retrieval success and marks the integration complete while the database still has no `mem_quickstart` row.

## Global shell and responsive checks

| Area | Result | Evidence |
|---|---|---|
| Console navigation | PASS | Desktop sidebar links and mobile drawer all opened and navigated. |
| Environment switch | PASS (local only) | Sandbox → Prod changed the selected styling; it does not change API context. |
| Theme | PASS | `<html>` changed from `dark` to `light`. |
| Preview-as-user menu | PASS | Memory Center, consent, binding, and migration destinations appeared. |
| Account menu | PASS | Account, role, settings, and sign-out entries appeared. |
| Responsive console | PASS | At 390×844, mobile navigation appeared and page width stayed at 390 px without horizontal overflow. |
| Responsive Memory Center | PASS | At 390×844, page width stayed within the viewport and the category strip/list remained usable. |
| Console runtime errors | PASS | Controlled Chrome reported zero `warn`/`error` console entries during the production-route sweep. |
| Browser/backend integration | FAIL | UI showed `Backend offline — showing demo data`; an explicit browser preflight returned HTTP 405. |

## Route-by-route coverage

| Route | Functions exercised | Result |
|---|---|---|
| `/` | Builder/user entry links, migration link, console links | PASS for navigation. Footer still says `no real backend`, which conflicts with the repository and running backend. |
| `/console` | KPI/dashboard render, chart hydration, Prod switch, theme, preview menu, account menu | PASS for local UI. KPIs/alerts are seeded rather than live because hydration cannot reach the backend. |
| `/console/quickstart` | Four code-copy buttons, test ingest, test retrieve, completion state, next-step links | **FAIL end-to-end**. The page reports `mem_quickstart created`, `3 memories returned`, and `Integration complete` without calling the backend. `Debugger` links lead to a 404. |
| `/console/apps` | App list and create/detail navigation | PASS for seeded list. |
| `/console/apps/new` | Name, product type, environment, region, branding preview, create | Form UI PASS; **create is a prototype**. Submission only routes to Quickstart and the new app is absent from the app list. |
| `/console/apps/app_luna` | Reveal/hide/copy key, new key, roll key, integration status | Reveal/hide/copy works locally. `New key` and `Roll key` are no-ops. The production key is a masked placeholder and the four integration checks are hard-coded green. |
| `/console/memory/policy` | Portability axis, sensitive-memory switch, max-results select, disabled cross-brand axis | Local UI PASS. Database policy remained at cross-device=true, max=8, sensitive=false after UI showed changed values. Auto-write rules are read-only. |
| `/console/memory/users` | User selector, memory-type filter, S3 masking, trace drawer, four feedback buttons, source/edit/archive/delete actions | Local UI PASS. Trace and feedback are derived from seed data; feedback is toast-only; inline edit explicitly says prototype; archive/delete did not persist. |
| `/console/devices` | Upgrade-path view, registry, failed migration retry, report export, migration link | UI PASS. Retry and export only emit toasts; no retry or file download occurs. Health tiles include seeded/static values. |
| `/console/settings` | Team tab, invite, audit tab | UI PASS. Invite says `Invite link copied` but the handler writes nothing to the clipboard. Audit entries are seeded because backend hydration fails. |
| `/app/consent` | `Turn on`, `Not now`, ownership copy | `Not now` PASS. **`Turn on` is logically wrong when the seeded user is already enabled:** it toggles memory off, navigates to Memory Center showing `Paused`, but toasts `Memory is on`. |
| `/app/memory` | Search, type/archive filters, pause/resume, Tell Luna, export, action menu | Local UI PASS. Export is a toast only and does not call the real export endpoint. |
| `/app/memory/mem_001` | Detail metadata, edit dialog, report wrong, delete cancel/confirm | Local UI PASS; persistence FAIL. The UI showed edited/deleted states, while the backend row remained original, version 1, active. |
| `/app/memory/delete` | Exact `DELETE` guard and delete-all confirmation | Guard PASS; persistence FAIL. UI went from 39 visible memories to 0 and announced success, while backend total remained 42. It also bypasses the backend `/v1/delete_user` workflow. |
| `/app/devices` | Device list, upgrade banner, bind/migrate links | PASS for seeded display/navigation. |
| `/app/devices/bind` | QR scan simulation, uppercase pairing code, bind completion | Local simulation PASS. It always “detects” the already-bound Luna v1 and never calls register/bind APIs. |
| `/app/migrate` | Exclusion bucket, select-all, individual deselection, keep/remove v1 radio, execute | Local flow PASS; persistence FAIL. Clicking nested `Select all` also collapses its parent bucket. The UI completed a 33-memory migration while the database stayed `preview`, 0 selected, `remove`. |
| `/app/migrate/complete` | Completion guard, moved/skipped/access stats, next links | Guard PASS. Stats have an off-by-one error: moving 33 of 39 displayed items with 5 device-local + 1 deselected reports `Skipped 5`, but the correct value is 6. |
| `/_not-found` and `/console/memory/debugger` | Invalid/missing route behavior | Standard 404 renders. The latter is a broken product link referenced three times by Quickstart. |

## Browser-visible success versus database truth

| Workflow | Browser result | Database/API result |
|---|---|---|
| Quickstart ingest | `mem_quickstart created` | `mem_quickstart_count = 0`; total stayed 42. |
| Quickstart retrieve | `3 memories returned`; integration complete | `runRetrieveTest` never invokes `api.retrieveMemories`. |
| Edit `mem_001` | Content changed; v2 shown | Original content, version 1, active. |
| Archive/delete `mem_030` | Row changed to Archived, then Deleted | `mem_030` remained active. |
| Delete all | UI total 0; success toast | Backend total 42. |
| Policy changes | Cross-device off, sensitive on, max 16 | Database stayed cross-device=true, sensitive=false, max 8. |
| Migration | Completion page: 33 moved | Database migration stayed `preview`, 0 selected, old access `remove`. |

## Development-mode note

The controlled browsers initially loaded `next dev` HTML but did not attach client interactions. A same-browser control page under this artifact directory proved both inline scripts, external scripts, and click handlers were executable. The optimized production build hydrated and worked normally. This leaves an unresolved development-mode/Turbopack compatibility risk, but it did not reproduce under `next start`; all functional UI results above therefore use the production build.

## Supporting artifacts

- `live_api_matrix.py` — independent backend live matrix.
- `live_api_results.json` — 95 detailed backend checks, latest run 95 passed / 0 failed.
- `browser-runtime-probe.html` and `.js` — isolated browser script-execution control used during hydration diagnosis.
