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
#
# Role passwords are sourced from MP_DB_PASSWORD / HMS_DB_PASSWORD (the same
# variables docker-compose.yml feeds into the backend / HMS containers), so a
# single .env override now flows end-to-end. The defaults below match
# .env.example so `make demo` still works out of the box.
set -euo pipefail

PSQL=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER")

# -- Memory Passport ----------------------------------------------------------
# CREATEDB so the test suite can spin up throwaway databases
# (test_seed / test_smoke / test_migrations each create+drop a DB).
MP_DB_PASSWORD="${MP_DB_PASSWORD:?MP_DB_PASSWORD must be set (see .env.example)}"
"${PSQL[@]}" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mp') THEN
    CREATE ROLE mp LOGIN PASSWORD '${MP_DB_PASSWORD}' CREATEDB;
  END IF;
END\$\$;
SQL

if ! "${PSQL[@]}" -tAc "SELECT 1 FROM pg_database WHERE datname='memory_passport'" | grep -q 1; then
  "${PSQL[@]}" -c "CREATE DATABASE memory_passport OWNER mp"
fi
# pgvector lives in the shared server; ensure the extension is available in MP's DB.
"${PSQL[@]}" -d memory_passport -c "CREATE EXTENSION IF NOT EXISTS vector"

# -- HMS ----------------------------------------------------------------------
HMS_DB_PASSWORD="${HMS_DB_PASSWORD:?HMS_DB_PASSWORD must be set (see .env.example)}"
"${PSQL[@]}" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms') THEN
    CREATE ROLE hms LOGIN PASSWORD '${HMS_DB_PASSWORD}';
  END IF;
END\$\$;
SQL

if ! "${PSQL[@]}" -tAc "SELECT 1 FROM pg_database WHERE datname='hms'" | grep -q 1; then
  "${PSQL[@]}" -c "CREATE DATABASE hms OWNER hms"
fi
"${PSQL[@]}" -d hms -c "CREATE EXTENSION IF NOT EXISTS vector"

echo "postgres-init: databases memory_passport (mp) and hms (hms) ready."
