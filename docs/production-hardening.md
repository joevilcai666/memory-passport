# Production hardening guide

> Audience: the B2B installer who has finished the local POC (see
> [`CUSTOMER_QUICKSTART.zh-CN.md`](../CUSTOMER_QUICKSTART.zh-CN.md) and
> [`B2B_CUSTOMER_GUIDE.zh-CN.md`](../B2B_CUSTOMER_GUIDE.zh-CN.md)) and is now
> moving Memory Passport to pre-production or shared infrastructure.
>
> The repo deliberately ships in an "open by default, loopback-only" posture
> that is exactly right for a single-machine eval and exactly wrong for anything
> shared. This guide is the checklist of work that moves you from one to the
> other. It implements the production-readiness paragraph at the end of
> [`B2B_CUSTOMER_GUIDE.zh-CN.md`](../B2B_CUSTOMER_GUIDE.zh-CN.md) §8.

Each section is independent — pick what your deployment actually needs.

---

## 1. TLS and domain (Caddy reverse proxy)

**Problem.** The default `docker-compose.yml` binds `mp-backend` to
`127.0.0.1:8000` (HTTP, loopback only) and `hms-api` to `127.0.0.1:18080`.
Loopback is correct for a single-machine eval; the moment the install is
reachable from a LAN or the internet you need TLS termination + a real domain.

**Solution.** A reference Caddy overlay terminates TLS and fronts
`mp-backend`; `hms-api` stays loopback-internal. Caddy auto-provisions and
renews Let's Encrypt certificates for a public domain, or runs its own internal
CA for a LAN-only deployment.

```bash
# Public domain — Caddy gets a real cert from Let's Encrypt.
MP_PUBLIC_DOMAIN=passport.example.com \
  make tls-up

# LAN / VPN only — Caddy issues an internal-CA cert (install the Caddy root
# on each client once; documented in the Caddy logs on first start).
MP_PUBLIC_DOMAIN=passport.local \
  make tls-up

make tls-down   # stop, keep data
```

What the overlay does:
- Adds a `caddy` service publishing `:80` and `:443`.
- Removes the `127.0.0.1:8000` host binding from `mp-backend` so **only**
  Caddy exposes it.
- Sets conservative security headers (HSTS, `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`).
- Leaves `hms-api` untouched — it was loopback-only and is now reachable only
  over the compose network. See §5 for removing even the loopback publish.

Files: [`docker/caddy/Caddyfile`](../docker/caddy/Caddyfile),
[`docker-compose.tls.yml`](../docker-compose.tls.yml).

**Why Caddy over nginx?** Caddy's auto-HTTPS removes the cert-bot/cron dance
entirely, which is the single biggest source of ops pain at this layer. If your
org standardises on nginx, the same outcome is a ~20-line `server { listen 443
ssl; ... }` block fronting `mp-backend:8000` — the compose overlay structure is
identical, swap the `caddy` service for your nginx service.

---

## 2. Secrets management (replace placeholder credentials)

**Problem.** `.env.example` ships placeholder values
(`*_change_me`, `mp_sandbox_...`, `hms_tenant_luna_change_me`). They exist so
`make demo` works with zero config. **Every one of them must change before you
expose the install.**

**What to rotate (minimum):**

| Secret | Env var | Notes |
| --- | --- | --- |
| Postgres superuser | `POSTGRES_PASSWORD` | Used by the init script + admin ops. |
| MP DB role | `MP_DB_PASSWORD` | Now flows into the init script (see below). |
| HMS DB role | `HMS_DB_PASSWORD` | Same. |
| MP seeded API key | `MP_SEED_API_KEY` | The `mp_sandbox_...` demo key — disable after seeding real tenants. |
| HMS tenant key | `HMS_API_TENANT_API_KEY` | Shared secret MP→HMS. |
| Real-HMS model keys | `HMS_API_LLM_API_KEY`, `HMS_API_RETAIN_LLM_API_KEY`, `HMS_API_EMBEDDINGS_OPENAI_API_KEY` | `make real-up` rejects placeholders (see [`scripts/validate-real-hms-env.sh`](../scripts/validate-real-hms-env.sh)). |

> **Correctness fix in this repo.** Historically
> [`docker/postgres-init.sh`](../docker/postgres-init.sh) hard-coded the MP/HMS
> role passwords — overriding `MP_DB_PASSWORD` in `.env` had no effect on the
> roles the init script created, so the backend couldn't connect. The script
> now reads `MP_DB_PASSWORD` / `HMS_DB_PASSWORD` from the environment (passed
> through by `docker-compose.yml`), so a single `.env` override flows
> end-to-end. Defaults still match `.env.example` for `make demo`.

**Where to store secrets at scale.** The `.env` file is fine for a single
sealed host. For anything shared, use one of:

- **Docker secrets** (Swarm / Compose `secrets:`) — files mounted at
  `/run/secrets/<name>`. Works today but requires the app to read a file path
  env var (`_FILE`) instead of the literal; a small code change.
