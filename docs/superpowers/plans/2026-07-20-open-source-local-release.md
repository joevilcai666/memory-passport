# Memory Passport V0.1 Open-Source Local Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish GitHub issues #2 through #10 and publish a locally runnable,
credential-free evaluation stack that can switch to real HMS inference through
configuration.

**Architecture:** Memory Passport keeps one HMS-compatible HTTP boundary. The
default Compose stack supplies a deterministic implementation of that contract;
a real-HMS overlay swaps in the pinned HMS API and worker. Domain features live
in focused FastAPI schemas/services/routers with tenant scoping, explicit state
machines, and tests at route, contract, and Compose levels.

**Tech Stack:** Python 3.11+; FastAPI; Pydantic v2; SQLAlchemy 2; Alembic;
PostgreSQL 16/pgvector; pytest/respx; Docker Compose; Next.js 16.2 App Router;
React 19; TypeScript 5; pnpm 10.

## Global Constraints

- Add no GitHub Actions workflow or dependency on hosted CI.
- Default local evaluation must not require paid model credentials.
- Real mode must use the vendored HMS submodule and perform real retain/recall
  after valid LLM and embedding settings are supplied.
- Preserve `bank_id == user_id` and the existing HMS HTTP namespace.
- All API resource access and mutations are tenant-scoped.
- Cross-brand-app portability remains disabled and returns `422` when enabled.
- Exports contain model-neutral MP data and never contain embeddings, secrets,
  provider payloads, or stack traces.
- Use test-first red-green-refactor for every behavior change.
- Read the relevant files in `node_modules/next/dist/docs/` before modifying
  Next.js code, as required by `AGENTS.md`.
- Work on the approved existing `HMS` branch and push the final result to
  `origin/HMS`.

---

## File Responsibility Map

- `backend/app/demo_hms.py`: deterministic HMS-compatible FastAPI application;
  no MP domain logic.
- `backend/app/hms/__init__.py`: one real/demo-compatible HTTP client contract.
- `backend/app/services/memory_crud.py`: memory list, versioning, status
  transitions, tombstones, and HMS suppression.
- `backend/app/services/policies.py`: persisted policy upsert and validation;
  `backend/app/services/policy.py` remains the live policy resolver/classifier.
- `backend/app/services/migrations.py`: preview buckets, execution state machine,
  retry, and rollback.
- `backend/app/services/aggregates.py`: audit reads and usage aggregation.
- `backend/app/services/data_ops.py`: export jobs, download validation, and
  delete-user cascade.
- `backend/app/services/usage.py`: one small writer for structured usage events.
- `backend/app/schemas/*.py`: request/response validation only.
- `backend/app/api/v1/*.py`: HTTP mapping, session ownership, commits, and
  upstream-error translation only.
- `backend/alembic/versions/0005_migration_lifecycle.py`: migration lifecycle
  columns and enum/audit literals.
- `backend/alembic/versions/0006_usage_events.py`: structured usage events.
- `backend/alembic/versions/0007_exports_user_deletion.py`: export jobs and
  passport-deletion fields.
- `docker-compose.yml`: zero-credential deterministic stack.
- `docker-compose.real.yml`: pinned real HMS API/worker overlay.
- `scripts/demo.sh`: idempotent local evaluator walkthrough.

---

### Task 1: Green Local Baseline and Dual-Mode HMS Contract

**Files:**

- Create: `backend/app/demo_hms.py`
- Create: `backend/tests/test_demo_hms.py`
- Create: `docker-compose.real.yml`
- Create: `scripts/demo.sh`
- Modify: `backend/app/hms/__init__.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/health.py`
- Modify: `backend/tests/test_health.py`
- Modify: `backend/tests/test_ingest_smoke.py`
- Modify: `backend/tests/test_migrations.py`
- Modify: `backend/tests/test_seed.py`
- Modify: `backend/tests/test_smoke.py`
- Modify: `backend/pyproject.toml`
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `Makefile`
- Modify: `backend/Makefile`
- Modify: `eslint.config.mjs`
- Modify: `src/app/console/settings/page.tsx`

