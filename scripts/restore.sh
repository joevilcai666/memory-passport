#!/usr/bin/env bash
# Memory Passport restore — replay a scripts/backup.sh snapshot.
#
# Usage:
#   scripts/restore.sh <stamp>      # restores ./backups/<stamp>
#   scripts/restore.sh ./path/to/dir
#
# DESTRUCTIVE: drops and recreates both databases (memory_passport + hms), so
# any data created after the backup is lost. The MP + HMS services should be
# stopped (or at least idle) during restore to avoid mid-write races.
#
# Runs pg_restore inside the postgres container — no local psql install needed.
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <backup-stamp-or-path>" >&2
  echo "Examples:" >&2
  echo "  $0 20260721T020000Z" >&2
  echo "  $0 ./backups/20260721T020000Z" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

# shellcheck disable=SC1091
[ -f .env ] && set -a && . ./.env && set +a

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres_dev_password_change_me}"
MP_DB_NAME="${MP_DB_NAME:-memory_passport}"
HMS_DB_NAME="${HMS_DB_NAME:-hms}"
MP_DB_PASSWORD="${MP_DB_PASSWORD:-mp_dev_password_change_me}"
HMS_DB_PASSWORD="${HMS_DB_PASSWORD:-hms_dev_password_change_me}"

ARG="$1"
if [ -d "$ARG" ]; then
  SRC="$ARG"
elif [ -d "$REPO_DIR/backups/$ARG" ]; then
  SRC="$REPO_DIR/backups/$ARG"
else
  echo "✗ backup directory not found: $ARG" >&2
  echo "  looked for: $ARG and $REPO_DIR/backups/$ARG" >&2
  exit 1
fi

# Verify both dump files exist before touching anything.
for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  if [ ! -f "$SRC/$db.dump" ]; then
    echo "✗ missing $SRC/$db.dump — backup is incomplete" >&2
    exit 1
  fi
done

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=(docker-compose)
fi

