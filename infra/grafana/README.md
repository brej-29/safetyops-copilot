# Grafana Dashboard

A "SafetyOps Copilot — Overview" dashboard is auto-provisioned on startup —
no manual setup needed.

## Run it

```bash
# 1. Start infra (Postgres, Redis, MLflow, Prometheus, Grafana)
make up

# 2. Start the API and worker (separate terminals, or `docker compose` services)
make api
make worker
```

Then open **http://localhost:3000** — anonymous viewer access is enabled for
local demo purposes, so the dashboard loads directly (no login required).
The `admin` / `admin` credentials still work if you want to edit panels.

## Generate some data to see it move

```bash
make produce-demo
# or, repeatedly, from the Streamlit UI's "Produce demo events" button
```

Within ~15–30 seconds you should see:

- **Events ingested (total)** and **Events processed successfully** ticking up
- **Ingestion rate** and **Processing rate by status** time series moving
- **Worker processing latency (p95)** and **Model inference latency (p95)**
  populating once a few events have gone through

## What's being scraped

- `safetyops-api` job → the FastAPI `/metrics` endpoint (ingestion counters).
- `safetyops-worker` job → a **separate** metrics endpoint served by the
  worker process itself, on port `9100` (`safetyops.core.settings.worker_metrics_port`).

This split exists because the API and worker are separate OS processes, each
with its own Prometheus client registry — the worker's processing/DLQ/model
metrics are not visible through the API's `/metrics` and must be scraped
directly from the worker.

## Files

- `../prometheus/prometheus.yml` — scrape targets for both jobs above.
- `provisioning/datasources/prometheus.yml` — auto-adds the Prometheus datasource.
- `provisioning/dashboards/dashboards.yml` — tells Grafana to load dashboards from `dashboards/`.
- `dashboards/safetyops-overview.json` — the dashboard itself (edit and it reloads within ~30s).

## Running everything via docker-compose instead?

The scrape targets in `prometheus.yml` default to `host.docker.internal`,
matching the primary dev flow (`make up` for infra, `make api` / `make
worker` on the host). If you instead run the API and worker as the `api` /
`worker` compose services, change the targets to `api:8000` / `worker:9100`.
On Linux, `host.docker.internal` isn't available by default — use your host's
IP instead.