**Interfaces:**

- `create_demo_hms_app(database_url: str | None = None) -> FastAPI`
- `HmsClient.delete_document(bank_id: str, document_id: str) -> dict[str, Any]`
- `HmsClient.delete_bank(bank_id: str) -> dict[str, Any]`
- `HmsClient.update_document_tags(bank_id: str, document_id: str,
  tags: list[str]) -> dict[str, Any]`
- `Settings.memory_engine_mode: Literal["demo", "real"]`
- Health response adds `memory_engine: "demo" | "real"` without changing the
  existing `mp`, `hms`, and `db` fields.

- [ ] **Step 1: Read the installed Next.js guidance before frontend edits**

Read:

```bash
sed -n '1,260p' node_modules/next/dist/docs/01-app/01-getting-started/01-installation.md
sed -n '1,260p' node_modules/next/dist/docs/01-app/02-guides/production-checklist.md
```

Expected: guidance for the installed Next.js 16.2.10 version, not remembered
framework behavior.

- [ ] **Step 2: Write failing deterministic HMS contract tests**

Add tests that create the demo app on SQLite and prove this exact sequence:

```python
def test_demo_hms_bank_retain_recall_update_and_delete():
    client.put("/v1/default/banks/usr_1", json={}, headers=AUTH).raise_for_status()
    retained = client.post(
        "/v1/default/banks/usr_1/memories",
        json={"items": [{"content": "Mia likes tea", "document_id": "evt_1",
                          "context": "chat", "tags": ["rel:rel_1"]}], "async": False},
        headers=AUTH,
    )
    assert retained.status_code == 200
    listing = client.get(
        "/v1/default/banks/usr_1/memories/list", headers=AUTH
    ).json()
    assert listing["items"][0]["document_id"] == "evt_1"
    recalled = client.post(
        "/v1/default/banks/usr_1/memories/recall",
        json={"query": "tea", "tags": ["rel:rel_1"], "tags_match": "any"},
        headers=AUTH,
    ).json()
    assert recalled["results"][0]["text"] == "Mia likes tea"
    assert client.delete(
        "/v1/default/banks/usr_1/documents/evt_1", headers=AUTH
    ).status_code == 200
    assert client.delete(
        "/v1/default/banks/usr_1", headers=AUTH
    ).status_code == 200
```

Also assert invalid bearer tokens return `401`, retain IDs are stable UUID-like
strings, list pagination is deterministic, and health returns
`{"status": "healthy", "mode": "demo"}`.

- [ ] **Step 3: Run the contract tests and verify RED**

Run:

```bash
cd backend && .venv/bin/pytest tests/test_demo_hms.py -q
```

Expected: FAIL because `app.demo_hms` does not exist.

- [ ] **Step 4: Implement the deterministic service and client methods**

Implement two standalone SQLAlchemy tables (`demo_hms_banks` and
`demo_hms_memory_units`) under their own `MetaData`. Retain stores one unit per
item, with the response fields currently consumed by MP:

```python
unit = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{bank_id}:{document_id}:{content}")),
    "text": content,
    "type": "world",
    "context": item.get("context"),
    "document_id": document_id,
    "metadata": item.get("metadata") or {},
    "tags": item.get("tags") or [],
    "mentioned_at": item.get("timestamp"),
    "proof_count": 1,
}
```

Recall tokenizes case-folded alphanumeric words, filters by bank/tags, sorts by
descending query-token overlap and then ID, and returns only positive-overlap
rows unless the query has no tokens. Implement the pinned HMS paths used by MP:

