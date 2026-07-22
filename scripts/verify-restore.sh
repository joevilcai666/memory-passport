#!/usr/bin/env bash
# Destructive default-stack backup/restore verification.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

# shellcheck disable=SC1091
[ -f .env ] && set -a && . ./.env && set +a

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres_dev_password_change_me}"
MP_DB_NAME="${MP_DB_NAME:-memory_passport}"
HMS_DB_NAME="${HMS_DB_NAME:-hms}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=(docker-compose)
fi

psql_value() {
  local db="$1"
  local sql="$2"
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d "$db" -Atqc "$sql" | tr -d '\r'
}

snapshot() {
  local mp hms mp_vector hms_vector
  mp="$(psql_value "$MP_DB_NAME" \
    "SELECT concat_ws(',', (SELECT count(*) FROM tenants), (SELECT count(*) FROM apps), (SELECT count(*) FROM users), (SELECT count(*) FROM devices), (SELECT count(*) FROM memory_records), (SELECT count(*) FROM memory_record_hms_units), (SELECT count(*) FROM memory_policies), (SELECT count(*) FROM migrations), (SELECT count(*) FROM audit_logs));")"
  hms="$(psql_value "$HMS_DB_NAME" \
    "SELECT concat_ws(',', (SELECT count(*) FROM demo_hms_banks), (SELECT count(*) FROM demo_hms_memory_units));")"
  mp_vector="$(psql_value "$MP_DB_NAME" \
    "SELECT count(*) FROM pg_extension WHERE extname = 'vector';")"
  hms_vector="$(psql_value "$HMS_DB_NAME" \
    "SELECT count(*) FROM pg_extension WHERE extname = 'vector';")"
  printf 'mp=%s;hms=%s;vector=%s,%s' "$mp" "$hms" "$mp_vector" "$hms_vector"
}

if ! "${COMPOSE[@]}" ps postgres | grep -q "Up\|healthy"; then
  echo "postgres container is not healthy" >&2
  exit 1
fi

before="$(snapshot)"
echo "before: $before"

backup_output="$("$SCRIPT_DIR/backup.sh")"
printf '%s\n' "$backup_output"
backup_path="$(
  printf '%s\n' "$backup_output" \
    | sed -n 's/^.*backup complete: //p' \
    | tail -n 1
)"
if [ -z "$backup_path" ] || [ ! -d "$backup_path" ]; then
  echo "unable to resolve completed backup directory" >&2
  exit 1
fi

# Stop DB clients so restore does not race application reconnects.
"${COMPOSE[@]}" stop mp-backend hms-api >/dev/null
printf '%s\n' "$MP_DB_NAME" | "$SCRIPT_DIR/restore.sh" "$backup_path"
"${COMPOSE[@]}" up -d --wait >/dev/null

after="$(snapshot)"
echo "after:  $after"
if [ "$before" != "$after" ]; then
  echo "backup/restore row or extension parity failed" >&2
  exit 1
fi

health="$(curl -fsS http://127.0.0.1:${MP_PORT:-8000}/v1/health)"
if ! printf '%s' "$health" | grep -q '"mp":"ok"'; then
  echo "backend did not return to healthy state: $health" >&2
  exit 1
fi

echo "restore verification passed: row parity, pgvector, owner access, and health"
