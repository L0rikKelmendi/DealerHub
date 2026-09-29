.PHONY: help install api seed test test-backend lint migrate revision up down logs

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install backend dependencies
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

api: ## Run the API locally (needs Postgres + Redis running)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

seed: ## Seed demo data
	cd backend && .venv/bin/python -m app.seed

migrate: ## Apply all Alembic migrations
	cd backend && .venv/bin/alembic upgrade head

revision: ## Autogenerate a migration (make revision m="message")
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(m)"

test: test-backend ## Run the test suite

test-backend: ## Backend unit + API tests (needs Postgres + Redis on TEST_DATABASE_URL/TEST_REDIS_URL)
	cd backend && .venv/bin/pytest -q

lint: ## Ruff for backend
	cd backend && .venv/bin/ruff check app tests

up: ## Start the stack with Docker Compose
	docker compose up --build

down: ## Stop the stack
	docker compose down

logs: ## Tail stack logs
	docker compose logs -f api