```text
GET    /health
PUT    /v1/default/banks/{bank_id}
GET    /v1/default/banks
DELETE /v1/default/banks/{bank_id}
POST   /v1/default/banks/{bank_id}/memories
GET    /v1/default/banks/{bank_id}/memories/list
POST   /v1/default/banks/{bank_id}/memories/recall
DELETE /v1/default/banks/{bank_id}/documents/{document_id:path}
```

Extend `HmsClient` with `delete_document`, `delete_bank`, and
`update_document_tags`, using the same error wrapper and bearer header pattern
as existing methods.

- [ ] **Step 5: Make host and service-backed tests explicit**

Register markers in `backend/pyproject.toml`:

```toml
markers = [
  "postgres: requires a reachable PostgreSQL service",
  "hms: requires a reachable HMS HTTP service",
  "compose: exercises the complete Docker Compose stack",
]
```

Mark every fixture that creates a PostgreSQL database or calls a real HMS
service. At fixture setup, perform a bounded connectivity probe and call
`pytest.skip()` with the missing service name. Fast SQLite/respx tests remain
unmarked. The host command `.venv/bin/pytest -m 'not postgres and not hms and
not compose'` must therefore pass without local services.

- [ ] **Step 6: Fix the frontend baseline**

Add `vendor/hms/**`, `backend/**`, `.worktrees/**`, and runtime export paths to
`globalIgnores`. Replace the exhaustive `Record<AuditAction, AuditMeta>` with a
complete metadata factory that covers all action literals and returns a neutral
fallback for future literals:

```ts
function metaForAudit(action: AuditAction): AuditMeta {
  if (action === "memory.deleted") {
    return { label: action, Icon: Trash2, tint: "bg-rose-500/10",
      color: "text-rose-600 dark:text-rose-400" };
  }
  if (action === "memory.exported") {
    return { label: action, Icon: Download, tint: "bg-amber-500/10",
      color: "text-amber-600 dark:text-amber-400" };
  }
  if (action.startsWith("device.")) {
    return { label: action, Icon: Smartphone, tint: "bg-neutral-500/10",
      color: "text-neutral-600 dark:text-neutral-400" };
  }
  if (action.startsWith("migration.")) {
    return { label: action, Icon: History, tint: "bg-emerald-500/10",
      color: "text-emerald-600 dark:text-emerald-400" };
  }
  return { label: action, Icon: ShieldCheck, tint: "bg-ink-600/10",
    color: "text-ink-700 dark:text-ink-300" };
}
```

Use `metaForAudit(log.action)` at render time.

- [ ] **Step 7: Wire zero-credential and real Compose modes**

The base stack runs `python -m uvicorn app.demo_hms:app --host 0.0.0.0 --port
18080` from the backend image as `hms-api`, with a dedicated Postgres URL and
`MP_MEMORY_ENGINE_MODE=demo`. The real overlay replaces the `hms-api` build and
command with the vendored HMS image, adds `hms-worker`, applies all provider
settings, and sets `MP_MEMORY_ENGINE_MODE=real`.

Add configuration validation:

```python
required_provider_credentials = (
    settings.hms_llm_api_key,
    settings.hms_retain_llm_api_key,
    settings.hms_embeddings_api_key,
)
if settings.memory_engine_mode == "real" and any(
    not value or value.endswith("_change_me")
    for value in required_provider_credentials
):
    raise RuntimeError("real HMS mode requires non-placeholder LLM and embedding credentials")
```

`make demo` builds/starts the base stack, waits for health, seeds, and runs
`scripts/demo.sh`. `make real-up` uses both Compose files. `make check` runs
frontend lint/build, Ruff, fast tests, and Compose-backed tests locally.

- [ ] **Step 8: Verify GREEN and commit**

Run:

```bash
pnpm lint
pnpm build
cd backend && .venv/bin/ruff check app tests
cd backend && .venv/bin/pytest -m 'not postgres and not hms and not compose' -q
docker compose config
docker compose -f docker-compose.yml -f docker-compose.real.yml config
```

Expected: every command exits 0; no GitHub workflow appears in `git diff`.

Commit:

