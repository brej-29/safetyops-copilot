.PHONY: help install lint test up down api worker ui fmt format seed produce-demo

help:
	@echo "Common SafetyOps Copilot commands:"
	@echo "  make install       Install dev dependencies"
	@echo "  make up            Start local infra (Postgres, Redis, MLflow, Prometheus, Grafana)"
	@echo "  make down          Stop local infra"
	@echo "  make api           Run FastAPI server locally"
	@echo "  make worker        Run worker service locally"
	@echo "  make ui            Run Streamlit UI locally"
	@echo "  make lint          Run Ruff lint checks"
	@echo "  make fmt           Auto-fix style issues with Ruff"
	@echo "  make test          Run pytest test suite"
	@echo "  make seed          Seed demo data into the database"
	@echo "  make produce-demo  Publish demo events into the stream"

install:
	python -m pip install --upgrade pip
	pip install -r requirements-dev.txt

lint:
	ruff check .

test:
	pytest

up:
	docker compose -f infra/docker-compose.local.yml up -d

down:
	docker compose -f infra/docker-compose.local.yml down

api:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

worker:
	python -m services.worker.run

ui:
	streamlit run apps/ui/main.py --server.port 8501

fmt:
	ruff check --fix .

# Backwards-compatible alias
format: fmt

seed:
	python scripts/seed_demo_data.py

produce-demo:
	python scripts/produce_demo_events.py