#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESTORE="$REPO_DIR/scripts/restore.sh"
TESTS_RUN=0

# Detect the current Alembic head revision so this test stays correct as
# migrations are added (mirrors the auto-detect logic in restore.sh).
EXPECTED_REVISION="$(sed -n 's/^revision: str = "\([^"]*\)".*/\1/p' \
  "$REPO_DIR/backend/alembic/versions/0012_webhooks.py" 2>/dev/null || true)"
[ -n "$EXPECTED_REVISION" ] || EXPECTED_REVISION="0012_webhooks"

fail() {
  echo "not ok - $1" >&2
  exit 1
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"
  local message="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    fail "$message"
  fi
}

assert_before() {
  local haystack="$1"
  local first="$2"
  local second="$3"
  local message="$4"
  local prefix
  [[ "$haystack" == *"$first"*"$second"* ]] || fail "$message"
  prefix="${haystack%%"$second"*}"
  [[ "$prefix" == *"$first"* ]] || fail "$message"
}

run_restore() {
  local fixture="$1"
  local manifest_count="${2:-0}"
  local fake_bin="$fixture/bin"
  local backup="$fixture/backup"

  mkdir -p "$fake_bin" "$backup"
  printf 'mp dump\n' > "$backup/memory_passport.dump"
  printf 'hms dump\n' > "$backup/hms.dump"
  printf 'memory_passport\tpublic.memory_records\t%s\n' "$manifest_count" > "$backup/row-counts.tsv"
  printf 'hms\tpublic.demo_hms_memory_units\t0\n' >> "$backup/row-counts.tsv"

  TEST_LOG="$fixture/commands.log" \
    PATH="$fake_bin:/usr/bin:/bin" \
    "$RESTORE" "$backup" <<<"memory_passport" 2>&1
}

test_row_count_mismatch_fails_closed() {
  local fixture output status
  fixture="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-test.XXXXXX")"
  trap 'rm -rf "$fixture"' RETURN
  mkdir -p "$fixture/bin"

  cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  cat > "$fixture/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
  "ps postgres") echo "postgres Up healthy" ;;
  "config --services") printf 'postgres\nhms-api\nmp-backend\n' ;;
esac
case " $* " in
  *"row count mismatch for public.memory_records: expected 999"*) exit 44 ;;
esac
exit 0
EOF
  chmod +x "$fixture/bin/docker" "$fixture/bin/docker-compose"

  set +e
  output="$(run_restore "$fixture" 999)"
  status=$?
  set -e

  [ "$status" -ne 0 ] || fail "row-count mismatch must make restore exit non-zero"
  assert_not_contains "$output" "restore complete" \
    "row-count mismatch must not print restore completion"
  [[ "$output" == *"application writers remain stopped"* ]] || \
    fail "row-count mismatch must leave the restore window locked"
  echo "ok - row-count mismatch fails closed"
  TESTS_RUN=$((TESTS_RUN + 1))
}

test_pg_restore_failure_fails_closed() {
  local fixture output status
  fixture="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-test.XXXXXX")"
  trap 'rm -rf "$fixture"' RETURN
  mkdir -p "$fixture/bin"

  cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  cat > "$fixture/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
if [ "$1" = "ps" ]; then
  echo "postgres Up healthy"
  exit 0
fi
if [ "$1 $2" = "config --services" ]; then
  printf 'postgres\nhms-api\nmp-backend\n'
  exit 0
fi
if [ "$1" = "exec" ]; then
  case " $* " in
    *" pg_restore "*" -d "*) exit 42 ;;
    *) exit 0 ;;
  esac
fi
exit 0
EOF
  chmod +x "$fixture/bin/docker" "$fixture/bin/docker-compose"

  set +e
  output="$(run_restore "$fixture")"
  status=$?
  set -e

  [ "$status" -ne 0 ] || fail "pg_restore failure must make restore exit non-zero"
  assert_not_contains "$output" "restore complete" \
    "pg_restore failure must not print restore completion"
  [[ "$output" == *"application writers remain stopped"* ]] || \
    fail "pg_restore failure must explain the locked recovery state"
  echo "ok - pg_restore failure fails closed"
  TESTS_RUN=$((TESTS_RUN + 1))
}

test_extension_failure_fails_closed_with_recovery_instructions() {
  local fixture output status
  fixture="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-test.XXXXXX")"
  trap 'rm -rf "$fixture"' RETURN
  mkdir -p "$fixture/bin"

  cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  cat > "$fixture/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
  "ps postgres") echo "postgres Up healthy" ;;
  "config --services") printf 'postgres\nhms-api\nmp-backend\n' ;;
esac
case " $* " in
  *" CREATE EXTENSION IF NOT EXISTS vector"*) exit 43 ;;
esac
exit 0
EOF
  chmod +x "$fixture/bin/docker" "$fixture/bin/docker-compose"

  set +e
  output="$(run_restore "$fixture")"
  status=$?
  set -e

  [ "$status" -ne 0 ] || fail "extension failure must make restore exit non-zero"
  assert_not_contains "$output" "restore complete" \
    "extension failure must not print restore completion"
  [[ "$output" == *"restore incomplete"*"rerun this same restore"* ]] || \
    fail "extension failure must include actionable recovery instructions"
  echo "ok - extension failure fails closed with recovery instructions"
  TESTS_RUN=$((TESTS_RUN + 1))
}