```bash
git add .env.example Makefile backend docker-compose.yml docker-compose.real.yml \
  eslint.config.mjs scripts src/app/console/settings/page.tsx
git commit -m "feat: add local demo and real HMS modes"
```

---

### Task 2: Memory CRUD and State Machine (#6)

**Files:**

- Create: `backend/app/schemas/memory_crud.py`
- Create: `backend/app/services/memory_crud.py`
- Create: `backend/tests/test_memory_crud.py`
- Modify: `backend/app/api/v1/memories.py`
- Modify: `backend/app/hms/__init__.py`
- Modify: `backend/app/services/scopes.py`
- Modify: `backend/app/services/ids.py`
- Modify: `backend/app/schemas/__init__.py`

**Interfaces:**

- `list_memories(db, tenant_id, filters, page, page_size, include_deleted)`
- `edit_memory(db, context, hms_client, memory_id, content) -> MemoryRecord`
- `transition_memory(db, context, memory_id, target_status) -> MemoryRecord`
- `delete_memory(db, context, hms_client, memory_id) -> MemoryRecord`
- `HmsClient.update_document_tags(bank_id, document_id, tags) -> dict[str, Any]`

- [ ] **Step 1: Write route tests for every acceptance criterion**

Tests must cover filters (`user_id`, `type`, `status`, `scope`,
`relationship_id`, `agent_id`, `device_id`), pagination metadata, deleted
default exclusion, `include_deleted`, a two-edit supersedes chain, all legal
transitions, `deleted -> active` conflict, tombstone retrieval exclusion,
tenant isolation, audit actions, and HMS rollback.

The core RED assertion is:

```python
edited = client.patch(
    "/v1/memories/mem_1", headers=AUTH, json={"content": "new text"}
)
assert edited.status_code == 200
assert edited.json()["version"] == 2
assert edited.json()["supersedes"] == "mem_1"
assert db.get(MemoryRecord, "mem_1").status == MemoryStatus.ARCHIVED
```

- [ ] **Step 2: Verify RED**

Run `cd backend && .venv/bin/pytest tests/test_memory_crud.py -q`.

Expected: FAIL because list/edit/status/delete behavior is absent.

- [ ] **Step 3: Implement schemas and explicit transition table**

Use a discriminated request with exactly one mutation kind:

```python
class MemoryPatch(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    status: MemoryStatus | None = None

    @model_validator(mode="after")
    def exactly_one_change(self):
        if (self.content is None) == (self.status is None):
            raise ValueError("provide exactly one of content or status")
        return self
```

The transition table is:

```python
LEGAL = {
    MemoryStatus.CANDIDATE: {MemoryStatus.ACTIVE, MemoryStatus.NEEDS_REVIEW},
    MemoryStatus.ACTIVE: {
        MemoryStatus.ARCHIVED, MemoryStatus.NEEDS_REVIEW,
        MemoryStatus.DELETED, MemoryStatus.EXPIRED, MemoryStatus.FLAGGED_WRONG,
    },
}
```

- [ ] **Step 4: Implement list, edit, transition, and tombstone services**

Copy all immutable ownership/source fields into an edited version, reset
usage fields, archive the old record, retain the edited content under a fresh
document ID, reconcile its HMS unit, and create a new mapping. On successful
edit, remove or suppress the old document only when no other live MP mapping
depends on it. Tombstones remove the MP mapping so HMS recall results become
orphans and are skipped; when the document has no other live mapping, delete it
from HMS. Emit one `memory.edited` or `memory.deleted` audit per operation.
Task 5 adds structured usage writes to these already-tested success paths.

