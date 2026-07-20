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

retrieve="$(curl -fsS -X POST "$api_url/v1/memories/retrieve" \
  -H "$auth_header" \
  -H 'Content-Type: application/json' \
  --data '{"user_id":"usr_mia","agent_id":"agt_luna","relationship_id":"rel_mia_luna","query":"jasmine tea","model":"local-demo"}')"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert any("jasmine tea" in row["content"].lower() for row in body["results"]), body' <<<"$retrieve"

echo "Memory Passport local demo passed: $api_url/docs"
