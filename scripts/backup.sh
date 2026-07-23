#!/usr/bin/env bash
# Memory Passport backup — pg_dump both databases to a timestamped directory.
#
# Backs up:
#   memory_passport  — MP's tenants/apps/users/memories/audit/migrations
#   hms              — the HMS memory engine's data (demo or real mode)
#
# Restore with scripts/restore.sh. Schedule via cron, e.g. nightly at 02:00:
#   0 2 * * *  /path/to/memory-passport/scripts/backup.sh >> /var/log/mp-backup.log 2>&1
#
# Env (all optional, see .env.example for defaults):
#   BACKUP_DIR            destination directory (default: ./backups)
#   POSTGRES_USER         superuser that can read both DBs (default: postgres)
#   POSTGRES_PASSWORD     its password (default: from .env or compose default)
#   MP_DB_NAME            (default: memory_passport)
#   HMS_DB_NAME           (default: hms)
#   COMPOSE               docker compose / docker-compose override
#
# Runs the dump inside the postgres container so no local psql install is
# required. Retention is the operator's responsibility (this script keeps
# every backup; pair with a logrotate-style prune for long-term runs).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

# Match Docker Compose's precedence: explicitly exported caller values must win
# over repository `.env` defaults (important for isolated projects/backups).
ENV_OVERRIDE_NAMES=()
ENV_OVERRIDE_VALUES=()
for name in \
  BACKUP_DIR POSTGRES_USER POSTGRES_PASSWORD MP_DB_NAME HMS_DB_NAME \
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

BACKUP_DIR="${BACKUP_DIR:-$REPO_DIR/backups}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres_dev_password_change_me}"
MP_DB_NAME="${MP_DB_NAME:-memory_passport}"
HMS_DB_NAME="${HMS_DB_NAME:-hms}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=(docker-compose)
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_DIR/$STAMP"
mkdir -p "$DEST"
MANIFEST="$DEST/row-counts.tsv"
: > "$MANIFEST"
echo "==> backing up to $DEST"

# Sanity-check the postgres container is up — we dump through it.
if ! "${COMPOSE[@]}" ps postgres | grep -q "Up\|healthy"; then
  echo "✗ postgres container is not running. Start the stack first: make up" >&2
  exit 1
fi

# MP mappings and HMS units form one logical dataset even though they live in
# separate databases. Stop every configured writer so the two serial pg_dump
# snapshots cannot straddle a cross-service mutation.
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

BACKUP_WINDOW_OPEN=0
restart_after_backup() {
  local status=$?
  trap - EXIT
  if [ "$BACKUP_WINDOW_OPEN" -eq 1 ]; then
    if ! "${COMPOSE[@]}" up -d --wait "${APP_SERVICES[@]}"; then
      echo "✗ backup finished but application services did not recover" >&2
      status=1
    fi
  fi
  exit "$status"
}
trap restart_after_backup EXIT

echo "  → stopping application writers for a consistent MP + HMS snapshot ..."
BACKUP_WINDOW_OPEN=1
"${COMPOSE[@]}" stop "${APP_SERVICES[@]}"

for db in "$MP_DB_NAME" "$HMS_DB_NAME"; do
  echo "  → dumping $db ..."
  # -Fc = custom Postgres format (parallel-restore friendly, compressed).
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_dump -U "$POSTGRES_USER" -d "$db" -Fc \
    > "$DEST/$db.dump"
  if [ ! -s "$DEST/$db.dump" ]; then
    echo "✗ $db dump is empty — aborting (did the DB exist?)" >&2
    exit 2
  fi
  # Derive row counts from the archive itself, not from a later live query.
  # This keeps the manifest on the exact pg_dump snapshot even while the
  # application remains online. COPY escapes embedded newlines, so each data
  # row occupies exactly one output line.
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_restore -U "$POSTGRES_USER" --data-only --file=- \
    < "$DEST/$db.dump" | \
    awk -v database="$db" '
      BEGIN { OFS = "\t" }
      /^COPY / { relation = $2; rows = 0; copying = 1; next }
      copying && $0 == "\\." {
        print database, relation, rows
        copying = 0
        next
      }
      copying { rows++ }
    ' >> "$MANIFEST"
  if ! grep -q "^${db}$(printf '\t')" "$MANIFEST"; then
    echo "✗ could not derive row counts from $db.dump" >&2
    exit 2
  fi
  echo "    ✓ $(du -h "$DEST/$db.dump" | cut -f1)"
done

LC_ALL=C sort -o "$MANIFEST" "$MANIFEST"

"${COMPOSE[@]}" up -d --wait "${APP_SERVICES[@]}"
BACKUP_WINDOW_OPEN=0
trap - EXIT

echo "✓ backup complete: $DEST"
echo "  restore with: scripts/restore.sh $STAMP"
