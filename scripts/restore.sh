#!/usr/bin/env bash
# Memory Passport restore — replay a scripts/backup.sh snapshot.
#
# Usage:
#   scripts/restore.sh <stamp>      # restores ./backups/<stamp>
#   scripts/restore.sh ./path/to/dir
#
# DESTRUCTIVE: drops and recreates both databases (memory_passport + hms), so
# any data created after the backup is lost. The script stops the configured
# MP + HMS application services and keeps service-role connections locked until
# every database and health verification passes.
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

# Match Docker Compose's precedence: explicitly exported caller values must win
# over repository `.env` defaults (important for isolated ports/projects).
ENV_OVERRIDE_NAMES=()
ENV_OVERRIDE_VALUES=()
for name in \
  POSTGRES_USER POSTGRES_PASSWORD MP_DB_NAME HMS_DB_NAME MP_DB_USER HMS_DB_USER \
  COMPOSE_FILE COMPOSE_PROJECT_NAME MP_PORT HMS_LOCAL_API_PORT; do
  if declare -p "$name" >/dev/null 2>&1; then
    ENV_OVERRIDE_NAMES+=("$name")
    ENV_OVERRIDE_VALUES+=("${!name}")
  fi
done
# shellcheck disable=SC1091
[ -f .env ] && set -a && . ./.env && set +a
for ((i = 0; i < ${#ENV_OVERRIDE_NAMES[@]}; i++)); do
  printf -v "${ENV_OVERRIDE_NAMES[$i]}" '%s' "${ENV_OVERRIDE_VALUES[$i]}"
  export "${ENV_OVERRIDE_NAMES[$i]}"
done
unset ENV_OVERRIDE_NAMES ENV_OVERRIDE_VALUES name i

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres_dev_password_change_me}"
MP_DB_NAME="${MP_DB_NAME:-memory_passport}"
HMS_DB_NAME="${HMS_DB_NAME:-hms}"
MP_DB_USER="${MP_DB_USER:-mp}"
HMS_DB_USER="${HMS_DB_USER:-hms}"

for identifier in \
  "$POSTGRES_USER" "$MP_DB_NAME" "$HMS_DB_NAME" "$MP_DB_USER" "$HMS_DB_USER"; do
  if [[ ! "$identifier" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "✗ unsafe PostgreSQL identifier in restore configuration: $identifier" >&2
    exit 1
  fi
done

if [ -z "${EXPECTED_ALEMBIC_REVISION:-}" ]; then
  ALEMBIC_HEAD_FILE="$(find "$REPO_DIR/backend/alembic/versions" \
    -type f -name '*.py' | sort | tail -n 1)"
  EXPECTED_ALEMBIC_REVISION="$(sed -nE \
    's/^revision(:[^=]+)?= *"([^"]+)".*/\2/p' "$ALEMBIC_HEAD_FILE")"
fi
if [[ ! "$EXPECTED_ALEMBIC_REVISION" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "✗ could not determine the expected Alembic revision" >&2
  exit 1
fi

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

MANIFEST="$SRC/row-counts.tsv"
if [ ! -s "$MANIFEST" ]; then
  echo "✗ missing $MANIFEST — backup has no verifiable data manifest" >&2
  exit 1
fi

MP_COUNT_ASSERTIONS=""
HMS_COUNT_ASSERTIONS=""
MP_MANIFEST_ROWS=0
HMS_MANIFEST_ROWS=0
while IFS=$'\t' read -r manifest_db relation expected_rows extra; do
  if [ -n "${extra:-}" ] ||
     [[ ! "$relation" =~ ^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$ ]] ||
     [[ ! "$expected_rows" =~ ^[0-9]+$ ]]; then
    echo "✗ invalid row-count manifest entry: $manifest_db $relation $expected_rows" >&2
    exit 1
  fi
  schema="${relation%%.*}"
  table="${relation#*.}"
  assertion="
    IF (SELECT count(*) FROM \"$schema\".\"$table\") <> $expected_rows THEN
      RAISE EXCEPTION 'row count mismatch for $relation: expected $expected_rows';
    END IF;"
  case "$manifest_db" in
    "$MP_DB_NAME")
      MP_COUNT_ASSERTIONS+="$assertion"
      MP_MANIFEST_ROWS=$((MP_MANIFEST_ROWS + 1))
      ;;
    "$HMS_DB_NAME")
      HMS_COUNT_ASSERTIONS+="$assertion"
      HMS_MANIFEST_ROWS=$((HMS_MANIFEST_ROWS + 1))
      ;;
    *)
      echo "✗ row-count manifest names unexpected database: $manifest_db" >&2
      exit 1
      ;;
  esac
done < "$MANIFEST"
if [ "$MP_MANIFEST_ROWS" -eq 0 ] || [ "$HMS_MANIFEST_ROWS" -eq 0 ]; then
  echo "✗ row-count manifest must cover both restored databases" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=(docker-compose)
fi

LOCAL_LISTS=()
CONTAINER_LISTS=()
RESTORE_WINDOW_OPEN=0
RESTORE_COMPLETE=0

cleanup_restore_lists() {
  local path
  for path in "${LOCAL_LISTS[@]}"; do
    rm -f -- "$path"
  done
  for path in "${CONTAINER_LISTS[@]}"; do
    MSYS_NO_PATHCONV=1 "${COMPOSE[@]}" exec -T postgres \
      rm -f -- "$path" >/dev/null 2>&1 || true
  done
}

recover_failed_restore() {
  local status=$?
  trap - EXIT
  cleanup_restore_lists
  if [ "$RESTORE_WINDOW_OPEN" -eq 1 ] && [ "$RESTORE_COMPLETE" -ne 1 ]; then
    set +e
    "${COMPOSE[@]}" stop "${APP_SERVICES[@]}" >/dev/null 2>&1
    lock_database_connections "$MP_DB_NAME" "$MP_DB_USER" >/dev/null 2>&1
    lock_database_connections "$HMS_DB_NAME" "$HMS_DB_USER" >/dev/null 2>&1
    set -e
    echo "" >&2
    echo "✗ restore incomplete; application writers remain stopped and service-role database connections are locked." >&2
    echo "  Recovery: fix the reported error and rerun this same restore." >&2
    echo "  Do not restart services or grant CONNECT until every verification passes." >&2
  fi
  exit "$status"
}
trap recover_failed_restore EXIT

if ! "${COMPOSE[@]}" ps postgres | grep -q "Up\|healthy"; then
  echo "✗ postgres container is not running. Start the stack first: make up" >&2
  exit 1
fi

# Validate every custom-format archive before asking for confirmation or
# touching a live database. pg_restore --list parses the complete TOC and
# exits non-zero for corrupt or unsupported input.
for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  if ! "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_restore -U "$POSTGRES_USER" --list < "$SRC/$db.dump" >/dev/null; then
    echo "✗ cannot read $SRC/$db.dump — backup is corrupt or incompatible" >&2
    exit 2
  fi
done

# Build both filtered restore lists before confirmation or any destructive SQL.
# pgvector is a cluster capability and must be created by the administrator;
# every application-owned archive entry remains in the list.
for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  local_list="$(mktemp "${TMPDIR:-/tmp}/mp-restore-${db}.XXXXXX.list")"
  container_list="/tmp/mp-restore-${db}-$$.list"
  LOCAL_LISTS+=("$local_list")
  CONTAINER_LISTS+=("$container_list")
  "${COMPOSE[@]}" exec -T postgres pg_restore -l < "$SRC/$db.dump" \
    | awk '!/ EXTENSION - vector[[:space:]]*$/ && !/ COMMENT - EXTENSION vector[[:space:]]*$/' \
    > "$local_list"
  if grep -Eq ' EXTENSION - vector[[:space:]]*$| COMMENT - EXTENSION vector[[:space:]]*$' "$local_list"; then
    echo "✗ failed to filter pgvector archive entries for $db" >&2
    exit 1
  fi
  MSYS_NO_PATHCONV=1 "${COMPOSE[@]}" exec -T postgres tee "$container_list" \
    < "$local_list" >/dev/null
  case "$db" in
    "$MP_DB_NAME") MP_CONTAINER_LIST="$container_list" ;;
    "$HMS_DB_NAME") HMS_CONTAINER_LIST="$container_list" ;;
  esac
done

echo "⚠  DESTRUCTIVE restore from: $SRC"
echo "    This will DROP and recreate: $MP_DB_NAME, $HMS_DB_NAME"
printf "    Type the database name to confirm (%s): " "$MP_DB_NAME"
read -r CONFIRM
if [ "$CONFIRM" != "$MP_DB_NAME" ]; then
  echo "✗ aborted (confirmation did not match)" >&2
  exit 1
fi

# Stop every configured writer before disabling connections or dropping a
# database. Filtering `config --services` keeps the default evaluator and the
# real-HMS overlay compatible without naming services that are not present.
APP_SERVICES=()
while IFS= read -r service; do
  case "$service" in
    mp-backend|hms-api|hms-worker) APP_SERVICES+=("$service") ;;
  esac
done < <("${COMPOSE[@]}" config --services)
if [ "${#APP_SERVICES[@]}" -eq 0 ]; then
  echo "✗ no application services found in the Compose configuration" >&2
  exit 1
fi

lock_database_connections() {
  local db="$1"
  local owner="$2"
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "REVOKE CONNECT ON DATABASE \"$db\" FROM PUBLIC;" \
    -c "REVOKE CONNECT ON DATABASE \"$db\" FROM \"$owner\";"
}

echo "  → stopping application services for an exclusive restore window ..."
RESTORE_WINDOW_OPEN=1
"${COMPOSE[@]}" stop "${APP_SERVICES[@]}"

for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  echo "  → restoring $db ..."
  # The owner is whatever docker/postgres-init.sh set up (mp for memory_passport,
  # hms for hms). Recreate with the matching role so permissions stay correct.
  case "$db" in
    "$MP_DB_NAME")
      owner="$MP_DB_USER"
      container_list="$MP_CONTAINER_LIST"
      ;;
    "$HMS_DB_NAME")
      owner="$HMS_DB_USER"
      container_list="$HMS_CONTAINER_LIST"
      ;;
    *)
      owner="$POSTGRES_USER"
      echo "✗ unexpected database selected for restore: $db" >&2
      exit 1
      ;;
  esac

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
    -c "CREATE DATABASE \"$db\" OWNER \"$owner\";"

  # Keep normal service roles out even if an operator manually starts a
  # container during this window. The privileged restore role retains access.
  lock_database_connections "$db" "$owner"

  # Extensions are cluster capabilities, not application-owned schema. Create
  # pgvector as the privileged backup role before replaying dependent objects.
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d "$db" -v ON_ERROR_STOP=1 \
    -c "CREATE EXTENSION IF NOT EXISTS vector;"

  # Restore application objects as the database owner. The filtered list keeps
  # vector administrator-owned, and the transaction prevents partial schemas.
  MSYS_NO_PATHCONV=1 "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_restore -U "$POSTGRES_USER" -d "$db" -v --exit-on-error \
    --single-transaction --no-owner --role="$owner" \
    --use-list="$container_list" \
    < "$SRC/$db.dump"
  echo "    ✓ $db restored"
