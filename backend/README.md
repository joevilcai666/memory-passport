# Memory Passport — Backend (V0.1)

A Python **FastAPI** domain service that wraps the
[Holographic Memory System (HMS)](https://github.com/Shadow-Weave/HMS) memory
engine and implements the Memory Passport data model (PRD v2.0 §7–§11). Slice 1
shipped the **runnable foundation**: the docker-compose stack, the MP Postgres
schema, API-key auth, `/v1/health`, and the Luna seed dataset. Slice 2 adds the
**provisioning endpoints** (apps / agents / users / relationships / devices).
Every later slice builds on this.

> The Next.js prototype in `../src` is unchanged. The backend lives in
> `backend/`; the two share a repo but not a process.

---

## Architecture

```
                 ┌─────────────────────────────────────────────┐
   client ──HTTP──▶ mp-backend (FastAPI :8000)                  │
                 │   • /v1/health                               │
                 │   • API-key auth middleware                  │
                 │   • MP Postgres schema (memory_passport DB)  │
                 └───────────────┬─────────────────────────────┘
                                 │ Bearer ${HMS_API_TENANT_API_KEY}
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │ hms-api (FastAPI :18080, vendored submodule) │
                 │   • PUT /v1/default/banks/{bank_id}          │
                 │   • retain / recall (later slices)           │
                 │   • tenant_luna PG schema (HMS DB)           │
                 └───────────────┬─────────────────────────────┘
                                 │ polls task backend
                                 ▼
                          hms-worker (standalone CLI, same image)
                                 │
                                 ▼
                          postgres (pgvector/pgvector:pg16)
                          ├── memory_passport (mp role)
                          └── hms (hms role, tenant_luna schema)
```

- **postgres** — one shared `pgvector/pgvector:pg16` instance with two
  isolated databases: `memory_passport` (MP) and `hms` (HMS). Provisioned by
  `docker/postgres-init.sh` on first boot.
- **hms-api** — HMS FastAPI service, built from the vendored submodule at
  `vendor/hms`. Migrations run on startup; the in-process worker is disabled.
- **hms-worker** — the same HMS image running the standalone `hms-worker` CLI
  (the async-retain poller). Separate service so the stack is horizontally
  scalable.
- **mp-backend** — this package. Hot-reloads in dev (`uvicorn --reload`).

### Why a submodule?

HMS has no published image or release tags, and the repo is young (the pinned
commit `a808ab393ca0` is from 2026-07-15). `vendor/hms` is a git submodule
pinned to that exact commit — `git submodule update --init --recursive` after
clone fetches it, and `docker-compose build` builds the image from
`vendor/hms/docker/hms-api.Dockerfile`.

---

## Quick start

```bash
# 1. Clone with submodules
git clone --recursive <repo-url>
cd MemoryPassport

# (already cloned?) fetch the HMS submodule:
git submodule update --init --recursive

# 2. Configure env (edit *_change_me values)
cp .env.example .env

# 3. Build + start the full stack
make -C backend build      # or: docker-compose build
make -C backend dev        # builds, starts, tails mp-backend logs

# 4. Seed the Luna dataset + provision empty HMS banks
make -C backend seed

# 5. Smoke test
curl -s http://localhost:8000/v1/health
# -> {"mp":"ok","hms":"ok","db":"ok"}

# 6. Run the test suite
make -C backend test
```

---

## Make targets

| Target | Description |
|---|---|
| `make build` | Build all four docker images. |
| `make up` / `make down` | Start / stop the stack (volumes persist). |
| `make dev` | Start + tail `mp-backend` logs. |
| `make ps` | Service status (all should be `healthy`). |
| `make logs` | Tail logs from every service. |
| `make migrate` | `alembic upgrade head`. |
| `make downgrade` | `alembic downgrade base` — clean slate (DESTRUCTIVE). |
| `make seed` | Seed Luna dataset + 4 empty HMS banks. |
| `make test` | Run the pytest suite inside the `mp-backend` container. |
| `make smoke` | The Slice 1 acceptance flow: up → seed → `/v1/health`. |
| `make clean` | Stop + **remove volumes** (wipes all DB data). |

All targets shell out to `docker-compose`; the host only needs Docker.

---

## Environment variables

Copy `.env.example` (repo root) to `.env` and fill in the `*_change_me`
values. `docker-compose up` reads `.env` automatically.

### Memory Passport

| Var | Default | Purpose |
|---|---|---|
| `MP_PORT` | `8000` | Host port for `mp-backend`. |
| `MP_DB_USER` / `MP_DB_PASSWORD` / `MP_DB_NAME` | `mp` / `mp_dev_password_change_me` / `memory_passport` | MP's Postgres role + DB. |
| `MP_SEED_API_KEY` | `mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd` | Seeded sandbox key — **must match** `src/lib/mock-data.ts` so the auth acceptance test holds. |
| `MP_RUN_MIGRATIONS_ON_STARTUP` | `true` | Run Alembic on boot. |
| `MP_LOG_LEVEL` | `info` | uvicorn/app log level. |

### Postgres

| Var | Purpose |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Superuser for the `pgvector/pgvector:pg16` instance. |

### HMS

| Var | Purpose |
|---|---|
| `HMS_DB_USER` / `HMS_DB_PASSWORD` / `HMS_DB_NAME` | HMS's Postgres role + DB. |
| `HMS_API_TENANT_API_KEY` | Single shared tenant key for Slice 1 — MP sends this as `Authorization: Bearer …` when calling hms-api. |
| `HMS_API_DATABASE_SCHEMA` | `tenant_luna` — every HMS bank lives under this PG schema. |
| `HMS_API_SKIP_LLM_VERIFICATION` | `true` — skip the OpenAI connectivity probe on boot (Slice 1 makes no LLM calls). Set `false` + real keys when later slices run retain/recall. |
| `HMS_API_LLM_*` / `HMS_API_RETAIN_LLM_*` / `HMS_API_EMBEDDINGS_*` | LLM + embedding provider config passed through to hms-api. Placeholder values are fine for Slice 1 (no calls made). |

---

## The Luna seed dataset

`app/seed/data.py` is a faithful port of `../src/lib/mock-data.ts`. Counts:

| Entity | Count |
|---|---|
| tenants | 1 (`ten_luna`) |
| apps | 1 (`app_luna`) |
| api_keys | 2 (sandbox unmasked, production redacted) |
| users | 4 (`usr_mia` primary + alex/sam/jordan) |
| agents | 2 (Luna companion + Luna Robot) |
| devices | 4 (3× v1 + 1× v2) |
| relationships | 1 (`rel_mia_luna`) |
| memory_policies | 1 (with 6 auto-write rules) |
| memory_records | 42 (Preferences 12 / Relationship 8 / Events 9 / Boundaries 4 / Tasks 6 / Archived 3) |
| migrations | 1 (`mig_001`, status `preview`) |
| audit_logs | 8 |

The seed also provisions **one empty HMS bank per user** (`bank_id == user_id`)
under the `tenant_luna` HMS schema, via `PUT /v1/default/banks/{bank_id}`.

---

## Slice 2 — Provisioning endpoints

The seven `POST` endpoints that create the core entities a memory pipeline
needs (PRD v2.0 §8). All are under `/v1`, all require
`Authorization: Bearer mp_<env>_<secret>`, and all return the created entity
with a generated `id` + timestamps. Each successful creation appends an
`AuditLog` row (`actor = api:<key_id>`).

| Endpoint | Body (highlights) | Returns |
|---|---|---|
| `POST /v1/apps` | `name`, `product_type`, `environment`, `data_region`, `show_powered_by` | `{ app, api_key }` — the new App + its first auto-generated `mp_<env>_<secret>` key (shown once) |
| `POST /v1/agents` | `app_id`, `name`, `type`, `persona_version`, `allowed_memory_types`, `emoji` | `Agent` |
| `POST /v1/users` | `app_id`, `external_user_id`, `age_group?`, `region`, `display_name` | `User` — generates `passport_id`; **idempotent** on `(app_id, external_user_id)` and provisions an HMS bank (`bank_id == user_id`) on first sight only |
| `POST /v1/relationships` | `user_id`, `agent_id`, `device_id?`, `relationship_type`, `memory_enabled?` | `Relationship` |
| `POST /v1/devices/register` | `model`, `generation`, `serial_number_hash` | `{ device, pairing_code }` — device in `registered` status + a one-time 8-char pairing code |
| `POST /v1/devices/bind` | `device_id`, `user_id`, `pairing_code` | `Device` — transitions `registered → bound`; **anonymous / code-less binds are rejected** (403) per PRD §9.1 |
| `POST /v1/devices/unbind` | `device_id` | `Device` — transitions `bound → unbound` |
| `POST /v1/devices/wipe` | `device_id` | `{ device, tombstoned_memories }` — transitions `bound → wiped`; tombstones the device's `device_only` memories (Slice 7) |

**Device state machine** — `bind` is only legal from `registered`, `unbind`
only from `bound`, `wipe` only from `bound`. Any illegal transition returns
`409 Conflict` with
`{ "code": "illegal_state_transition", "current": "...", "action": "..." }`.

**Tenant isolation** — every lookup is scoped to the caller's tenant. A
reference to another tenant's row returns `404` (not `403`) so existence isn't
leaked.

`transfer` / `repair_mode` device operations are deferred (P1).

---

## Slice 3 — Ingest (`POST /v1/events/ingest`)

The architecture-validating tracer — the first slice that exercises the
MP↔HMS contract end-to-end. Accepts a raw event, resolves the user/agent/
relationship/device context, runs the app's `MemoryPolicy` auto-write rules,
then calls **HMS `retain`** (`bank_id = user_id`) to do fact extraction +
embedding + dedup. Each extracted HMS fact is mirrored as an MP
`MemoryRecord` carrying the rich domain fields HMS doesn't know about
(`sensitivity`, `portability`, `scope`, `source.quote`, `model_provenance`).

| Endpoint | Body (highlights) | Returns |
|---|---|---|
| `POST /v1/events/ingest` | `user_id`, `agent_id`, `relationship_id`, `device_id?`, `source_type`, `content`, `quote?`, `event_id?` | `{ event_id, results: [{ id, action }] }` — action ∈ `ADD`/`UPDATE`/`NOOP`/`BLOCKED` |

**Sensitivity → action (PRD §7):** S0/S1 → `active` (auto-write); S2 →
`candidate` (visible in console, not in retrieve by default); S3 → **blocked
end-to-end** (no HMS call, no MP record, `memory.blocked` audit only).

**HMS failure** (5xx/timeout) → `502 hms_retain_failed` + rollback (no partial
MP rows).

---

## Slice 4 — Retrieve + debug traces

The read-side counterpart to Slice 3. Given a query + a user/agent/device
context, calls **HMS `recall`** (`bank_id = user_id`), joins the results back
to MP `MemoryRecord`s via the Slice 3 mapping table, applies the scope matrix
+ sensitivity masking, and appends a `RetrievalEvent` to each returned memory's
`model_provenance.retrieval_history` (the cross-model parity moat, PRD §9.4).

| Endpoint | Body / param | Returns |
|---|---|---|
| `POST /v1/memories/retrieve` | `user_id`, `agent_id`, `relationship_id`, `device_id?`, `query`, `model?` | `{ trace_id, results: [RetrievedMemory] }` |
| `GET /v1/debug/traces/{trace_id}` | — | the full retrieval event chain (query, HMS results, projected records, retrieval events) |

**Scope matrix (PRD §9.1):** `blocked` → never; `private` → only the
originating agent; `device_only` → only the bound device AND device.status ==
`bound` (a **wiped** device loses access — ties into Slice 7); `agent_only` →
only that agent; `relationship_only` → only within the relationship;
`user_global` → any of the user's relationships.

**Sensitivity masking:** when
`policy.retrieval.include_sensitive_in_prompt == false`, S2/S3 content is
projected as `[redacted]` (the DB row is untouched).

**Cap:** at most `policy.retrieval.max_memories_per_response` records.

Traces persist for ≥7 days (PRD §8 P0); V0.1 enforces this by row age.

---

## Slice 7 — Device wipe (`POST /v1/devices/wipe`)

The privacy-positive "factory reset" path (PRD §8). Transitions a `bound`
device to `wiped`, clears `bound_user_id` (revoking its read authorization
end-to-end), and tombstones every `device_only`-scoped memory tied to it
(`status = deleted`, soft-delete per PRD §9.1). Memories in other scopes
(`user_global`, `relationship_only`, …) on the same device are untouched.

Post-wipe retrieve rejection is enforced by Slice 4's scope matrix: a wiped
device's `device_only` memories are filtered out (`is_readable` requires
`caller_device_status == 'bound'`).

---

## What this slice does NOT include (deferred)

- Device `transfer` / `repair_mode` states (P1 per the PRD).
- A custom HMS `TenantExtension` mapping multiple MP tenants to multiple HMS
  schemas. Slice 1 has exactly one tenant and uses HMS's built-in
  `ApiKeyTenantExtension` with `HMS_API_DATABASE_SCHEMA=tenant_luna`. See
  `app/hms/tenant.py` for the documented next-slice plan.
- Cross-brand-app portability (locked off in V0.1 per the PRD).

---

## Local (non-docker) development

```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
# Point DATABASE_URL + HMS_API_URL at a local postgres / hms-api:
export DATABASE_URL="postgresql+psycopg://mp:mp_dev_password_change_me@localhost:5432/memory_passport"
export HMS_API_URL="http://localhost:18080"
export HMS_API_KEY="hms_tenant_luna_change_me"
alembic upgrade head
python -m app.seed.run_seed
uvicorn app.main:app --reload
pytest                # health/auth run on sqlite; seed/smoke/migration tests need PG
```
