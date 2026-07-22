# Local Evaluation Guide

This guide exercises the open-source Memory Passport backend without paid model
credentials. The default `hms-api` is deterministic but uses the same network
paths and response contract as real HMS.

## Prerequisites and clone

- Docker Desktop/Engine; either `docker compose` or `docker-compose`
- Git
- Node.js 22+ and pnpm 10+ for frontend verification
- `curl` and Python 3 for the executable demo

Windows evaluators should use WSL2 for the full `make demo` workflow. The
supported native PowerShell Compose path and its role/database verification are
documented in [`windows.md`](windows.md).

```bash
git clone --branch HMS --recursive https://github.com/joevilcai666/memory-passport.git
cd memory-passport
git submodule update --init --recursive
cp .env.example .env   # optional in demo mode
make demo
```

Expected final line:

```text
Memory Passport local demo passed: http://127.0.0.1:8000/docs
```

The stack binds only to loopback by default. Open Swagger at
<http://localhost:8000/docs>.

## Shell setup

The examples below use the seeded Luna tenant.

```bash
export MP_API=http://127.0.0.1:8000
export MP_KEY=mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd
export MP_AUTH="Authorization: Bearer $MP_KEY"
curl -s "$MP_API/v1/health" | python3 -m json.tool
```

Health must report `mp`, `hms`, and `db` as `ok`, plus
`"memory_engine": "demo"`.

## Provisioning

Create a disposable user; the response contains its generated `id` and
`passport_id`, while HMS gets a bank with `bank_id == user_id`.

```bash
curl -sS -X POST "$MP_API/v1/users" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{
    "app_id":"app_luna",
    "external_user_id":"local-evaluator-1",
    "age_group":"adult",
    "region":"US",
    "display_name":"Local Evaluator"
  }' | python3 -m json.tool
```

Apps, agents, relationships, and device register/bind/unbind/wipe requests are
all discoverable and executable in Swagger. Device bind requires the one-time
pairing code returned by register.

## Ingest and retrieve

```bash
curl -sS -X POST "$MP_API/v1/events/ingest" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{
    "user_id":"usr_mia",
    "agent_id":"agt_luna",
    "relationship_id":"rel_mia_luna",
    "source_type":"explicit_instruction",
    "content":"Mia prefers jasmine tea during local evaluation.",
    "event_id":"evt_docs_local_1"
  }' | python3 -m json.tool

curl -sS -X POST "$MP_API/v1/memories/retrieve" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{
    "user_id":"usr_mia",
    "agent_id":"agt_luna",
    "relationship_id":"rel_mia_luna",
    "query":"jasmine tea",
    "model":"local-evaluator"
  }' | python3 -m json.tool
```

The retrieve response includes a `trace_id`. Inspect it with:

```bash
curl -sS "$MP_API/v1/debug/traces/TRACE_ID" -H "$MP_AUTH" | python3 -m json.tool
```

## Memory CRUD

Use a memory ID returned by ingest:

```bash
curl -sS "$MP_API/v1/memories?user_id=usr_mia&page=1&page_size=20" \
  -H "$MP_AUTH" | python3 -m json.tool

curl -sS -X PATCH "$MP_API/v1/memories/MEMORY_ID" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{"content":"Mia prefers jasmine green tea."}' | python3 -m json.tool

curl -sS -X PATCH "$MP_API/v1/memories/MEMORY_ID" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{"status":"needs_review"}' | python3 -m json.tool

curl -sS -X DELETE "$MP_API/v1/memories/MEMORY_ID" \
  -H "$MP_AUTH" | python3 -m json.tool
```

Content edits create a new active version and archive the old ID. Illegal
state transitions return 409. Add `include_deleted=true` to list tombstones.

## Policy

The following preserves V0.1's cross-brand prohibition and makes S1
relationship events auto-write:

```bash
curl -sS -X POST "$MP_API/v1/policies" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{
    "app_id":"app_luna",
    "agent_id":"agt_luna",
    "auto_write_rules":[
      {"memory_type":"relationship","action":"auto_write","sensitivity":"S1","ttl_days":null}
    ],
    "portability":{
      "layer":"portable","cross_device":true,"cross_role":true,
      "cross_model":true,"cross_brand_app":false
    },
    "retrieval":{"max_memories_per_response":8,"include_sensitive_in_prompt":false}
  }' | python3 -m json.tool
```

Setting `cross_brand_app` to true is rejected with 422 and writes nothing.
Run `make seed` to restore the full six-rule Luna policy after experimentation.

## Luna migration

```bash
curl -sS -X POST "$MP_API/v1/migrations/preview" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{
    "user_id":"usr_mia",
    "source_relationship_id":"rel_mia_luna",
    "target_relationship_id":"rel_mia_luna_v2",
    "source_device_id":"dev_luna_v1",
    "target_device_id":"dev_luna_v2"
  }' | python3 -m json.tool

curl -sS -X POST "$MP_API/v1/migrations/execute" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{
    "migration_id":"mig_001",
    "selected_memory_ids":["mem_013"],
    "old_device_access":"keep"
  }' | python3 -m json.tool

curl -sS -X POST "$MP_API/v1/migrations/mig_001/rollback" \
  -H "$MP_AUTH" | python3 -m json.tool
```

Migration only changes MP device links. The HMS bank remains `usr_mia`.

## Audit and usage

```bash
curl -sS "$MP_API/v1/audit_logs?page=1&page_size=20" \
  -H "$MP_AUTH" | python3 -m json.tool
curl -sS "$MP_API/v1/audit_logs?action=memory.edited" \
  -H "$MP_AUTH" | python3 -m json.tool
curl -sS "$MP_API/v1/usage" -H "$MP_AUTH" | python3 -m json.tool
```

Both endpoints are read-only. `since` and `until` accept URL-encoded ISO-8601
timestamps and use inclusive UTC bounds.

## Export

```bash
EXPORT_ID=$(curl -sS -X POST "$MP_API/v1/exports" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{"user_id":"usr_mia"}' | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["export_id"])')

curl -sS "$MP_API/v1/exports/$EXPORT_ID" -H "$MP_AUTH" | python3 -m json.tool
```

Poll status until `completed`, then request its relative `download_url` with
the same bearer key. The bundle format is `memory-passport/v1` and never
contains embeddings, provider payloads, or API keys.

## Delete user

Use only a disposable user ID. This operation deletes the user's HMS bank,
tombstones every MP memory, removes MP↔HMS mappings, and revokes the passport.

```bash
curl -sS -X POST "$MP_API/v1/delete_user" \
  -H "$MP_AUTH" -H 'Content-Type: application/json' \
  --data '{"user_id":"DISPOSABLE_USER_ID"}' | python3 -m json.tool
```

Cross-tenant targets are explicitly rejected with 403. A deleted passport's
retrieve path returns an empty, auditable trace without calling HMS.

## Verification and lifecycle

```bash
make check       # complete local release gate
make down        # preserve database and exports
make demo        # idempotently upsert seed data and run the customer journey
make clean       # destructive: delete database volumes and local stack state
```

Troubleshooting:

- If `docker compose` is unavailable, the Makefile automatically tries
  standalone `docker-compose`.
- Port conflicts: override `MP_PORT` or `HMS_LOCAL_API_PORT` in `.env`.
- Stale schema: `docker-compose exec -T mp-backend alembic upgrade head`.
- Completely fresh evaluator state: `make clean && make demo`.
- Service logs: `docker-compose logs --tail=200 mp-backend hms-api postgres`.
