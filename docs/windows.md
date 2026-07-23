# Windows evaluation

The recommended Windows environment is Docker Desktop with its WSL2 backend
and an Ubuntu WSL2 shell. Clone the repository inside the WSL filesystem (for
example, under `~/src`, not `/mnt/c`) and run the standard customer path:

```bash
git clone --recursive https://github.com/joevilcai666/memory-passport.git
cd memory-passport
make demo
```

This is the recommended Windows path for `make`, the executable demo, and the
Bash examples in the evaluation guides. Docker Desktop must have WSL
integration enabled for the chosen distribution. The repository mechanically
verifies LF checkout behavior with `core.autocrlf=true`; customer sign-off still
requires these commands to pass on a real Windows/WSL2 host.

## Native PowerShell

Native PowerShell has an equivalent documented path for bringing up and
verifying the default Compose stack, but still requires real-Windows acceptance
before release. It does not run `make demo` or `scripts/demo.sh`, which are
POSIX-shell interfaces. Make, WSL, Python, and a host Bash installation are not
required for this Compose-only path:

```powershell
git clone --recursive https://github.com/joevilcai666/memory-passport.git
Set-Location memory-passport
docker compose up -d --wait --remove-orphans
docker compose exec -T mp-backend alembic upgrade head
docker compose exec -T mp-backend python -m app.seed.run_seed
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/v1/health
```

The three services `postgres`, `hms-api`, and `mp-backend` should be running
and healthy. The health response must report `mp`, `hms`, and `db` as `ok` and
`memory_engine` as `demo`.

On a fresh Compose volume, the PostgreSQL entrypoint also creates both
application roles and databases. Verify them from PowerShell with:

```powershell
docker compose exec -T postgres psql -U postgres -d postgres -tAc "SELECT rolname FROM pg_roles WHERE rolname IN ('mp','hms') ORDER BY 1;"
docker compose exec -T postgres psql -U postgres -d postgres -tAc "SELECT datname FROM pg_database WHERE datname IN ('memory_passport','hms') ORDER BY 1;"
```

The first command prints `hms` and `mp`; the second prints `hms` and
`memory_passport`.

## Line endings and executable modes

The committed `.gitattributes` file forces LF for repository text, including
shell scripts and Docker entrypoints, even when global `core.autocrlf=true`.
Do not add repository-local Git configuration or manually convert files after
cloning.

Git records the protected shell scripts as executable (`100755`). A native
Windows worktree does not expose POSIX executable bits in the same way as a
Linux filesystem; the PowerShell path therefore executes those scripts only
inside Linux containers. A clone inside WSL preserves the normal Linux host
behavior needed by `make demo`.

Maintainers can validate both the LF attributes and stored executable modes
with:

```bash
python3 scripts/check_line_endings.py
```
