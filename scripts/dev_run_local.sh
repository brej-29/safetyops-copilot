#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwdamp; pwd)"

cd "$ROOT_DIR"

echo "Starting local infra (Postgres, Redis, MLflow, Prometheus, Grafana)..."
docker compose -f infra/docker-compose.local.yml up -d

echo
echo "Infra started."
echo "Run the following in separate terminals to start the services:"
echo "  uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000"
echo "  python -m services.worker.run"
echo "  streamlit run apps/ui/main.py --server.port 8501"