LOCAL_LISTS=()
CONTAINER_LISTS=()
cleanup() {
  local path
  for path in "${LOCAL_LISTS[@]}"; do
    rm -f -- "$path"
  done
  for path in "${CONTAINER_LISTS[@]}"; do
    MSYS_NO_PATHCONV=1 "${COMPOSE[@]}" exec -T postgres \
      rm -f -- "$path" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT

if ! "${COMPOSE[@]}" ps postgres | grep -q "Up\|healthy"; then
  echo "✗ postgres container is not running. Start the stack first: make up" >&2
  exit 1
fi

echo "⚠  DESTRUCTIVE restore from: $SRC"
echo "    This will DROP and recreate: $MP_DB_NAME, $HMS_DB_NAME"
printf "    Type the database name to confirm (%s): " "$MP_DB_NAME"
read -r CONFIRM
if [ "$CONFIRM" != "$MP_DB_NAME" ]; then
  echo "✗ aborted (confirmation did not match)" >&2
  exit 1
fi

for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  echo "  → restoring $db ..."
  # The owner is whatever docker/postgres-init.sh set up (mp for memory_passport,
  # hms for hms). Recreate with the matching role so permissions stay correct.
  case "$db" in
    "$MP_DB_NAME")
      owner="mp"
      owner_password="$MP_DB_PASSWORD"
      expected_relation="public.memory_records"
      ;;
    "$HMS_DB_NAME")
      owner="hms"
      owner_password="$HMS_DB_PASSWORD"
      expected_relation=""
      ;;
    *)
      owner="$POSTGRES_USER"
      owner_password="$POSTGRES_PASSWORD"
      expected_relation=""
      ;;
  esac

  # Build a restore list before touching the database. pgvector must be
  # created by the Postgres administrator, while the remaining objects should
  # be restored as the database owner. Exclude only vector's CREATE/COMMENT
  # archive entries; every application object remains in the list.
  local_list="$(mktemp "${TMPDIR:-/tmp}/mp-restore-${db}.XXXXXX.list")"
  container_list="/tmp/mp-restore-${db}-$$.list"
  LOCAL_LISTS+=("$local_list")
  CONTAINER_LISTS+=("$container_list")
  "${COMPOSE[@]}" exec -T postgres pg_restore -l < "$SRC/$db.dump" \
    | grep -Ev ' EXTENSION - vector[[:space:]]*$| COMMENT - EXTENSION vector[[:space:]]*$' \
    > "$local_list"
  if grep -Eq ' EXTENSION - vector[[:space:]]*$| COMMENT - EXTENSION vector[[:space:]]*$' "$local_list"; then
    echo "  ✗ failed to filter pgvector archive entries for $db" >&2
    exit 1
  fi
  MSYS_NO_PATHCONV=1 "${COMPOSE[@]}" exec -T postgres tee "$container_list" \
    < "$local_list" >/dev/null

  # Drop + recreate so pg_restore starts from a clean slate (avoids the
  # "already exists" errors from restoring into a pre-populated DB). We first
  # force-disconnect any live sessions (e.g. a still-running mp-backend) so the
  # DROP doesn't block on "database is being accessed by other users". Stop the
  # app containers for a cleaner window, but this keeps the script usable when
  # the operator forgot to.
  MSYS_NO_PATHCONV=1 "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "ALTER DATABASE \"$db\" WITH ALLOW_CONNECTIONS false;" \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db' AND pid <> pg_backend_pid();" \
    -c "DROP DATABASE IF EXISTS \"$db\";" \
    -c "CREATE DATABASE \"$db\" OWNER $owner;"

  # Extensions require administrator privileges. Pre-create vector before
  # switching to the application owner for all archive objects.
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d "$db" -v ON_ERROR_STOP=1 \
    -c "CREATE EXTENSION IF NOT EXISTS vector;"

  MSYS_NO_PATHCONV=1 "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_restore -U "$POSTGRES_USER" -d "$db" -v --exit-on-error \
    --no-owner --role="$owner" --use-list="$container_list" \
    < "$SRC/$db.dump"

  vector_ok="$(
    "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
      psql -U "$POSTGRES_USER" -d "$db" -Atqc \
      "SELECT count(*) FROM pg_extension WHERE extname = 'vector';" \
      | tr -d '\r'
  )"
  if [ "$vector_ok" != "1" ]; then
    echo "  ✗ pgvector verification failed for $db" >&2
    exit 1
  fi

  table_count="$(
    "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
      psql -U "$POSTGRES_USER" -d "$db" -Atqc \
      "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema');" \
      | tr -d '\r'
  )"
  if ! [[ "$table_count" =~ ^[1-9][0-9]*$ ]]; then
    echo "  ✗ no application tables restored for $db" >&2
    exit 1
  fi

  if [ -n "$expected_relation" ]; then
    relation_ok="$(
      "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
        psql -U "$POSTGRES_USER" -d "$db" -Atqc \
        "SELECT CASE WHEN to_regclass('$expected_relation') IS NULL THEN 0 ELSE 1 END;" \
        | tr -d '\r'
    )"
    if [ "$relation_ok" != "1" ]; then
      echo "  ✗ expected relation $expected_relation is missing in $db" >&2
      exit 1
    fi
  fi

  owner_access="$(
    "${COMPOSE[@]}" exec -T -e PGPASSWORD="$owner_password" postgres \
      psql -U "$owner" -d "$db" -Atqc \
      "SELECT CASE WHEN count(*) > 0 AND bool_and(has_table_privilege(current_user, format('%I.%I', schemaname, tablename), 'SELECT')) THEN 1 ELSE 0 END FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema');" \
      | tr -d '\r'
  )"
  if [ "$owner_access" != "1" ]; then
    echo "  ✗ owner role $owner cannot read every restored table in $db" >&2
    exit 1
  fi

  echo "    ✓ $db restored"
done

echo ""
echo "✓ restore complete from $SRC"
echo "  Re-run migrations + seed if needed:"
echo "    docker-compose exec mp-backend alembic upgrade head"
echo "    docker-compose exec mp-backend python -m app.seed.run_seed"
