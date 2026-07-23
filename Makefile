COMPOSE ?= $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)

.PHONY: help build demo up down clean seed check real-config real-up real-down tls-up tls-down backup restore restore-verify test-backup test-restore test-restore-roundtrip check-e2e

help: ## Show local evaluator commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

build: ## Explicitly rebuild default local images
	$(COMPOSE) build

demo: ## Start, seed, and exercise the credential-free local stack
	$(COMPOSE) up -d --wait --remove-orphans
	$(COMPOSE) exec -T mp-backend alembic upgrade head
	$(COMPOSE) exec -T mp-backend python -m app.seed.run_seed
	./scripts/demo.sh

up: ## Start the credential-free local stack
	$(COMPOSE) up -d --wait --remove-orphans

down: ## Stop the default local stack and preserve data
	$(COMPOSE) down

clean: ## Stop the stack and delete local database volumes (DESTRUCTIVE)
	$(COMPOSE) down --volumes --remove-orphans

seed: ## Idempotently load the Luna evaluator dataset
	$(COMPOSE) exec -T mp-backend python -m app.seed.run_seed

check: ## Run frontend, backend, and running-stack checks locally
	python3 scripts/check_line_endings.py
	$(MAKE) test-backup test-restore
	pnpm test
	pnpm lint
	pnpm build
	cd backend && .venv/bin/ruff check app tests
	cd backend && .venv/bin/pytest -m 'not postgres and not hms and not compose' -q
	$(COMPOSE) up -d --wait --remove-orphans
	$(COMPOSE) exec -T mp-backend pytest -q
	@echo ""
	@echo "Note: portability, restore/frontend tests, lint/build, ruff, and unit pytest also run in GitHub Actions"
	@echo "      (.github/workflows/ci.yml). The compose integration above"
	@echo "      stays local — it needs a running stack. See issue #15."

real-config: ## Validate credentials and render the real-HMS Compose overlay
	./scripts/validate-real-hms-env.sh
	$(COMPOSE) -f docker-compose.yml -f docker-compose.real.yml config >/dev/null

real-up: real-config ## Start the pinned real HMS API/worker stack
	$(COMPOSE) -f docker-compose.yml -f docker-compose.real.yml up -d --wait --remove-orphans

real-down: ## Stop the real-HMS overlay stack and preserve data
	$(COMPOSE) -f docker-compose.yml -f docker-compose.real.yml down

tls-up: ## Start the stack behind the Caddy TLS reverse proxy (requires MP_PUBLIC_DOMAIN)
	$(COMPOSE) -f docker-compose.yml -f docker-compose.tls.yml up -d --wait --remove-orphans

tls-down: ## Stop the TLS overlay stack and preserve data
	$(COMPOSE) -f docker-compose.yml -f docker-compose.tls.yml down

backup: ## Dump both databases to ./backups/<timestamp>/ (see scripts/backup.sh)
	./scripts/backup.sh

restore: ## Restore a backup snapshot — USAGE: make restore STAMP=<timestamp>  (or STAMP=./path)
	@if [ -z "$(STAMP)" ]; then echo "Usage: make restore STAMP=20260721T020000Z" >&2; exit 1; fi
	./scripts/restore.sh "$(STAMP)"

restore-verify: ## DESTRUCTIVE: prove backup/restore row, pgvector, owner, and health parity
	./scripts/verify-restore.sh

test-backup: ## Run non-destructive backup consistency tests
	./scripts/tests/backup_test.sh

test-restore: ## Run non-destructive restore command/failure-path tests
	./scripts/tests/restore_test.sh

test-restore-roundtrip: ## Run destructive restore test in a unique disposable Compose project
	./scripts/tests/restore_roundtrip.sh

check-e2e: ## Run the browser→API→database E2E gate against a clean seeded stack
	$(COMPOSE) down --volumes --remove-orphans
	$(COMPOSE) up -d --wait --remove-orphans
	$(COMPOSE) exec -T mp-backend alembic upgrade head
	$(COMPOSE) exec -T mp-backend python -m app.seed.run_seed
	pnpm build
	MP_API_URL=http://127.0.0.1:8000 MP_API_KEY=mp_sandbox_LK39sn8vQ4x2pRwY1tBz0Hd \
	  MP_GATEWAY_ALLOW_UNAUTHENTICATED=true pnpm start --hostname 127.0.0.1 --port 3000 & \
	  SERVER_PID=$$!; \
	for i in $$(seq 1 60); do curl -sf http://127.0.0.1:3000 >/dev/null && break; sleep 1; done; \
	pnpm test:e2e; EXIT=$$?; kill $$SERVER_PID 2>/dev/null || true; exit $$EXIT
