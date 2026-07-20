#!/usr/bin/env bash
set -euo pipefail

api_url="${MP_DEMO_API_URL:-http://127.0.0.1:8000}"
api_key="${MP_SEED_API_KEY:-mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd}"
auth_header="Authorization: Bearer $api_key"
event_id="evt_local_demo_$(date +%s)"

health="$(curl -fsS "$api_url/v1/health")"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert body == {"mp":"ok","hms":"ok","db":"ok","memory_engine":"demo"}, body' <<<"$health"

ingest="$(curl -fsS -X POST "$api_url/v1/events/ingest" \
  -H "$auth_header" \
  -H 'Content-Type: application/json' \
  --data "{\"user_id\":\"usr_mia\",\"agent_id\":\"agt_luna\",\"relationship_id\":\"rel_mia_luna\",\"source_type\":\"explicit_instruction\",\"content\":\"For the local demo, Mia prefers jasmine tea.\",\"event_id\":\"$event_id\"}")"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert any(row["action"] == "ADD" for row in body["results"]), body' <<<"$ingest"
memory_id="$(python3 -c 'import json,sys; body=json.load(sys.stdin); print(next(row["id"] for row in body["results"] if row["action"] == "ADD"))' <<<"$ingest")"

retrieve="$(curl -fsS -X POST "$api_url/v1/memories/retrieve" \
  -H "$auth_header" \
  -H 'Content-Type: application/json' \
  --data '{"user_id":"usr_mia","agent_id":"agt_luna","relationship_id":"rel_mia_luna","query":"jasmine tea","model":"local-demo"}')"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert any("jasmine tea" in row["content"].lower() for row in body["results"]), body' <<<"$retrieve"

edited="$(curl -fsS -X PATCH "$api_url/v1/memories/$memory_id" \
  -H "$auth_header" \
  -H 'Content-Type: application/json' \
  --data '{"content":"For the local demo, Mia prefers jasmine green tea."}')"
edited_id="$(python3 -c 'import json,sys; body=json.load(sys.stdin); assert body["version"] == 2 and body["supersedes"]; print(body["id"])' <<<"$edited")"

export_created="$(curl -fsS -X POST "$api_url/v1/exports" \
  -H "$auth_header" \
  -H 'Content-Type: application/json' \
  --data '{"user_id":"usr_mia"}')"
export_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["export_id"])' <<<"$export_created")"
export_status="$(curl -fsS "$api_url/v1/exports/$export_id" -H "$auth_header")"
download_url="$(python3 -c 'import json,sys; body=json.load(sys.stdin); assert body["status"] == "completed", body; print(body["download_url"])' <<<"$export_status")"
export_bundle="$(curl -fsS "$api_url$download_url" -H "$auth_header")"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert body["format"] == "memory-passport/v1"; assert all("embedding" not in json.dumps(row).lower() for row in body["memories"])' <<<"$export_bundle"

deleted="$(curl -fsS -X DELETE "$api_url/v1/memories/$edited_id" -H "$auth_header")"
python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "deleted"' <<<"$deleted"

audit="$(curl -fsS "$api_url/v1/audit_logs?target=$edited_id" -H "$auth_header")"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert body["total"] >= 1, body' <<<"$audit"

usage="$(curl -fsS "$api_url/v1/usage" -H "$auth_header")"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert set(body["memory_ops"]) == {"ingest","retrieve","update","delete"}, body' <<<"$usage"

echo "Memory Passport local demo passed: $api_url/docs"
