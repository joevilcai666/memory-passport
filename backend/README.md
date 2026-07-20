# Memory Passport Backend

FastAPI + SQLAlchemy + Alembic service implementing the Memory Passport V0.1
domain model over one HMS-compatible HTTP boundary.

## Architecture

```text
client -> mp-backend :8000 -> hms-api :18080 -> PostgreSQL/pgvector
              |                 |
              |                 +-- deterministic implementation (default)
              |                 +-- pinned HMS API + worker (real overlay)
              +-- MP schema, auth, policy, CRUD, audit, exports
```

Memory Passport owns identity, sensitivity, scope, portability, state,
versioning, policy, audit, and privacy semantics. HMS owns extraction,
embedding, deduplication, and semantic recall. `bank_id` is always the MP
`user_id`.

## Quick start

From the repository root:

```bash
make demo
```

Or operate the backend stack directly:

```bash
make -C backend up
make -C backend migrate
make -C backend seed
make -C backend test
```

The Makefiles detect the Docker Compose plugin and fall back to standalone
`docker-compose`. Swagger is at <http://localhost:8000/docs>.

## API families

All business endpoints require
`Authorization: Bearer mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd` in the seeded
environment.

| Capability | Endpoints |
|---|---|
| Health | `GET /v1/health` |
| Provisioning | `POST /v1/apps`, `/agents`, `/users`, `/relationships` |
| Devices | `POST /v1/devices/register`, `/bind`, `/unbind`, `/wipe` |
| Memory pipeline | `POST /v1/events/ingest`, `/v1/memories/retrieve` |
| CRUD | `GET /v1/memories`, `PATCH/DELETE /v1/memories/{id}` |
| Debug | `GET /v1/debug/traces/{trace_id}` |
| Policy | `POST /v1/policies` |
| Migration | `POST /v1/migrations/preview`, `/execute`, `/{id}/rollback`; `GET /{id}` |
| Aggregates | `GET /v1/audit_logs`, `/v1/usage` |
| Data operations | `POST /v1/exports`, `GET /v1/exports/{id}`, download, `POST /v1/delete_user` |

See [`../docs/local-evaluation.md`](../docs/local-evaluation.md) for request
bodies and runnable curl examples.

## Configuration

`Settings` uses the `MP_` prefix, except shared `DATABASE_URL`, `HMS_API_URL`,
and `HMS_API_KEY` aliases.

| Variable | Default/purpose |
|---|---|
| `DATABASE_URL` | MP PostgreSQL connection |
| `HMS_API_URL` / `HMS_API_KEY` | HMS-compatible upstream and bearer key |
| `MP_MEMORY_ENGINE_MODE` | `demo` or `real` |
| `MP_RUN_MIGRATIONS_ON_STARTUP` | apply Alembic head on boot |
| `MP_EXPORT_DIR` | export artifact directory |
| `MP_EXPORT_TOKEN_TTL_SECONDS` | download token lifetime; default 900 |
| `HMS_API_LLM_API_KEY` | real HMS general LLM key |
| `HMS_API_RETAIN_LLM_API_KEY` | real HMS retain/extraction key |
| `HMS_API_EMBEDDINGS_OPENAI_API_KEY` | real HMS embedding key |

Real HMS configuration is documented in
[`../docs/real-hms.md`](../docs/real-hms.md).

## Local Python development

```bash
cd backend
uv venv
uv pip install -e '.[dev]'

# fast SQLite/respx suite; service tests skip if dependencies are absent
.venv/bin/ruff check app tests
.venv/bin/pytest -q

# service-backed suite
cd ..
docker-compose up -d --wait
docker-compose exec -T mp-backend pytest -q
```

Pytest markers:

- `postgres`: needs a reachable PostgreSQL service
- `hms`: needs a reachable HMS-compatible HTTP service
- `compose`: exercises the complete stack

## Database lifecycle

```bash
make -C backend migrate       # upgrade to head
make -C backend downgrade     # destructive: downgrade to base
make -C backend seed          # idempotently upsert Luna rows and HMS banks
```

The migrations include MP↔HMS mappings, retrieval traces, migration rollback
state, usage events, export jobs, and passport deletion state. PostgreSQL
upgrade/downgrade is covered by `tests/test_migrations.py`.

## Default versus real HMS

The default Compose file starts `app.demo_hms`, a deterministic implementation
of the paths MP consumes. It is intended for local evaluation, contract tests,
and contributor development; it does not pretend to perform LLM inference.

`docker-compose.real.yml` replaces that service with the pinned submodule image
and adds the HMS worker. The MP code and URLs do not change. Real mode fails
fast unless all LLM and embedding credentials are non-placeholder values.

## Safety properties

- Cross-tenant references fail closed.
- `cross_brand_app` cannot be enabled in V0.1.
- Deleted/tombstoned/passport-deleted memories never reach recall output.
- User deletion calls HMS before committing the local cascade.
- Export bundles contain model-neutral MP fields, not embeddings, secrets, or
  provider payloads.
- Download tokens are short-lived; only SHA-256 hashes are persisted.
