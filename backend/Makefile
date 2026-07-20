# Memory Passport backend — developer commands.
# Targets prefer the Docker Compose plugin and fall back to standalone Compose.
# Local (non-docker) equivalents are in the README.

DC ?= $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)
MP_RUN ?= $(DC) run --rm mp-backend
MP_EXEC ?= $(DC) exec mp-backend

.PHONY: help build up down logs ps dev migrate upgrade downgrade seed test lint smoke clean real-up

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

build: ## Build the default local images
	$(DC) build

up: ## Start the credential-free stack (postgres + demo hms-api + mp-backend)
	$(DC) up -d --remove-orphans

down: ## Stop the stack (keeps volumes)
	$(DC) down

ps: ## Show service status
	$(DC) ps

logs: ## Tail logs (all services)
	$(DC) logs -f --tail=100

dev: up ## Start the stack and tail mp-backend logs
	$(DC) logs -f mp-backend

migrate: ## Apply Alembic migrations to head
	$(MP_RUN) alembic upgrade head

upgrade: migrate ## Alias of migrate

downgrade: ## Roll all migrations back to base (clean slate)
	$(MP_RUN) alembic downgrade base

seed: ## Seed the Luna dataset + provision empty HMS banks
	$(MP_EXEC) python -m app.seed.run_seed

test: ## Run the pytest suite
	$(MP_RUN) pytest

lint: ## Run ruff
	$(MP_RUN) ruff check .

smoke: ## The Slice 1 acceptance smoke test: up -> seed -> health
	$(MAKE) up
	@echo ">> waiting for services to become healthy..."
	@$(DC) exec -T mp-backend sh -c 'for i in $$(seq 1 30); do curl -fsS http://localhost:8000/v1/health && break; sleep 2; done'
	$(MAKE) seed
	@curl -s http://localhost:8000/v1/health | python3 -m json.tool

clean: ## Stop and remove containers + volumes (DESTRUCTIVE — wipes DB data)
	$(DC) down -v

real-up: ## Start the pinned real HMS API and worker overlay
	$(MAKE) -C .. real-up