done

echo "  → comparing every restored table with the archive row-count manifest ..."
for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  case "$db" in
    "$MP_DB_NAME") count_assertions="$MP_COUNT_ASSERTIONS" ;;
    "$HMS_DB_NAME") count_assertions="$HMS_COUNT_ASSERTIONS" ;;
  esac
  COUNT_VERIFY_SQL="DO \$verify\$ BEGIN $count_assertions END \$verify\$;"
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d "$db" -v ON_ERROR_STOP=1 \
    -c "$COUNT_VERIFY_SQL"
done

echo "  → verifying Memory Passport schema, data, and ownership ..."
read -r -d '' MP_VERIFY_SQL <<SQL || true
DO \$verify\$
DECLARE
  actual_revision text;
  bad_owner text;
  required_name text;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_extension
    WHERE extname = 'vector'
      AND NULLIF(extversion, '') IS NOT NULL
      AND pg_get_userbyid(extowner) = '$POSTGRES_USER'
  ) THEN
    RAISE EXCEPTION 'vector extension missing, versionless, or not owned by $POSTGRES_USER';
  END IF;

  IF (SELECT count(*) FROM alembic_version) <> 1 THEN
    RAISE EXCEPTION 'Alembic version table must contain exactly one row';
  END IF;
  SELECT version_num INTO actual_revision FROM alembic_version;
  IF actual_revision IS DISTINCT FROM '$EXPECTED_ALEMBIC_REVISION' THEN
    RAISE EXCEPTION 'Alembic revision mismatch: expected %, restored %',
      '$EXPECTED_ALEMBIC_REVISION', actual_revision;
  END IF;

  FOREACH required_name IN ARRAY ARRAY[
    'tenants', 'memory_records', 'memory_record_hms_units',
    'retrieval_traces', 'audit_logs', 'team_members', 'team_invites'
  ] LOOP
    IF to_regclass('public.' || required_name) IS NULL THEN
      RAISE EXCEPTION 'required MP table missing: %', required_name;
    END IF;
  END LOOP;
  FOREACH required_name IN ARRAY ARRAY[
    'ix_memory_records_tenant_id',
    'ix_memory_record_hms_units_hms_unit_id',
    'ix_audit_logs_tenant_action',
    'ix_team_members_tenant_id', 'ix_team_members_tenant_role',
    'ix_team_invites_tenant_id', 'ix_team_invites_expires_at',
    'ix_team_invites_tenant_email'
  ] LOOP
    IF to_regclass('public.' || required_name) IS NULL THEN
      RAISE EXCEPTION 'required MP index missing: %', required_name;
    END IF;
  END LOOP;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'retrieval_traces'
      AND column_name = 'feedback'
  ) THEN
    RAISE EXCEPTION 'required retrieval_traces.feedback column missing';
  END IF;

  IF (SELECT pg_get_userbyid(datdba) FROM pg_database
      WHERE datname = '$MP_DB_NAME') IS DISTINCT FROM '$MP_DB_USER' THEN
    RAISE EXCEPTION 'database $MP_DB_NAME is not owned by $MP_DB_USER';
  END IF;
  IF (SELECT rolsuper FROM pg_roles WHERE rolname = '$MP_DB_USER') IS DISTINCT FROM false THEN
    RAISE EXCEPTION 'service role $MP_DB_USER must exist and must not be superuser';
  END IF;
  SELECT c.relname INTO bad_owner
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relkind IN ('r', 'p', 'S', 'v', 'm')
    AND pg_get_userbyid(c.relowner) <> '$MP_DB_USER'
  LIMIT 1;
  IF bad_owner IS NOT NULL THEN
    RAISE EXCEPTION 'MP relation % is not owned by $MP_DB_USER', bad_owner;
  END IF;
  IF NOT has_table_privilege(
    '$MP_DB_USER', 'public.memory_records', 'SELECT,INSERT,UPDATE,DELETE'
  ) THEN
    RAISE EXCEPTION 'service role $MP_DB_USER cannot use memory_records';
  END IF;

  RAISE NOTICE 'MP row counts: memory_records=%, mappings=%, audit_logs=%',
    (SELECT count(*) FROM memory_records),
    (SELECT count(*) FROM memory_record_hms_units),
    (SELECT count(*) FROM audit_logs);
