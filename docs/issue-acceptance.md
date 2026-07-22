# V0.1 local issue acceptance evidence

Date: 2026-07-22

This matrix records the local acceptance evidence for the V0.1 backend and product-remediation work. Host tests use isolated databases and mocked HMS failures where appropriate; the Compose suite runs all service-dependent tests against PostgreSQL and the live deterministic HMS-compatible service.

## Final commands and results

```powershell
.\node_modules\.bin\vitest.CMD run
.\node_modules\.bin\eslint.CMD .
.\node_modules\.bin\next.CMD build
.\backend\.venv\Scripts\python.exe -m ruff check backend/app backend/tests scripts/live-api-matrix.py
.\backend\.venv\Scripts\python.exe -m pip check
.\backend\.venv\Scripts\python.exe -m pytest -q backend/tests
docker compose up -d --wait
docker compose exec -T mp-backend pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate-remediation.ps1
```

Final results:

- Frontend: 94/94 tests; ESLint pass; optimized Next.js build pass.
- Host backend: 185 passed; 11 service-dependent tests skipped.
- Container backend: 196/196; no skips or failures.
- Live HTTP: 120/120 plus CORS and five direct database assertions.
- Product source claims, Windows line endings, shell syntax, official demo, and restore round trip: pass.

## Backend issue matrix

| Issue | Acceptance group | Automated/runtime evidence |
|---|---|---|
| #2 Provisioning | Creation, generated IDs/timestamps, audit rows | `backend/tests/test_provisioning.py` happy paths |
| #2 Provisioning | Idempotent `bank_id=user_id`, passport persistence, HMS rollback | `test_create_user_provisions_hms_bank_once`, `test_create_user_is_idempotent`, `test_create_user_hms_failure_returns_502_and_rolls_back` |
| #2 Provisioning | Pairing authorization, device state machine, tenant/auth isolation | Remaining provisioning device, tenant, and auth tests |
| #3 Device wipe | Bound-only state transition, selective tombstones, summary audit | `backend/tests/test_wipe.py` happy, illegal-state, and audit tests |
| #3 Device wipe | Wiped-device retrieve denial and isolation | Wipe/retrieve cross-tenant and authorization tests |
| #4 Ingest | HMS retain/list reconciliation, MP mappings, source/provenance | `backend/tests/test_ingest.py`; live ingest cases |
| #4 Ingest | S3 block, S2 candidate, HMS rollback, isolation | Remaining ingest tests and live candidate lifecycle |
| #5 Retrieve | Scope matrix, wiped-device exclusion, masking, caps | `backend/tests/test_retrieve.py` |
| #5 Retrieve | Trace round trip and feedback persistence | Retrieve/debug tests plus live matrix and direct DB assertion |
| #6 Memory CRUD | Filters, pagination, deleted opt-in | List cases in `backend/tests/test_memory_crud.py` |
| #6 Memory CRUD | Version/supersedes chain and HMS reconciliation | Content-edit and two-edit-chain tests |
| #6 Memory CRUD | Complete legal/illegal state matrix | Exhaustive parametrized transition tests, including delete from every non-deleted state |
| #6 Memory CRUD | Tombstone exclusion, audit, isolation, rollback | CRUD/retrieve tests plus live edit -> archive -> delete |
| #7 Policy | Create/update, persisted rules/config, defaults, audit | `backend/tests/test_policies.py` |
| #7 Policy | Cross-brand rejection and tenant isolation | Policy validation/isolation tests |
| #7 Policy | Live ingest block, retrieval cap/masking | Policy integration tests and live matrix |
| #8 Migration | Exact buckets and idempotent preview | `test_preview_exact_buckets_and_is_idempotent` |
| #8 Migration | Execute, relink, old access, retry/rollback | `backend/tests/test_migration_wedge.py` |
| #8 Migration | Browser count and persistence | Real 35 moved / 5 skipped / 0 failed journey; DB rollback assertion |
| #9 Aggregates | Audit filters, pagination, ordering, bounds, isolation | `backend/tests/test_aggregates.py` |
| #9 Aggregates | MAU, four operations, storage, activations, migrations, windows | Usage aggregate tests and official demo |
| #10 Data ops | Export poll/download, neutral bundle, token enforcement | `backend/tests/test_data_ops.py`; live export matrix |
| #10 Data ops | User deletion, tombstones, bank deletion, passport revoke | Delete-user cascade tests, live matrix, and browser delete-all |

## Product-remediation matrix

| Area | Acceptance evidence |
|---|---|
| CORS | `backend/tests/test_cors.py`; allowed local preflight 200; unlisted origin 400 |
| Browser truthfulness | Store/component failure tests; backend-offline browser writes disabled; no optimistic success |
| Apps and keys | API-client/store/page tests; browser app create, one-time key, rotate/revoke live matrix |
| Consent | `backend/tests/test_consent.py`; component/store tests; explicit off/on browser journey |
| Team | Backend lifecycle tests; page/public-invite tests; browser issue/preview/accept; consumed-token DB assertion |
| Trace feedback | Backend/API-client/store/component tests; live response and direct DB persistence |
| Memory Center | Add/export/pause/edit/report/delete/delete-all tests and real browser journeys |
| Device bind | Backend provisioning tests; bind-page tests; browser register/code/bind journey |
| Migration UI | Component/store tests; browser selection and completed result counts |
| Windows shell safety | `.gitattributes`, `scripts/verify-line-endings.ps1`, fresh `core.autocrlf=true` clone, `bash -n` |
| Restore | `scripts/verify-restore.sh`; row parity, pgvector/vector query, owner access, health |
| Documentation | `scripts/check-product-claims.ps1` and corrected evaluator/security/branch/device claims |
| Hydration/routes | Development and production route sweeps; final production 18/18 |

## Operational checks

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-product-claims.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-line-endings.ps1
& 'D:\software_data\Git\bin\bash.exe' scripts/demo.sh
& 'D:\software_data\Git\bin\bash.exe' scripts/verify-restore.sh
```

The local evaluator proves the complete Memory Passport orchestration and lifecycle boundary. It does not substitute for production session/BFF authorization, real provider inference, public TLS, or physical hardware validation; those boundaries are listed explicitly in `docs/validation-report-2026-07-22.md`.