test_corrupt_archive_is_rejected_before_database_drop() {
  local fixture output status log
  fixture="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-test.XXXXXX")"
  trap 'rm -rf "$fixture"' RETURN
  mkdir -p "$fixture/bin"

  cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  cat > "$fixture/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
if [ "$1" = "ps" ]; then
  echo "postgres Up healthy"
  exit 0
fi
if [ "$1" = "exec" ]; then
  case " $* " in
    *" pg_restore "*" --list "*) exit 41 ;;
    *) exit 0 ;;
  esac
fi
exit 0
EOF
  chmod +x "$fixture/bin/docker" "$fixture/bin/docker-compose"

  set +e
  output="$(run_restore "$fixture")"
  status=$?
  set -e
  log="$(cat "$fixture/commands.log")"

  [ "$status" -ne 0 ] || fail "corrupt archive must make restore exit non-zero"
  [[ "$log" != *" psql "* ]] || \
    fail "corrupt archive must be rejected before destructive SQL"
  assert_not_contains "$output" "restore complete" \
    "corrupt archive must not print restore completion"
  echo "ok - corrupt archive is rejected before database drop"
  TESTS_RUN=$((TESTS_RUN + 1))
}

test_application_services_stop_before_destructive_sql() {
  local fixture output log
  fixture="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-test.XXXXXX")"
  trap 'rm -rf "$fixture"' RETURN
  mkdir -p "$fixture/bin"

  cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  cat > "$fixture/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
  "ps postgres") echo "postgres Up healthy" ;;
  "config --services") printf 'postgres\nhms-api\nmp-backend\n' ;;
esac
exit 0
EOF
  chmod +x "$fixture/bin/docker" "$fixture/bin/docker-compose"

  output="$(run_restore "$fixture")"
  log="$(cat "$fixture/commands.log")"

  [[ "$output" == *"restore complete"* ]] || fail "successful restore must complete"
  assert_before "$log" "stop hms-api mp-backend" " psql " \
    "application services must stop before destructive SQL"
  echo "ok - application services stop before destructive SQL"
  TESTS_RUN=$((TESTS_RUN + 1))
}

test_extension_is_created_privileged_before_archive_restore() {
  local fixture log
  fixture="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-test.XXXXXX")"
  trap 'rm -rf "$fixture"' RETURN
  mkdir -p "$fixture/bin"

  cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  cat > "$fixture/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
  "ps postgres") echo "postgres Up healthy" ;;
  "config --services") printf 'postgres\nhms-api\nmp-backend\n' ;;
esac
exit 0
EOF
  chmod +x "$fixture/bin/docker" "$fixture/bin/docker-compose"

  run_restore "$fixture" >/dev/null
  log="$(cat "$fixture/commands.log")"

  assert_before "$log" "CREATE EXTENSION IF NOT EXISTS vector" \
    "pg_restore -U postgres -d memory_passport" \
    "privileged vector creation must happen before archive restore"
  [[ "$log" == *"pg_restore -U postgres"*"--exit-on-error"*"--single-transaction"* ]] || \
    fail "archive restore must run atomically and stop on errors"
  [[ "$log" == *"--no-owner --role=mp"*"--use-list="* ]] || \
    fail "MP application objects must restore as the MP owner from a filtered list"
  [[ "$log" == *"--no-owner --role=hms"*"--use-list="* ]] || \
    fail "HMS application objects must restore as the HMS owner from a filtered list"
  echo "ok - extension is created privileged before archive restore"
  TESTS_RUN=$((TESTS_RUN + 1))
}

test_completion_is_gated_on_database_and_health_verification() {
  local fixture log required
  fixture="$(mktemp -d "${TMPDIR:-/tmp}/mp-restore-test.XXXXXX")"
  trap 'rm -rf "$fixture"' RETURN
  mkdir -p "$fixture/bin"

  cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  cat > "$fixture/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
  "ps postgres") echo "postgres Up healthy" ;;
  "config --services") printf 'postgres\nhms-api\nmp-backend\n' ;;
esac
exit 0
EOF
  chmod +x "$fixture/bin/docker" "$fixture/bin/docker-compose"

  run_restore "$fixture" >/dev/null
  log="$(cat "$fixture/commands.log")"

  for required in \
    "extversion" \
    "alembic_version" \
    "$EXPECTED_REVISION" \
    "memory_record_hms_units" \
    "ix_memory_records_tenant_id" \
    "audit_logs" \
    "demo_hms_memory_units" \
    "pg_get_userbyid" \
    "rolsuper" \
    "GRANT CONNECT"; do
    [[ "$log" == *"$required"* ]] || \
      fail "restore verification must check $required"
  done
  [[ "$log" == *"up -d --wait hms-api mp-backend"* ]] || \
    fail "restore must restart configured application services and wait"
  [[ "$log" == *"curl -fsS http://localhost:8000/v1/health"* ]] || \
    fail "restore completion must be gated on MP health"
  echo "ok - completion is gated on database and health verification"
  TESTS_RUN=$((TESTS_RUN + 1))
}

test_pg_restore_failure_fails_closed
test_extension_failure_fails_closed_with_recovery_instructions
test_corrupt_archive_is_rejected_before_database_drop
test_row_count_mismatch_fails_closed
test_application_services_stop_before_destructive_sql
test_extension_is_created_privileged_before_archive_restore
test_completion_is_gated_on_database_and_health_verification
echo "1..$TESTS_RUN"