- **HashiCorp Vault** + [`vault agent`](https://developer.hashicorp.com/vault)
  templating, or the Vault container sidecar pattern. Best for multi-host.
- **Cloud KMS** (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) +
  a small bootstrapping sidecar that fetches and exports. Best when you're
  already on that cloud.

**Rotation procedure.** All keys are plain env vars today, so rotation is:

1. Generate new values (`openssl rand -base64 32` for keys, `pg_password`
   style for DB roles).
2. For API keys: insert a new `ApiKey` row for an existing app (the old one
   keeps working during the cutover). Roll clients to the new key. Once no
   traffic hits the old key, delete it.
3. For DB role passwords: rotate in a maintenance window — update
   `POSTGRES_PASSWORD` / `MP_DB_PASSWORD` / `HMS_DB_PASSWORD`, run
   `ALTER ROLE ... PASSWORD '...'` inside postgres, then `make down && make up`.
4. For HMS model keys: just swap the env and `make real-down && make real-up`.

---

## 3. Backups and restore

**Problem.** The default stack keeps all state in the `postgres-data` volume.
Losing the volume (disk failure, accidental `make clean`) loses every tenant's
data.

**Solution.** [`scripts/backup.sh`](../scripts/backup.sh) dumps both databases
(`memory_passport` + `hms`) in Postgres custom format to a timestamped
directory under `./backups/` (configurable via `BACKUP_DIR`).
[`scripts/restore.sh`](../scripts/restore.sh) replays a snapshot — it drops +
recreates both databases, restores them atomically, and refuses to report
success until database and application verification pass.

```bash
make backup                              # → ./backups/<UTC timestamp>/
make restore STAMP=20260721T020000Z      # destructive; asks for confirmation
# or: make restore STAMP=./path/to/dir
```

Both run `pg_dump`/`pg_restore` inside the `postgres` container, so no local
psql install is required. Backup and restore use exclusive maintenance windows:

1. Backup stops the configured MP/HMS writers before either dump and restarts
   them after both archives are complete, preventing MP mappings and HMS units
   from being captured at different logical times. New backups include
   `row-counts.tsv`, derived directly from each archive's COPY stream.
2. Restore parses both archives before making changes, requires the manifest,
   asks the operator to type the MP database name, and compares every restored
   table with that exact archive snapshot.
3. It discovers and stops the configured `mp-backend`, `hms-api`, and (in real
   mode) `hms-worker` services before dropping a database. Service-role
   connections stay revoked throughout the destructive window.
4. It recreates each database with its least-privilege service owner, creates
   `vector` as the privileged Postgres backup role, and replays the archive as
   that role with `--exit-on-error --single-transaction`. The archive's
   original object owners are restored; `mp`/`hms` never need extension-create
   privilege and must remain non-superusers.
5. It verifies the `vector` version/owner, MP Alembic head, required MP and HMS
   tables/indexes, representative row counts, database/relation ownership, and
   service-role access. Only then does it grant service-role `CONNECT`, restart
   the configured applications, and require `GET /v1/health` to succeed.

Any archive, extension, schema, ownership, data-query, startup, or health error
exits non-zero and never prints `restore complete`.

Backups created before the row-count manifest was introduced are intentionally
rejected because their data completeness cannot be proven. Create a fresh
backup with the current `scripts/backup.sh` before relying on this restore path.

**Interrupted/failed restore recovery.** The failure trap stops application
writers again and revokes `CONNECT` from both service roles. Leave that lock in
place: correct the reported cause (for example, replace a corrupt dump or make
the `vector` extension available to the privileged Postgres role), then rerun
the same `make restore STAMP=...`. Do not manually restart services or grant
database access to make health look green; the rerun must pass every gate.

**Schedule.** The script is cron-friendly — no flags needed for the default
`./backups/` target. Example nightly at 02:00 UTC:

```cron
0 2 * * *  /opt/memory-passport/scripts/backup.sh >> /var/log/mp-backup.log 2>&1
```

**Test the restore.** A backup you've never restored is a hope, not a backup.
Run the non-destructive command/failure-path suite on every change:

```bash
make test-restore
```

Before trusting a schedule, run the opt-in end-to-end proof:

```bash
make test-restore-roundtrip
```

That test never uses the default Compose project. It creates a uniquely named
`mp-restore-it-*` project with its own Postgres volume, ports, and temporary
backup directory; ingests a sentinel; backs up; mutates MP text, the MP↔HMS
mapping, audit data, and HMS text; restores; then proves memory text,
retrieval, mapping, Alembic head, audit, HMS data, and health returned. Its
validated cleanup trap removes only that isolated project and volume. The
first run may need to build the backend image and therefore needs package-index
access. If a known-good backend image already exists locally, the same isolated
test can avoid package-index access without reusing the default project's data:

```bash
MP_RESTORE_TEST_BACKEND_IMAGE=memory-passport-mp-backend make test-restore-roundtrip
```

**Retention.** The script keeps every backup forever; retention is the
operator's responsibility. Pair with a prune job
(`find ./backups -mtime +30 -delete` for 30-day retention) or ship the dumps to
object storage with lifecycle rules.

---

## 4. Monitoring and alerting

**Problem.** A failing HMS or DB is invisible until a user complains. The
health endpoint at `GET /v1/health` already tells the truth about all three
components — scrape it.

**What the endpoint returns** ([`backend/app/api/health.py`](../backend/app/api/health.py)):

```json
{ "mp": "ok", "hms": "ok", "db": "ok", "memory_engine": "demo" }
```

HTTP 200 when all three are `"ok"`, **HTTP 503 otherwise**. This makes it a
drop-in Prometheus blackbox target and a clean load-balancer health check.

**Prometheus scrape (blackbox exporter):**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'memory-passport-health'
    metrics_path: /probe
    params:
      module: [http_2xx]   # 503 → probe_success=0
    static_configs:
      - targets: ['https://passport.example.com/v1/health']
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

**Alertmanager rules (minimum):**

```yaml
groups:
  - name: memory-passport
    rules:
      - alert: MemoryPassportDown
        expr: probe_success{job="memory-passport-health"} == 0
        for: 2m
        annotations:
          summary: "Memory Passport health probe is failing ({{ $labels.instance }})"
      # The HTTP 503 path covers hms != ok OR db != ok already; if you want to
      # distinguish, expose a richer /metrics endpoint later.
```

**Structured log shipping.** The containers log plain JSON or console lines
(depending on `MP_LOG_FORMAT` / `HMS_API_LOG_FORMAT`). Ship via your usual
Docker log driver (Fluent Bit, Vector, CloudWatch) — there's no app-side
change required.

---

## 5. Access control (hms-api stays internal)

**Problem.** `docker-compose.yml` publishes `hms-api` on `127.0.0.1:18080`.
That's fine for local eval (you can poke it from the host for debugging) but
wrong for shared infra — the HMS API is a privileged internal service and must
not be reachable outside the compose network.

**Solution.** In production, remove the `hms-api` `ports:` binding entirely so
only `mp-backend` (on the same `mp-net` bridge) can reach it. Two options:

- **Quickest:** override it in your own compose overlay:
  ```yaml
  # docker-compose.no-hms-port.yml
  services:
    hms-api:
      ports: !reset []
  ```
  then `docker compose -f docker-compose.yml -f docker-compose.tls.yml -f docker-compose.no-hms-port.yml up -d`.

- **Permanent:** if you never use the host-side HMS debug port, delete the
  `ports:` block under `hms-api` in `docker-compose.yml`.

The Caddy overlay (§1) already drops the `mp-backend` host binding; doing the
same for `hms-api` closes the last publicly-reachable service port.

---

## 6. Region and compliance review

**Problem.** Memory Passport stores end-user personal data (memories, audit
trails, export bundles). Where that data physically lives matters for GDPR,
CCPA, PIPL, and sector-specific rules.

**What the app records.** Each [`App`](../backend/app/models/tenant.py) row has
a `data_region` field (e.g. `us-east-1`, `eu-west-1`) documenting where the
tenant's data is intended to reside. The field is informational today — the app
does not yet enforce that the Postgres backing matches it — so compliance is an
**operator responsibility**: confirm the deployment region matches every
tenant's `data_region`, and don't onboard tenants whose declared region you
can't satisfy.

**Checklist before going live:**

- [ ] The host/region running this stack matches every onboarded tenant's
      `App.data_region`.
- [ ] `var/exports/` (the on-disk export bundles) is on encrypted storage and
      on the same host as the database (export artifacts reference real user
      data — treat them with the same care as the DB).
- [ ] Backups (§3) land in the same regulatory region as the primary.
- [ ] The delete-user endpoint (`POST /v1/delete_user`) is exercised during
      acceptance — it tombstones memories and deletes the HMS bank, which is
      your right-to-erasure primitive.
- [ ] Audit log retention (`audit_logs` table) matches the customer's policy;
      the app writes one row per mutating action and never deletes them.

---

## What this repo does NOT do

These remain the operator's responsibility and are out of scope for V0.1:

- **Network-level DDoS protection** — put a CDN/WAF (Cloudflare, Cloud Front,
  etc.) in front of Caddy if you need it.
- **Per-tenant rate limiting / quotas** — `services/usage.py` records usage
  events but doesn't enforce limits; add a middleware if a tenant could
  meaningfully abuse the API.
- **Backup encryption at rest** — `pg_dump` output is unencrypted; encrypt the
  `BACKUP_DIR` (filesystem-level) or pipe through `gpg` before ship-to-object-storage.
- **HA / multi-host** — the default topology is single-host. Multi-host needs
  external Postgres (RDS, Cloud SQL) and shared export storage; that's a
  deployment redesign, not a config flip.

For the original scoping statement see
[`B2B_CUSTOMER_GUIDE.zh-CN.md`](../B2B_CUSTOMER_GUIDE.zh-CN.md) §8 closing
paragraph.
