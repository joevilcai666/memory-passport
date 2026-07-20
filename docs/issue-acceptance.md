# GitHub Issue Acceptance Evidence

This matrix records the local evidence for V0.1 issues #2–#10. All tests run
without GitHub Actions. Host tests use SQLite/respx; the final Compose command
runs the same suite with PostgreSQL and the live HMS-compatible service.

## Release commands

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm build
cd backend && .venv/bin/ruff check app tests
cd backend && .venv/bin/pytest -q
docker-compose up -d --wait
docker-compose exec -T mp-backend pytest -q
make demo
```

| Issue | Acceptance group | Automated/runtime evidence |
|---|---|---|
| #2 Provisioning | Seven creation flows, generated IDs/timestamps, audit rows | `tests/test_provisioning.py` happy-path tests |
| #2 | Idempotent `bank_id=user_id`, passport persistence, HMS rollback | `test_create_user_provisions_hms_bank_once`, `test_create_user_is_idempotent`, `test_create_user_hms_failure_returns_502_and_rolls_back` |
| #2 | Pairing authorization, device state machine, tenant/auth isolation | remaining device/cross-tenant/auth tests in `test_provisioning.py` |
| #3 Device wipe | Bound-only state transition, selective tombstones, summary audit | `tests/test_wipe.py` happy, illegal-state, and audit tests |
| #3 | Wiped-device retrieve denial and tenant isolation | `test_wiped_device_cannot_retrieve_device_only_memories`, cross-tenant/auth tests |
| #4 Ingest | HMS retain/list reconciliation, N MP mappings, source/provenance | `test_ingest_creates_mp_records_backed_by_hms_units`; `tests/test_ingest_smoke.py` in Compose |
| #4 | S3 block, S2 candidate, HMS rollback, isolation/auth | remaining tests in `tests/test_ingest.py` |
| #4 | Seeded HTTP quickstart | `scripts/demo.sh` ingest assertion |
| #5 Retrieve | Scope matrix and wiped-device exclusion | first five scope tests in `tests/test_retrieve.py` |
| #5 | Masking toggle, live cap, history/usage | masking, cap, and retrieval-event tests in `test_retrieve.py` |
| #5 | Trace round trip, tenant/auth/HMS failure | trace and error tests in `test_retrieve.py` |
| #5 | Seeded HTTP quickstart | `scripts/demo.sh` retrieve assertion |
| #6 Memory CRUD | Seven filters, pagination, deleted opt-in | list tests in `tests/test_memory_crud.py` |
| #6 | Version/supersedes chain and HMS reconciliation | content-edit and two-edit-chain tests |
| #6 | Every legal and illegal transition | exhaustive parametrized state-machine tests |
| #6 | Tombstone/retrieve exclusion, audit, isolation, HMS rollback | remaining CRUD tests plus `test_tombstoned_memory_is_excluded_from_subsequent_retrieve` |
| #7 Policy | Create/update, persisted rules/config, defaults, audit | `test_create_then_update_same_pair_persists_every_field` |
| #7 | Cross-brand 422 with no write; tenant isolation | corresponding tests in `tests/test_policies.py` |
| #7 | Live ingest block and retrieve cap/masking | final two policy tests |
| #8 Migration | Exact three buckets and idempotent preview | `test_preview_exact_buckets_and_is_idempotent` |
| #8 | Device relink while HMS bank stays unchanged; keep/remove old access | execute and rollback tests in `tests/test_migration_wedge.py` |
| #8 | Partial warnings, total failure retry, full lookup, isolation | remaining migration-wedge tests |
| #8 | Seed `mig_001` end-to-end | HTTP execution against Compose; migration upgrade/downgrade tests |
| #9 Aggregates | Audit filters/pagination/newest-first/bounds/isolation | first two tests in `tests/test_aggregates.py` |
| #9 | MAU, four ops, storage, activations, migration count, time window | `test_usage_returns_five_dimensions_and_honors_window` |
| #9 | Read-only behavior and invalid window | final aggregate test; operation writers asserted by ingest/retrieve/CRUD tests |
| #10 Data ops | Async 202→poll→download, neutral bundle, export audit | `test_export_round_trip_is_model_neutral_and_audited` |
| #10 | Wrong/expired token and sanitized failed job | download/failure tests in `tests/test_data_ops.py` |
| #10 | HMS bank deletion, tombstones, mapping removal, passport revoke, empty retrieve, one summary audit | `test_delete_user_cascades_and_retrieve_short_circuits_hms` |
| #10 | Explicit cross-tenant 403 | `test_data_operations_explicitly_forbid_cross_tenant_users` |

## Cross-cutting local evidence

- `tests/test_migrations.py`: fresh PostgreSQL upgrade and downgrade lifecycle.
- `tests/test_seed.py`: exact Luna seed counts and HMS bank provisioning.
- `tests/test_demo_hms.py` and `tests/test_hms_client.py`: deterministic/real
  compatible network contract.
- `tests/test_real_hms_config.py`: real mode fails closed on missing or
  placeholder LLM/embedding keys.
- `pnpm lint` and `pnpm build`: frontend lint, TypeScript, and Next.js build.
- `make demo`: health, ingest, retrieve, versioned edit, export/download,
  tombstone, audit, and usage over the running stack.
- `docker-compose -f docker-compose.yml -f docker-compose.real.yml config`:
  real HMS API/worker overlay renders without changing the MP boundary.
- No workflow under `.github/workflows` is added or required.