- [ ] **Step 5: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/pytest tests/test_memory_crud.py tests/test_retrieve.py -q
cd backend && .venv/bin/ruff check app tests
```

Expected: PASS with no warnings.

Commit:

```bash
git add backend/app backend/tests/test_memory_crud.py
git commit -m "feat: complete memory CRUD and state machine"
```

---

### Task 3: Authoritative Policy Upsert and Enforcement (#7)

**Files:**

- Create: `backend/app/api/v1/policies.py`
- Create: `backend/app/schemas/policies.py`
- Create: `backend/app/services/policies.py`
- Create: `backend/tests/test_policies.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/services/policy.py`
- Modify: `backend/app/services/ingest.py`
- Modify: `backend/app/services/retrieve.py`

**Interfaces:**

- `upsert_policy(db, context, request) -> MemoryPolicy`
- `resolve_policy(db, agent_id) -> ResolvedPolicy`
- `match_auto_write_rule(policy, memory_type, sensitivity) -> AutoWriteAction`

- [ ] **Step 1: Write failing policy tests**

Cover create, same-pair update, persisted auto-write/portability/retrieval
fields, default masking, cross-brand `422` with no write, three mutable axes,
one audit row, tenant isolation, block-rule ingest with zero HMS calls, live
retrieve cap, and masking toggle.

```python
blocked = client.post(
    "/v1/policies",
    headers=AUTH,
    json={"app_id": "app_luna", "agent_id": "agt_luna",
          "portability": {"layer": "portable", "cross_device": True,
                          "cross_role": True, "cross_model": True,
                          "cross_brand_app": True}},
)
assert blocked.status_code == 422
assert "deferred to P2" in blocked.json()["detail"]
```

- [ ] **Step 2: Verify RED**

Run `cd backend && .venv/bin/pytest tests/test_policies.py -q`.

Expected: FAIL with missing `/v1/policies`.

- [ ] **Step 3: Implement upsert and authoritative live reads**

Validate agent-to-app and tenant ownership in one joined query. Replace the
policy's auto-write-rule children transactionally. Store all four portability
keys while enforcing `cross_brand_app is False`. The live resolver returns
defaults only when no persisted policy exists; ingest/retrieve call it for each
request and never cache policy values across requests.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/pytest tests/test_policies.py tests/test_ingest.py tests/test_retrieve.py -q
cd backend && .venv/bin/ruff check app tests
```

Commit:

```bash
git add backend/app backend/tests/test_policies.py
git commit -m "feat: enforce live memory policies"
```

---

### Task 4: Luna Migration Preview, Execute, Retry, and Rollback (#8)

**Files:**

- Create: `backend/app/api/v1/migrations.py`
- Create: `backend/app/schemas/migrations.py`
- Create: `backend/app/services/migrations.py`
- Create: `backend/tests/test_migration_wedge.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/models/migration.py`
- Modify: `backend/app/services/ids.py`
- Modify: `backend/app/seed/data.py`
- Modify: `src/lib/types.ts`
- Modify: `src/app/console/settings/page.tsx`
- Create: `backend/alembic/versions/0005_migration_lifecycle.py`

**Interfaces:**

- `preview_migration(db, context, request) -> MigrationPreviewResponse`
- `execute_migration(db, context, migration_id, selected_ids, old_access)`
- `get_migration(db, tenant_id, migration_id) -> Migration`
- `rollback_migration(db, context, migration_id) -> Migration`

- [ ] **Step 1: Write failing migration-wedge tests**

Pin Luna memories to all three exact buckets, execute `mig_001`, assert selected
memory device IDs change but HMS bank IDs/mappings do not, test keep/remove
source-device access, partial warnings, total failure then retry, full response
shape, cross-tenant isolation, and rollback round trip.

```python
preview = client.post("/v1/migrations/preview", headers=AUTH, json=LUNA_PREVIEW).json()
assert "mem_013" in preview["recommended"]["memory_ids"]
assert "mem_024" in preview["not_moved"]["memory_ids"]
assert preview["counts"] == {
    "recommended": len(preview["recommended"]["memory_ids"]),
    "needs_review": len(preview["needs_review"]["memory_ids"]),
    "not_moved": len(preview["not_moved"]["memory_ids"]),
}
```

