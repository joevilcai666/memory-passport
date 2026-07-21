COMPOSE ?= $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)

.PHONY: help build demo up down clean seed check real-config real-up real-down tls-up tls-down backup restore

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
	pnpm lint
	pnpm build
	cd backend && .venv/bin/ruff check app tests
	cd backend && .venv/bin/pytest -m 'not postgres and not hms and not compose' -q
	$(COMPOSE) up -d --wait --remove-orphans
	$(COMPOSE) exec -T mp-backend pytest -q
	@echo ""
	@echo "Note: steps 1-4 (lint/build/ruff/unit pytest) also run in GitHub Actions"
	@echo "      (.github/workflows/ci.yml). The compose integration above (steps 5-6)"
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
