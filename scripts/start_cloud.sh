#!/bin/sh
# Cloud entrypoint: fetch models (best-effort), start the worker in the
# background, then serve the API on $PORT (7860 = Hugging Face Spaces default).
set -u

python scripts/fetch_models.py || echo "model fetch failed; continuing with fallbacks"

python -m services.worker.run &
WORKER_PID=$!
echo "worker started (pid $WORKER_PID)"

exec uvicorn apps.api.main:app --host 0.0.0.0 --port "${PORT:-7860}"
