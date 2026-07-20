#!/usr/bin/env bash
# Postgres init script — runs once on a fresh data volume.
# Mount at /docker-entrypoint-initdb.d/ (the official postgres image runs *.sh
# alphabetically on first init). Provisions two roles + two databases on the
# single shared pgvector instance:
#   - mp   / memory_passport   Memory Passport FastAPI backend (this repo)
#   - hms  / hms               Holographic Memory System (vendor/hms)
#
# Both roles get full privileges on their own DB only, so MP and HMS are
# isolated at the database level while still sharing one server.
set -euo pipefail

PSQL=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER")

# -- Memory Passport ----------------------------------------------------------
"${PSQL[@]}" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mp') THEN
    -- CREATEDB so the test suite can spin up throwaway databases
    -- (test_seed / test_smoke / test_migrations each create+drop a DB).
    CREATE ROLE mp LOGIN PASSWORD 'mp_dev_password_change_me' CREATEDB;
  END IF;
END$$;
SQL

if ! "${PSQL[@]}" -tAc "SELECT 1 FROM pg_database WHERE datname='memory_passport'" | grep -q 1; then
  "${PSQL[@]}" -c "CREATE DATABASE memory_passport OWNER mp"
fi
# pgvector lives in the shared server; ensure the extension is available in MP's DB.
"${PSQL[@]}" -d memory_passport -c "CREATE EXTENSION IF NOT EXISTS vector"

# -- HMS ----------------------------------------------------------------------
"${PSQL[@]}" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms') THEN
    CREATE ROLE hms LOGIN PASSWORD 'hms_dev_password_change_me';
  END IF;
END$$;
SQL

if ! "${PSQL[@]}" -tAc "SELECT 1 FROM pg_database WHERE datname='hms'" | grep -q 1; then
  "${PSQL[@]}" -c "CREATE DATABASE hms OWNER hms"
fi
"${PSQL[@]}" -d hms -c "CREATE EXTENSION IF NOT EXISTS vector"

echo "postgres-init: databases memory_passport (mp) and hms (hms) ready."