- [ ] **Step 2: Verify RED**

Run `cd backend && .venv/bin/pytest tests/test_migration_wedge.py -q`.

- [ ] **Step 3: Add schema support and migration**

Add `rolled_back` to `MigrationStatus`; add `failed_memory_ids` JSON, rollback
snapshot JSON, and `rolled_back_at` to `migrations`. Add audit action
`migration.rolled_back` consistently to Python/Postgres and TypeScript unions.
Revision `0005_migration_lifecycle` adds only fields and literals owned by this
task.

- [ ] **Step 4: Implement migration service**

Use exact bucket predicates from the issue. Store a snapshot before running:

```python
snapshot = {
    "memory_device_ids": {record.id: record.device_id for record in selected},
    "source_device_status": value(source.status),
    "source_bound_user_id": source.bound_user_id,
}
```

Treat missing/ineligible selected IDs as failures. Set running and write
`migration.started`; apply successful IDs; derive completed/warnings/failed;
write `migration.completed` only for a non-total failure. Failed is callable
again. Rollback is legal only from completed states and restores the snapshot.

- [ ] **Step 5: Verify GREEN, frontend type-check, and commit**

Run:

```bash
cd backend && .venv/bin/pytest tests/test_migration_wedge.py tests/test_migrations.py -q
pnpm build
cd backend && .venv/bin/ruff check app tests
```

Commit:

```bash
git add backend src/lib/types.ts src/app/console/settings/page.tsx
git commit -m "feat: add Luna migration lifecycle"
```

---

### Task 5: Audit Log and Usage Read Aggregates (#9)

**Files:**

- Create: `backend/app/models/usage.py`
- Create: `backend/app/services/usage.py`
- Create: `backend/app/services/aggregates.py`
- Create: `backend/app/schemas/aggregates.py`
- Create: `backend/app/api/v1/aggregates.py`
- Create: `backend/tests/test_aggregates.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/services/ingest.py`
- Modify: `backend/app/services/retrieve.py`
- Modify: `backend/app/services/memory_crud.py`
- Modify: `backend/app/services/provisioning.py`
- Modify: `backend/app/services/migrations.py`
- Create: `backend/alembic/versions/0006_usage_events.py`

**Interfaces:**

- `write_usage(db, tenant_id, user_id, operation, timestamp=None) -> UsageEvent`
- `query_audit_logs(db, tenant_id, filters, page, page_size)`
- `query_usage(db, tenant_id, since, until) -> UsageResponse`

- [ ] **Step 1: Write failing aggregate tests**

Build a sequence of provision, ingest, retrieve, edit, delete, bind, and
migration actions. Assert audit newest-first filtering/pagination/shape and
tenant isolation. Assert all five usage dimensions, ISO bounds, 30-day default,
and zero new audit/usage rows after calling either read endpoint.

```python
before = count_side_effect_rows(db)
usage = client.get("/v1/usage", headers=AUTH).json()
after = count_side_effect_rows(db)
assert set(usage) == {
    "since", "until", "memory_mau", "memory_ops", "storage",
    "device_activations", "migration_count",
}
assert before == after
```

- [ ] **Step 2: Verify RED**

Run `cd backend && .venv/bin/pytest tests/test_aggregates.py -q`.

- [ ] **Step 3: Implement structured usage events and aggregate queries**

The operation enum is `ingest`, `retrieve`, `update`, `delete`. Write events in
the existing successful transaction only. Compute MAU and operation groups from
`UsageEvent`, storage as active/non-deleted MP row count, activations from
`device.bound` audit rows, and migration count from `migration.started`. Use
UTC-aware inclusive bounds and reject `since > until` with `422`.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/pytest tests/test_aggregates.py tests/test_ingest.py \
  tests/test_retrieve.py tests/test_memory_crud.py -q