END
\$verify\$;
SQL
"${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
  psql -U "$POSTGRES_USER" -d "$MP_DB_NAME" -v ON_ERROR_STOP=1 \
  -c "$MP_VERIFY_SQL"

echo "  → verifying HMS schema, data, and ownership ..."
read -r -d '' HMS_VERIFY_SQL <<SQL || true
DO \$verify\$
DECLARE
  bad_owner text;
  hms_schema text;
  memory_count bigint;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_extension
    WHERE extname = 'vector'
      AND NULLIF(extversion, '') IS NOT NULL
      AND pg_get_userbyid(extowner) = '$POSTGRES_USER'
  ) THEN
    RAISE EXCEPTION 'vector extension missing, versionless, or not owned by $POSTGRES_USER';
  END IF;
  IF (SELECT pg_get_userbyid(datdba) FROM pg_database
      WHERE datname = '$HMS_DB_NAME') IS DISTINCT FROM '$HMS_DB_USER' THEN
    RAISE EXCEPTION 'database $HMS_DB_NAME is not owned by $HMS_DB_USER';
  END IF;
  IF (SELECT rolsuper FROM pg_roles WHERE rolname = '$HMS_DB_USER') IS DISTINCT FROM false THEN
    RAISE EXCEPTION 'service role $HMS_DB_USER must exist and must not be superuser';
  END IF;

  IF to_regclass('public.demo_hms_banks') IS NOT NULL THEN
    IF to_regclass('public.demo_hms_memory_units') IS NULL OR
       to_regclass('public.ix_demo_hms_memory_units_bank_id') IS NULL OR
       to_regclass('public.ix_demo_hms_memory_units_document_id') IS NULL THEN
      RAISE EXCEPTION 'required demo HMS tables or indexes are missing';
    END IF;
    IF NOT has_table_privilege(
      '$HMS_DB_USER', 'public.demo_hms_memory_units',
      'SELECT,INSERT,UPDATE,DELETE'
    ) THEN
      RAISE EXCEPTION 'service role $HMS_DB_USER cannot use demo HMS data';
    END IF;
    RAISE NOTICE 'HMS row counts: banks=%, memory_units=%',
      (SELECT count(*) FROM demo_hms_banks),
      (SELECT count(*) FROM demo_hms_memory_units);
  ELSE
    SELECT n.nspname INTO hms_schema
    FROM pg_class banks
    JOIN pg_namespace n ON n.oid = banks.relnamespace
    WHERE banks.relname = 'banks'
      AND banks.relkind IN ('r', 'p')
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND EXISTS (
        SELECT 1 FROM pg_class units
        WHERE units.relnamespace = n.oid
          AND units.relname = 'memory_units'
          AND units.relkind IN ('r', 'p')
      )
    ORDER BY n.nspname
    LIMIT 1;
    IF hms_schema IS NULL THEN
      RAISE EXCEPTION 'required real HMS banks/memory_units tables are missing';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM pg_class idx
      JOIN pg_namespace n ON n.oid = idx.relnamespace
      WHERE n.nspname = hms_schema
        AND idx.relname = 'idx_memory_units_bank_id'
        AND idx.relkind = 'i'
    ) THEN
      RAISE EXCEPTION 'required real HMS memory_units index is missing in schema %', hms_schema;
    END IF;
    IF NOT has_table_privilege(
      '$HMS_DB_USER', format('%I.memory_units', hms_schema),
      'SELECT,INSERT,UPDATE,DELETE'
    ) THEN
      RAISE EXCEPTION 'service role $HMS_DB_USER cannot use %.memory_units', hms_schema;
    END IF;
    EXECUTE format('SELECT count(*) FROM %I.memory_units', hms_schema)
      INTO memory_count;
    RAISE NOTICE 'HMS row counts: schema=%, memory_units=%', hms_schema, memory_count;
  END IF;

  SELECT n.nspname || '.' || c.relname INTO bad_owner
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
    AND n.nspname !~ '^pg_toast'
    AND c.relkind IN ('r', 'p', 'S', 'v', 'm')
    AND pg_get_userbyid(c.relowner) <> '$HMS_DB_USER'
  LIMIT 1;
  IF bad_owner IS NOT NULL THEN
    RAISE EXCEPTION 'HMS relation % is not owned by $HMS_DB_USER', bad_owner;
  END IF;
END
\$verify\$;
SQL
"${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
  psql -U "$POSTGRES_USER" -d "$HMS_DB_NAME" -v ON_ERROR_STOP=1 \
  -c "$HMS_VERIFY_SQL"

echo "  → reopening service-role connections and checking application health ..."
for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  case "$db" in
    "$MP_DB_NAME") owner="$MP_DB_USER" ;;
    "$HMS_DB_NAME") owner="$HMS_DB_USER" ;;
  esac
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "GRANT CONNECT ON DATABASE \"$db\" TO \"$owner\";"
done
"${COMPOSE[@]}" up -d --wait "${APP_SERVICES[@]}"
"${COMPOSE[@]}" exec -T mp-backend \
  curl -fsS http://localhost:8000/v1/health >/dev/null

RESTORE_COMPLETE=1
RESTORE_WINDOW_OPEN=0
echo ""
echo "✓ restore complete and verified from $SRC"
