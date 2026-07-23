#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP="$REPO_DIR/scripts/backup.sh"
FIXTURE="$(mktemp -d "${TMPDIR:-/tmp}/mp-backup-test.XXXXXX")"

cleanup() {
  local status=$?
  trap - EXIT
  if [[ "$FIXTURE" =~ /mp-backup-test\.[a-zA-Z0-9]+$ ]]; then
    rm -rf -- "$FIXTURE"
  fi
  exit "$status"
}
trap cleanup EXIT

mkdir -p "$FIXTURE/bin" "$FIXTURE/backups"
cat > "$FIXTURE/bin/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
cat > "$FIXTURE/bin/docker-compose" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
  "ps postgres") echo "postgres Up healthy" ;;
  "config --services") printf 'postgres\nhms-api\nmp-backend\n' ;;
esac
case " $* " in
  *" pg_dump "*) printf 'custom archive\n' ;;
  *" pg_restore "*)
    printf 'COPY public.example (id) FROM stdin;\n1\n\\.\n'
    ;;
esac
exit 0
EOF
chmod +x "$FIXTURE/bin/docker" "$FIXTURE/bin/docker-compose"

TEST_LOG="$FIXTURE/commands.log" \
  BACKUP_DIR="$FIXTURE/backups" \
  PATH="$FIXTURE/bin:/usr/bin:/bin" \
  "$BACKUP" >/dev/null

log="$(cat "$FIXTURE/commands.log")"
case "$log" in
  *"stop hms-api mp-backend"*"pg_dump"*"pg_dump"*"up -d --wait hms-api mp-backend"*) ;;
  *)
    echo "not ok - writers must stop before both dumps and restart afterward" >&2
    exit 1
    ;;
esac

manifest="$(find "$FIXTURE/backups" -name row-counts.tsv -type f -print -quit)"
grep -q $'^memory_passport\tpublic.example\t1$' "$manifest"
grep -q $'^hms\tpublic.example\t1$' "$manifest"
echo "ok - backup uses one exclusive MP + HMS snapshot window"
