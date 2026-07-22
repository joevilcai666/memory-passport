# Memory Passport

> Switch devices, not relationships. Switch models, not memory.

**B 端客户第一次安装和验收，请直接阅读：**
[`Memory Passport B 端客户安装与验收指南（中文）`](B2B_CUSTOMER_GUIDE.zh-CN.md)
| 想快速点击体验界面：[`客户快速上手指南（中文）`](CUSTOMER_QUICKSTART.zh-CN.md)

Memory Passport is an open-source, user-owned memory layer for AI companions
and robots. This repository contains a Next.js web console (wired to the real
backend, with seeded data as offline fallback) and a complete FastAPI backend
with tenant isolation, policy enforcement, versioned memory CRUD, device
migration, audit/usage aggregates, model-neutral exports, and privacy
deletion.

The default local stack is credential-free. It runs a deterministic service
that implements the same HTTP boundary used by HMS, so an evaluator can clone
the repository and exercise retain/recall without a paid model account. A
Compose overlay switches that service to the pinned real HMS API and worker
when valid LLM and embedding credentials are supplied.

## Run it locally

Requirements for the API demo: Docker Desktop/Engine with either
`docker compose` or `docker-compose`, Git, Make, curl, and Python 3. Node.js
22+ and pnpm 10+ are only required for the optional frontend and frontend
release checks.

```bash
git clone --branch main --recursive https://github.com/joevilcai666/memory-passport.git
cd memory-passport
cp .env.example .env        # optional for the default demo
make demo
```

`make demo` starts PostgreSQL, the deterministic HMS-compatible service, and
Memory Passport; migrates and seeds the Luna dataset; then verifies health,
ingest, retrieve, versioned edit, export, delete, audit, and usage over HTTP.

- Swagger: <http://localhost:8000/docs>
- API health: <http://localhost:8000/v1/health>
- Frontend (separate terminal): `pnpm install && pnpm dev`, then
  <http://localhost:3000>
- Seeded bearer key: `mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd`

The seeded key is exposed to the browser only for single-machine evaluation.
It is not a production authentication design. A deployed UI must authenticate
the user through a server-side session/BFF, keep tenant API keys on that
server, and proxy authorized Memory Passport calls.

Useful commands:

```bash
make up          # start the credential-free stack
make seed        # restore/upsert the Luna evaluator dataset
make check       # local frontend, backend, and Compose release gate
make down        # stop containers, preserve local data
make clean       # destructive: remove containers and database volumes
```

The full walkthrough, including curl examples for every API family, is in
[`docs/local-evaluation.md`](docs/local-evaluation.md).

## Real HMS inference

The repository keeps one MP→HMS HTTP contract in both modes:

```text
default: mp-backend -> deterministic hms-api -> PostgreSQL
real:    mp-backend -> pinned HMS API + worker -> LLM/embedding providers
```

Set the three provider keys in `.env`, adjust providers/models/base URLs if
needed, then run:

```bash
make real-up
```

Real mode fails fast while any LLM, retain-LLM, or embedding credential is
missing or still a `*_change_me` placeholder. See
[`docs/real-hms.md`](docs/real-hms.md) for the exact variables and verification
commands. The default `make demo` never calls a paid provider.

## Production hardening

The default stack is loopback-only with placeholder credentials — correct for a
single-machine eval, wrong for shared infrastructure. The repo ships the
self-service pieces to move past that:

- **TLS / reverse proxy** — `make tls-up` runs Caddy in front of `mp-backend`
  with auto-HTTPS on a real domain or an internal CA for LAN-only deploys
  ([`docker/caddy/Caddyfile`](docker/caddy/Caddyfile),
  [`docker-compose.tls.yml`](docker-compose.tls.yml)).
- **DB password parameterization** — `docker/postgres-init.sh` now reads
  `MP_DB_PASSWORD` / `HMS_DB_PASSWORD` from the environment, so a single
  `.env` override flows end-to-end.
- **Backups + restore** — `make backup` dumps both databases;
  `make restore STAMP=<timestamp>` replays them
  ([`scripts/backup.sh`](scripts/backup.sh), [`scripts/restore.sh`](scripts/restore.sh)).
  Restore pre-creates pgvector with the administrator role, restores all other
  objects as the database owner, and fails on any archive or verification
  error. `make restore-verify` performs a destructive backup/restore parity
  check against the default local stack.
- **Monitoring** — scrape `GET /v1/health` (returns 503 when HMS or DB is
  down); example Prometheus config in the guide.

The full walkthrough — TLS, secrets management + rotation, backup scheduling,
Prometheus alerting, HMS access control, region/compliance checklist — lives in
[`docs/production-hardening.md`](docs/production-hardening.md).

## What is implemented

- API-key authentication and strict tenant scoping
- Apps, agents, users, relationships, device pairing/bind/unbind/wipe
- HMS-backed ingest and recall with MP↔HMS mappings and debug traces
- Scope filtering, sensitivity masking, and live auto-write policies
- Versioned memory edits, explicit state machine, and tombstone deletion
- Reversible Luna Robot v1→v2 migration with partial-failure retry
- Filterable audit logs and five usage dimensions
- Asynchronous model-neutral JSON exports with expiring download tokens
- Delete-user cascade: HMS bank deletion, tombstones, mapping removal, and
  passport revocation
- Alembic migrations with clean upgrade/downgrade tests

Acceptance evidence for GitHub issues #2–#10 is mapped to automated tests in
[`docs/issue-acceptance.md`](docs/issue-acceptance.md).

## Repository layout

```text
backend/                  FastAPI domain service, Alembic, pytest suite
src/                      Next.js 16 App Router web console (wired to backend)
vendor/hms/               pinned real HMS git submodule
docker-compose.yml        zero-credential evaluator stack
docker-compose.real.yml   real HMS API/worker overlay
scripts/demo.sh           executable local customer journey
docs/                     evaluation, HMS, and acceptance documentation
```

## Development

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm build

cd backend
uv venv
uv pip install -e '.[dev]'
.venv/bin/ruff check app tests
.venv/bin/pytest -q
```

Tests that require PostgreSQL/HMS skip cleanly on a host without services and
run automatically inside the Compose gate. This project intentionally uses
local verification commands and does not depend on GitHub Actions.

## Product surfaces

The frontend preserves the interactive Luna story:

- `/console/*`: B-side admin console, policies, users, devices, and audit log
- `/app/*`: user consent, memory center, device binding, and migration hero flow

The UI is wired to the FastAPI backend via a typed HTTP client
(`src/lib/api-client.ts`); on mount it hydrates memories, audit logs, and
usage from the backend, and mutations (edit, delete, policy, migration, …)
call the backend live. Success state is shown only after the API resolves.
When the backend is unreachable, the store falls back to the seeded Luna
dataset in read-only mode so the UI keeps rendering without pretending that
writes succeeded. The backend is also independently runnable and fully
testable through its HTTP API.

## License and security

Never commit real provider credentials. `.env` and generated export artifacts
are ignored. Local placeholder database/API keys are evaluator-only defaults,
not production secrets. Review the repository license before redistribution.
