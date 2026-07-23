#!/usr/bin/env bash
# Destructive only inside a uniquely named, disposable Compose project.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

ALEMBIC_HEAD_FILE="$(find "$REPO_DIR/backend/alembic/versions" \
  -type f -name '*.py' | sort | tail -n 1)"
EXPECTED_ALEMBIC_REVISION="$(sed -nE \
  's/^revision(:[^=]+)?= *"([^"]+)".*/\2/p' "$ALEMBIC_HEAD_FILE")"
if [[ ! "$EXPECTED_ALEMBIC_REVISION" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "Could not determine expected Alembic revision" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "SKIP: Docker Compose is unavailable" >&2
  exit 77
fi

TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-roundtrip.XXXXXX")"
PROJECT="mp-restore-it-$(date -u +%Y%m%d%H%M%S)-$$"
if [[ ! "$PROJECT" =~ ^mp-restore-it-[0-9]+-[0-9]+$ ]] ||
   [[ ! "$TEST_ROOT" =~ /mp-restore-roundtrip\.[a-zA-Z0-9]+$ ]]; then
  echo "Refusing to run with unvalidated isolation identifiers" >&2
  exit 1
fi

port_seed=$((($$ % 10000) + 30000))
export COMPOSE_PROJECT_NAME="$PROJECT"
export MP_PORT="${MP_RESTORE_TEST_MP_PORT:-$port_seed}"
export HMS_LOCAL_API_PORT="${MP_RESTORE_TEST_HMS_PORT:-$((port_seed + 1))}"
export BACKUP_DIR="$TEST_ROOT/backups"
export MP_DEMO_API_URL="http://127.0.0.1:$MP_PORT"

UP_ARGS=(up -d --wait)
if [ -n "${MP_RESTORE_TEST_BACKEND_IMAGE:-}" ]; then
  export COMPOSE_FILE="$REPO_DIR/docker-compose.yml:$REPO_DIR/scripts/tests/docker-compose.restore-roundtrip.yml"
  export MP_RESTORE_TEST_BACKEND_IMAGE
  UP_ARGS+=(--no-build)
  echo "==> reusing local backend image $MP_RESTORE_TEST_BACKEND_IMAGE"
else
  UP_ARGS+=(--build)
fi

cleanup() {
  local status=$?
  trap - EXIT
  if [[ "$PROJECT" =~ ^mp-restore-it-[0-9]+-[0-9]+$ ]]; then
    "${COMPOSE[@]}" -p "$PROJECT" down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
  if [[ "$TEST_ROOT" =~ /mp-restore-roundtrip\.[a-zA-Z0-9]+$ ]]; then
    rm -rf -- "$TEST_ROOT"
  fi
  exit "$status"
}
trap cleanup EXIT

AUTH_HEADER="Authorization: Bearer ${MP_SEED_API_KEY:-mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd}"
SENTINEL="Restore sentinel $PROJECT: Mia remembers the cobalt lighthouse."

echo "==> starting isolated Compose project $PROJECT"
"${COMPOSE[@]}" -p "$PROJECT" "${UP_ARGS[@]}"
"${COMPOSE[@]}" -p "$PROJECT" exec -T mp-backend alembic upgrade head
"${COMPOSE[@]}" -p "$PROJECT" exec -T mp-backend python -m app.seed.run_seed

ingest="$(curl -fsS -X POST "$MP_DEMO_API_URL/v1/events/ingest" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  --data "{\"user_id\":\"usr_mia\",\"agent_id\":\"agt_luna\",\"relationship_id\":\"rel_mia_luna\",\"source_type\":\"explicit_instruction\",\"content\":\"$SENTINEL\",\"event_id\":\"evt_$PROJECT\"}")"
memory_id="$(python3 -c 'import json,sys; body=json.load(sys.stdin); print(next(row["id"] for row in body["results"] if row["action"] == "ADD"))' <<<"$ingest")"
if [[ ! "$memory_id" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Unexpected sentinel memory id: $memory_id" >&2
  exit 1
fi

mapping_row="$("${COMPOSE[@]}" -p "$PROJECT" exec -T postgres \
  psql -U postgres -d memory_passport -At -v ON_ERROR_STOP=1 \
  -c "SELECT hms_unit_id || '|' || hms_document_id FROM memory_record_hms_units WHERE mp_memory_id = '$memory_id';")"
hms_unit_id="${mapping_row%%|*}"
if [[ -z "$hms_unit_id" || ! "$hms_unit_id" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Sentinel HMS mapping was not created" >&2
  exit 1
fi

migration_row="$("${COMPOSE[@]}" -p "$PROJECT" exec -T postgres \
  psql -U postgres -d memory_passport -At -v ON_ERROR_STOP=1 \
  -c "SELECT id || '|' || status::text FROM migrations ORDER BY id LIMIT 1;")"
migration_id="${migration_row%%|*}"
migration_status="${migration_row#*|}"
if [[ ! "$migration_id" =~ ^[a-zA-Z0-9_-]+$ ]] ||
   [[ ! "$migration_status" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Seeded business migration was not found" >&2
  exit 1
fi

echo "==> backing up sentinel state"
./scripts/backup.sh
snapshot="$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [ -z "$snapshot" ]; then
  echo "Backup snapshot was not created" >&2
  exit 1
fi

echo "==> mutating MP and HMS after backup"
"${COMPOSE[@]}" -p "$PROJECT" exec -T postgres \
  psql -U postgres -d memory_passport -v ON_ERROR_STOP=1 \
  -c "UPDATE memory_records SET content = 'MUTATED AFTER BACKUP' WHERE id = '$memory_id';" \
  -c "DELETE FROM memory_record_hms_units WHERE mp_memory_id = '$memory_id';" \
  -c "DELETE FROM audit_logs WHERE target = '$memory_id';" \
  -c "DELETE FROM migrations WHERE id = '$migration_id';"
"${COMPOSE[@]}" -p "$PROJECT" exec -T postgres \
  psql -U postgres -d hms -v ON_ERROR_STOP=1 \
  -c "UPDATE demo_hms_memory_units SET text = 'MUTATED AFTER BACKUP' WHERE id = '$hms_unit_id';"

echo "==> restoring and verifying the snapshot"
./scripts/restore.sh "$snapshot" <<<"memory_passport"

restored_content="$("${COMPOSE[@]}" -p "$PROJECT" exec -T postgres \
  psql -U postgres -d memory_passport -At -v ON_ERROR_STOP=1 \
  -c "SELECT content FROM memory_records WHERE id = '$memory_id';")"
[ "$restored_content" = "$SENTINEL" ] || {
  echo "MP sentinel text was not restored" >&2
  exit 1
}

"${COMPOSE[@]}" -p "$PROJECT" exec -T postgres \
  psql -U postgres -d memory_passport -At -v ON_ERROR_STOP=1 \
  -c "SELECT 1/CASE WHEN (SELECT count(*) FROM memory_record_hms_units WHERE mp_memory_id = '$memory_id') = 1 THEN 1 ELSE 0 END;" \
  -c "SELECT 1/CASE WHEN (SELECT version_num FROM alembic_version) = '$EXPECTED_ALEMBIC_REVISION' THEN 1 ELSE 0 END;" \
  -c "SELECT 1/CASE WHEN (SELECT count(*) FROM audit_logs WHERE target = '$memory_id') >= 1 THEN 1 ELSE 0 END;" \
  -c "SELECT 1/CASE WHEN (SELECT status::text FROM migrations WHERE id = '$migration_id') = '$migration_status' THEN 1 ELSE 0 END;" \
  >/dev/null
"${COMPOSE[@]}" -p "$PROJECT" exec -T postgres \
  psql -U postgres -d hms -At -v ON_ERROR_STOP=1 \
  -c "SELECT 1/CASE WHEN (SELECT text FROM demo_hms_memory_units WHERE id = '$hms_unit_id') = '$SENTINEL' THEN 1 ELSE 0 END;" \
  >/dev/null

retrieved="$(curl -fsS -X POST "$MP_DEMO_API_URL/v1/memories/retrieve" \
  -H "$AUTH_HEADER" \
  -H 'Content-Type: application/json' \
  --data '{"user_id":"usr_mia","agent_id":"agt_luna","relationship_id":"rel_mia_luna","query":"cobalt lighthouse","model":"restore-roundtrip"}')"
python3 -c 'import json,sys; body=json.load(sys.stdin); assert any("cobalt lighthouse" in row["content"].lower() for row in body["results"]), body' <<<"$retrieved"
curl -fsS "$MP_DEMO_API_URL/v1/audit_logs?target=$memory_id" -H "$AUTH_HEADER" |
  python3 -c 'import json,sys; body=json.load(sys.stdin); assert body["total"] >= 1, body'
curl -fsS "$MP_DEMO_API_URL/v1/health" |
  python3 -c 'import json,sys; body=json.load(sys.stdin); assert body["mp"] == body["db"] == body["hms"] == "ok", body'

echo "✓ isolated backup → mutate → restore round trip passed"
