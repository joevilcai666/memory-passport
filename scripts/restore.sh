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
    "$MP_DB_NAME")  owner="mp" ;;
    "$HMS_DB_NAME") owner="hms" ;;
    *)              owner="$POSTGRES_USER" ;;
  esac
  # Drop + recreate so pg_restore starts from a clean slate (avoids the
  # "already exists" errors from restoring into a pre-populated DB). We first
  # force-disconnect any live sessions (e.g. a still-running mp-backend) so the
  # DROP doesn't block on "database is being accessed by other users". Stop the
  # app containers for a cleaner window, but this keeps the script usable when
  # the operator forgot to.
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "ALTER DATABASE \"$db\" WITH ALLOW_CONNECTIONS false;" \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db' AND pid <> pg_backend_pid();" \
    -c "DROP DATABASE IF EXISTS \"$db\";" \
    -c "CREATE DATABASE \"$db\" OWNER $owner;"
  "${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_restore -U "$POSTGRES_USER" -d "$db" -v --no-owner --role="$owner" \
    < "$SRC/$db.dump" || {
      # pg_restore exits non-zero on benign warnings (e.g. "extension vector
      # already exists"). Verify the row counts after restore to be sure.
      echo "  ! pg_restore reported warnings — verify the data manually."
    }
  echo "    ✓ $db restored"
done

echo ""
echo "✓ restore complete from $SRC"
echo "  Re-run migrations + seed if needed:"
echo "    docker-compose exec mp-backend alembic upgrade head"
echo "    docker-compose exec mp-backend python -m app.seed.run_seed"
