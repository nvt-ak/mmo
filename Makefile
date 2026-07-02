ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python3
NPM ?= npm
DOCKER_COMPOSE ?= docker compose
export DATABASE_URL ?= postgresql://postgres:postgres@localhost:5432/videoscout
export SCHEDULER_ENABLED ?= true
export NEXT_PUBLIC_API_URL ?= http://localhost:8000

RUN_DIR := $(ROOT_DIR)/.run
API_PID := $(RUN_DIR)/api.pid
WEB_PID := $(RUN_DIR)/web.pid

.PHONY: help up down install db-up db-down wait-db migrate stop-apps logs

help:
	@echo "VideoScout dev stack"
	@echo ""
	@echo "  make install   Install Python + Node dependencies"
	@echo "  make up        Start Postgres, migrate, API (:8000), Web (:3000)"
	@echo "  make down      Stop API/Web processes and Postgres container"
	@echo "  make db-up     Start Postgres only"
	@echo "  make db-down   Stop Postgres container"
	@echo "  make migrate   Run Alembic migrations"
	@echo "  make logs      Tail Postgres logs"

install:
	cd $(ROOT_DIR)/videoscout && $(PYTHON) -m pip install -r requirements.txt
	cd $(ROOT_DIR)/web && $(NPM) install

db-up:
	cd $(ROOT_DIR) && $(DOCKER_COMPOSE) up -d postgres

db-down:
	cd $(ROOT_DIR) && $(DOCKER_COMPOSE) down

wait-db:
	@echo "Waiting for PostgreSQL..."
	@for i in $$(seq 1 30); do \
		cd $(ROOT_DIR) && $(DOCKER_COMPOSE) exec -T postgres pg_isready -U postgres -d videoscout >/dev/null 2>&1 && exit 0; \
		sleep 1; \
	done; \
	echo "PostgreSQL not ready after 30s"; exit 1

migrate:
	cd $(ROOT_DIR) && $(PYTHON) -m alembic upgrade head

stop-apps:
	@if [ -f "$(API_PID)" ]; then kill $$(cat "$(API_PID)") 2>/dev/null || true; rm -f "$(API_PID)"; fi
	@if [ -f "$(WEB_PID)" ]; then kill $$(cat "$(WEB_PID)") 2>/dev/null || true; rm -f "$(WEB_PID)"; fi

logs:
	cd $(ROOT_DIR) && $(DOCKER_COMPOSE) logs -f postgres

down: stop-apps db-down

up: db-up wait-db migrate
	@mkdir -p "$(RUN_DIR)"
	@echo "VideoScout running — API http://localhost:8000  Web http://localhost:3000"
	@echo "Press Ctrl+C to stop API and Web (Postgres keeps running; use 'make down' to stop all)"
	@set -e; \
	set -a; \
	[ -f "$(ROOT_DIR)/videoscout/.env" ] && . "$(ROOT_DIR)/videoscout/.env"; \
	set +a; \
	trap '$(MAKE) stop-apps' INT TERM; \
	cd "$(ROOT_DIR)" && $(PYTHON) -m uvicorn videoscout.api_main:app --reload --host 0.0.0.0 --port 8000 & \
	echo $$! > "$(API_PID)"; \
	cd "$(ROOT_DIR)/web" && $(NPM) run dev & \
	echo $$! > "$(WEB_PID)"; \
	wait