cd backend && .venv/bin/ruff check app tests
```

Commit:

```bash
git add backend/app backend/tests/test_aggregates.py backend/alembic
git commit -m "feat: add audit and usage aggregates"
```

---

### Task 6: Async Export and Delete-User Cascade (#10)

**Files:**

- Create: `backend/app/models/export.py`
- Create: `backend/app/services/data_ops.py`
- Create: `backend/app/schemas/data_ops.py`
- Create: `backend/app/api/v1/data_ops.py`
- Create: `backend/tests/test_data_ops.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/identity.py`
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/services/retrieve.py`
- Modify: `backend/app/services/ids.py`
- Modify: `backend/app/config.py`
- Create: `backend/alembic/versions/0007_exports_user_deletion.py`
- Modify: `.gitignore`
- Modify: `docker-compose.yml`
- Modify: `src/lib/types.ts`
- Modify: `src/app/console/settings/page.tsx`

**Interfaces:**

- `create_export_job(db, context, user_id) -> ExportJob`
- `run_export_job(export_id: str) -> None`
- `get_export_status(db, tenant_id, export_id) -> ExportStatusResponse`
- `resolve_export_download(db, export_id, token) -> Path`
- `delete_user(db, context, hms_client, user_id) -> DeleteUserResponse`

- [ ] **Step 1: Write failing export and deletion tests**

Cover immediate `202`, pending-to-completed background execution, polling,
download token success/expiry/wrong-token, model-neutral bundle schema, no
embedding/provider fields, export audit, failed-job persistence, delete-user
tombstones, HMS bank removal, passport deletion, retrieve short-circuit, one
summary audit row, include-deleted list, and explicit cross-tenant `403`.

```python
response = client.post("/v1/exports", headers=AUTH, json={"user_id": "usr_mia"})
assert response.status_code == 202
export_id = response.json()["export_id"]
status = client.get(f"/v1/exports/{export_id}", headers=AUTH).json()
assert status["status"] == "completed"
bundle = client.get(status["download_url"], headers=AUTH).json()
assert bundle["format"] == "memory-passport/v1"
assert all("embedding" not in json.dumps(row).lower() for row in bundle["memories"])
```

- [ ] **Step 2: Verify RED**

Run `cd backend && .venv/bin/pytest tests/test_data_ops.py -q`.

- [ ] **Step 3: Add export/passport persistence**

Create `ExportJob` with `pending/completed/failed`, token hash/expiry, artifact
path, and timestamps. Add `passport_status` (`active/deleted`) and
`passport_deleted_at` to `User`. Configure `MP_EXPORT_DIR` and
`MP_EXPORT_TOKEN_TTL_SECONDS` with safe local defaults. Mount the export path in
Compose and ignore its contents in Git. Revision
`0007_exports_user_deletion` also adds `user.deleted` to the Postgres audit
enum and the TypeScript `AuditAction` union; update `metaForAudit` so
`user.deleted` uses the destructive-action style.

- [ ] **Step 4: Implement background export and secure download**

Generate a 32-byte URL-safe token, store only SHA-256, and expose a relative
download URL only while complete and unexpired. The versioned JSON bundle is:

```python
bundle = {
    "format": "memory-passport/v1",
    "exported_at": now.isoformat(),
    "user": {"id": user.id, "passport_id": user.passport_id},
    "memories": [serialize_memory(record) for record in records],
}
```

Use a fresh session in the background task. Write via a temporary file then
atomic rename. Persist sanitized `failed` state on any exception.

- [ ] **Step 5: Implement delete-user cascade**

Resolve the target user globally enough to distinguish cross-tenant and return
`403`. Call `HmsClient.delete_bank(user.id)` before committing MP changes.
Bulk-update every memory to deleted, remove mappings, set passport deletion
fields, and write exactly one `user.deleted` summary audit. Retrieve checks
passport status before HMS recall and returns an empty traced response.

- [ ] **Step 6: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/pytest tests/test_data_ops.py tests/test_retrieve.py \
  tests/test_memory_crud.py -q
