# Memory Passport — Backend (V0.1, Slice 1)

A Python **FastAPI** domain service that wraps the
[Holographic Memory System (HMS)](https://github.com/Shadow-Weave/HMS) memory
engine and implements the Memory Passport data model (PRD v2.0 §7–§11). This
slice ships the **runnable foundation**: the docker-compose stack, the MP
Postgres schema, API-key auth, `/v1/health`, and the Luna seed dataset. No
business endpoints yet — every later slice builds on this.

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

## What this slice does NOT include (deferred)

- Real Ingest/Retrieve/Migration endpoints (PRD §7.7–§7.9). Only `/v1/health` ships.
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