cd backend && .venv/bin/ruff check app tests
```

Commit:

```bash
git add .gitignore docker-compose.yml backend/app backend/tests/test_data_ops.py \
  backend/alembic
git commit -m "feat: add exports and user deletion"
```

---

### Task 7: Documentation, Full Local Gate, Issue Closure, and Publication

**Files:**

- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `.env.example`
- Modify: `Makefile`
- Modify: `backend/Makefile`
- Modify: `scripts/demo.sh`
- Create: `docs/local-evaluation.md`
- Create: `docs/real-hms.md`
- Create: `docs/issue-acceptance.md`

**Interfaces:**

- `make demo`: clean-clone default evaluator path.
- `make check`: complete local release gate, with no hosted CI.
- `make real-up`: real HMS stack after credential validation.

- [ ] **Step 1: Write the evaluator walkthrough and acceptance matrix**

Document prerequisites, recursive clone, default configuration, one-command
demo, API key, Swagger URL, curl commands for provisioning/ingest/retrieve/CRUD/
policy/migration/audit/usage/export/delete, reset behavior, troubleshooting,
and clean shutdown. Real-HMS docs list every required provider variable and the
exact overlay command. The acceptance matrix maps every checkbox in #2–#10 to
a focused automated test and a runtime command.

- [ ] **Step 2: Run the fast release gate**

Run:

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm build
cd backend && .venv/bin/ruff check app tests
cd backend && .venv/bin/pytest -m 'not postgres and not hms and not compose' -q
git diff --check
```

Expected: all exit 0 with no warnings treated as failures.

- [ ] **Step 3: Run the clean Compose release gate**

Run:

```bash
docker compose down --volumes --remove-orphans
docker compose build
docker compose up -d --wait
docker compose exec -T mp-backend alembic upgrade head
docker compose exec -T mp-backend python -m app.seed.run_seed
docker compose exec -T mp-backend pytest -q
./scripts/demo.sh
docker compose ps
```

Expected: migrations reach head, seed is idempotent, every test passes, demo
exercises the complete customer story, and all required services are healthy.

- [ ] **Step 4: Validate real-HMS switching without spending credentials**

Run:

```bash
docker compose -f docker-compose.yml -f docker-compose.real.yml config
MP_MEMORY_ENGINE_MODE=real \
  HMS_API_LLM_API_KEY=openai_key_change_me \
  docker compose -f docker-compose.yml -f docker-compose.real.yml config
```

Then run the repository's real-mode validation command and assert it rejects
placeholder keys with the documented error. Do not make paid provider calls
without credentials supplied by the operator.

- [ ] **Step 5: Perform the requirement-by-requirement completion audit**

For each #2–#10 checkbox, record the fresh test/runtime evidence in
`docs/issue-acceptance.md`. Verify no `.github/workflows` file was added:

```bash
git diff --name-only origin/HMS...HEAD | rg '^\.github/workflows/' && exit 1 || true
gh issue list --state open --limit 100
git status -sb
```

Any unproven criterion returns to its owning task; absence of a failing test is
not accepted as proof.

- [ ] **Step 6: Commit final documentation and fixes**

Run the complete fast and Compose gates again after the last change, then:

```bash
git add README.md backend/README.md .env.example Makefile backend/Makefile \
  scripts docs backend src docker-compose.yml docker-compose.real.yml \
  eslint.config.mjs .gitignore
git commit -m "docs: publish local evaluation guide"
```

- [ ] **Step 7: Close issues and push**

Only after the acceptance matrix and fresh gates are green:

```bash
git push -u origin HMS
for issue in 2 3 4 5 6 7 8 9 10; do
  gh issue close "$issue" --comment "Completed and locally verified on branch HMS; see docs/issue-acceptance.md."
done
```

Expected: `origin/HMS` contains every commit, `git status -sb` is clean and
tracking the remote, and GitHub reports no remaining open V0.1 issues.
