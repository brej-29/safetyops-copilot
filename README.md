# SafetyOps Copilot

A production-style **SafetyOps Copilot** for monitoring safety incidents from:

- **Vision events**: PPE compliance checks (person + hardhat/vest) via YOLO inference.
- **Text events**: free-text incident reports categorized and severity-scored.

The system is designed to be:

- **Local-first, free-first** – runs on a laptop with Docker and CPU-only dependencies.
- **Production-shaped** – clear separation between API, worker, UI, and infra.
- **AI-friendly** – context and decisions are documented to keep future changes grounded.

---

## High-level Architecture

```mermaid
flowchart LR
    subgraph Ingestion
        UI[Streamlit UI<br/>apps/ui]
        API[FastAPI API<br/>apps/api]
    end

    subgraph Streaming
        RS[(Redis Streams)]
    end

    subgraph Processing
        W[Worker Service<br/>services/worker]
        MLVision[YOLO PPE Wrapper<br/>safetyops/ml/vision]
        MLText[NLP Severity Model<br/>safetyops/ml/nlp]
        Agent[Copilot Triage Workflow<br/>safetyops/agents]
    end

    subgraph Storage
        PG[(Postgres)]
    end

    subgraph Monitoring
        Prom[Prometheus]
        Graf[Grafana]
        MLflow[MLflow Server]
    end

    UI -- HTTP --> API
    API -- publish events --> RS
    W -- consume events --> RS
    W -- raw + enriched events --> PG
    W -- aggregates --> PG

    API -- read --> PG
    UI -- HTTP --> API
    API -- /copilot/triage --> Agent

    API -- /metrics --> Prom
    W -- worker metrics --> Prom
    Prom -- dashboards --> Graf

    W -- training logs --> MLflow
```

---

## Repo Map

Core layout (created for v1):

- `context/`
  - `00_GOAL.md` – goal, scope, non-goals.
  - `01_ARCHITECTURE.md` – components, dataflow, diagrams.
  - `02_COMPONENTS.md` – detailed component descriptions.
  - `03_DECISIONS_LOG.md` – ADR-style decisions log.
  - `04_COSINE_WORKFLOW.md` – how to ground future AI tasks.
  - `05_ROADMAP.md` – roadmap for Prompt 1 and beyond.
- `apps/`
  - `api/` – FastAPI app (ingestion, health, metrics, queries).
  - `ui/` – Streamlit UI (live feed, triage, dashboard).
- `services/`
  - `worker/` – stream consumer, inference, persistence, aggregates.
- `safetyops/`
  - `core/` – logging, settings, exceptions.
  - `domain/` – Pydantic models for events, predictions, API schemas.
  - `ml/`
    - `vision/` – YOLO PPE inference wrapper and optional training.
    - `nlp/` – rule-based classifier plus DistilBERT fine-tuning and inference.
  - `streaming/` – Redis Streams event bus abstraction.
  - `db/` – SQLAlchemy models, engine/session, migrations scaffold.
  - `monitoring/` – Prometheus metrics helpers and Evidently drift reporting.
  - `agents/` – multi-step triage workflow (Copilot).
  - `runbooks/` – markdown incident playbooks used by the triage agent.
- `data/`
  - `sample/` – tiny synthetic sample inputs (text, vision placeholders).
- `notebooks/`
  - `00_text_eda.ipynb` – incident text EDA and modeling plan.
  - `01_vision_eda.ipynb` – PPE detection EDA and evaluation plan.
  - `02_end_to_end_walkthrough.ipynb` – system walkthrough and usage.
- `scripts/`
  - `dev_run_local.sh` – helper to spin up local infra.
  - `seed_demo_data.py` – seed database with demo events/aggregates.
  - `produce_demo_events.py` – generate demo events into the stream/API.
- `infra/`
  - `docker-compose.local.yml` – local infra stack.
  - `prometheus/prometheus.yml` – scrape config.
  - `grafana/` – placeholders for dashboards.
- `.github/workflows/ci.yml` – CI pipeline (ruff + pytest).
- `.env.example` – example environment configuration.
- `requirements.txt`, `requirements-dev.txt` – Python dependencies.
- `Makefile` – common commands.

---

## Getting Started

For a full, step-by-step local run manual (with copy-paste commands for macOS, Linux, and Windows), see:

- `context/06_LOCAL_RUN_GUIDE.md`

A detailed free-tier deployment guide lives in:

- `context/07_FREE_DEPLOY_GUIDE.md`

Below is a concise quickstart.

### Quickstart (Local)

#### 1. Prerequisites

- Python **3.10+**
- Docker and Docker Compose
- `make` (optional but convenient)

#### 2. Setup environment

```bash
# Clone the repo and cd into it
git clone <your-fork-or-origin> safetyops-copilot
cd safetyops-copilot

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# Install dependencies
make install  # or: python -m pip install --upgrade pip && pip install -r requirements-dev.txt

# Copy example env and adjust values if needed
cp .env.example .env
```

By default, the app expects local Postgres and Redis as defined in `infra/docker-compose.local.yml`. For a Docker-free demo you can instead set `SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db` in `.env`.

#### 3. Start local infra (Postgres, Redis, MLflow, Prometheus, Grafana)

```bash
make up
# or directly:
# docker compose -f infra/docker-compose.local.yml up -d
```

This brings up:

- Postgres on `localhost:5432`
- Redis on `localhost:6379`
- MLflow on `localhost:5000`
- Prometheus on `localhost:9090`
- Grafana on `localhost:3000`

#### 4. Run services locally

In **three separate terminals** (with the venv activated):

**API (FastAPI + Uvicorn)**

```bash
make api
# or:
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Worker**

```bash
make worker
# or:
python -m services.worker.run
```

**UI (Streamlit)**

```bash
make ui
# or:
streamlit run apps/ui/main.py --server.port 8501
```

You should now have:

- API at `http://localhost:8000`
- OpenAPI docs at `http://localhost:8000/docs`
- UI at `http://localhost:8501`
- Prometheus scraping `http://localhost:8000/metrics`
- MLflow at `http://localhost:5000`
- Grafana at `http://localhost:3000`

---

## API Overview

Key endpoints (FastAPI):

- `GET /health`
  - Returns `{ "status": "ok", "version": <app_version> }`.
- `GET /metrics`
  - Prometheus-compatible metrics.
- `POST /events/text`
  - Ingests an incident text event.
  - Publishes a `text_event` into Redis Streams.
- `POST /events/vision`
  - Ingests a vision event from:
    - An uploaded image; or
    - A path to a sample image (e.g. under `data/sample`).
  - Publishes a `vision_event` into Redis Streams.
- `GET /events/recent`
  - Returns recent enriched events from Postgres.
- `GET /aggregates/summary`
  - Returns simple aggregates (counts by type/severity over a recent window).
- `POST /monitoring/drift/run`
  - Runs Evidently-based drift analysis comparing training vs. recent events.
- `GET /monitoring/drift/latest`
  - Returns the path of the latest drift report HTML file.
- `GET /dlq/recent`
  - Returns recent messages that failed processing and were sent to the DLQ stream.
- `POST /reprocess/{message_id}`
  - Re-publishes a DLQ message for reprocessing by the worker.
- `POST /copilot/triage`
  - Runs the Copilot triage workflow for a given incident ID or free-text description.
  - Returns structured JSON plus a markdown incident brief.

All ingestion and response schemas are defined under `safetyops.domain`.

---

## Worker Overview

Entry point:

```bash
python -m services.worker.run
```

Responsibilities:

1. Ensure Redis consumer group exists.
2. Consume events from the stream using `RedisStreamsEventBus`.
3. For each event:
   - Store a `RawEvent` row.
   - Run enrichment:
     - **Text**: rule-based classifier (`safetyops.ml.nlp.classifier`).
     - **Vision**: YOLO PPE wrapper (`safetyops.ml.vision.yolo`) with:
       - Lazy import of `ultralytics` and `torch`.
       - Fallback stub if the model is unavailable (logged).
   - Store an `EnrichedEvent` row.
   - Update `DailyAggregate` for `(date, event_type, severity)`.
   - Acknowledge the message to Redis.

Metrics (Prometheus) capture publish and processing counts/timings.

---

## Streamlit UI Overview

Run:

```bash
streamlit run apps/ui/main.py --server.port 8501
```

Tabs:

1. **Live Feed**
   - Button to produce N demo events (both text and vision).
   - Auto-refreshes recent enriched events from `/events/recent`.
2. **Incident Triage**
   - Text area for incident description.
   - Submits to `/events/text`.
   - Displays the latest triaged incidents.
3. **Copilot Chat**
   - Text area to describe an incident.
   - Calls `/copilot/triage` and shows:
     - Structured JSON (category, severity, risk score, context events).
     - A markdown incident brief with immediate and preventive actions.
4. **Ops Dashboard**
   - Uses `/aggregates/summary` to render simple charts by event type and severity.
5. **Monitoring**
   - Button to trigger drift analysis via `/monitoring/drift/run`.
   - Shows latest drift report path and (where possible) an inline HTML preview.
   - Summarizes key Prometheus metrics: events ingested, processed, DLQ counts.

---

## Environment Variables

All configuration is centralized via `safetyops.core.settings.Settings` using `pydantic-settings`.

Key variables (prefix `SAFETYOPS_`):

| Variable                         | Default (local)                                                   | Description                                      |
|----------------------------------|-------------------------------------------------------------------|--------------------------------------------------|
| `SAFETYOPS_APP_NAME`            | `SafetyOps Copilot`                                               | Display name                                     |
| `SAFETYOPS_APP_VERSION`         | `0.1.0`                                                           | API version                                      |
| `SAFETYOPS_ENV`                 | `local`                                                           | Environment name                                 |
| `SAFETYOPS_LOG_LEVEL`           | `INFO`                                                            | Logging level                                    |
| `SAFETYOPS_DEPLOY_MODE`         | `local`                                                           | `local` or `cloud` deploy mode                   |
| `SAFETYOPS_REDIS_URL`           | `redis://localhost:6379`                                          | Redis connection URL                             |
| `SAFETYOPS_STREAM_KEY`          | `safetyops:events`                                                | Redis Stream key                                 |
| `SAFETYOPS_CONSUMER_GROUP`      | `safetyops-workers`                                               | Redis consumer group name                        |
| `SAFETYOPS_CONSUMER_NAME`       | `worker-1`                                                        | Consumer name                                    |
| `SAFETYOPS_DLQ_STREAM_KEY`      | `safetyops:events:dlq`                                            | Redis Stream key for DLQ messages                |
| `SAFETYOPS_DATABASE_URL`        | `postgresql+psycopg2://safetyops:safetyops@localhost:5432/safetyops` | Postgres URL for SQLAlchemy                      |
| `SAFETYOPS_MLFLOW_TRACKING_URI` | `http://localhost:5000`                                           | MLflow tracking URI                              |
| `SAFETYOPS_ARTIFACTS_DIR`       | `artifacts`                                                       | Base directory for derived artifacts             |
| `SAFETYOPS_NLP_MODEL_DIR`       | `models/nlp`                                                      | Directory containing the fine-tuned NLP model    |
| `SAFETYOPS_VISION_MODEL_PATH`   | `yolov8n.pt`                                                      | YOLOv8 weights path (pretrained or fine-tuned)   |
| `SAFETYOPS_OLLAMA_BASE_URL`     | *(unset)*                                                         | Base URL for local Ollama (optional)             |
| `SAFETYOPS_OLLAMA_MODEL`        | *(unset)*                                                         | Ollama model name (e.g. `llama3`)                |
| `SAFETYOPS_METRICS_NAMESPACE`   | `safetyops`                                                       | Prefix/namespace for Prometheus metrics          |

Update `.env.example` and `.env` if new configuration is introduced.

---

## Deploy (Free Tiers)

For a detailed guide to deploying on Streamlit Community Cloud and Hugging Face Spaces (with optional managed Redis/Postgres), see:

- `context/07_FREE_DEPLOY_GUIDE.md`

It describes:

- A simple Streamlit-only demo mode.
- A more realistic API + UI deployment with free managed services.
- Recommended environment variables and trade-offs for SQLite vs Postgres.

---

## Tooling and CI

### Linting

Uses `ruff`:

```bash
make lint
# or:
ruff check .
```

Configuration lives in `ruff.toml` (PEP8-ish with basic import checks).

### Testing

Uses `pytest`:

```bash
make test
# or:
pytest
```

Current tests cover:

- Event model validation.
- Redis Streams event bus (mocked client).
- Worker enrichment logic for text and vision (without requiring YOLO).

Tests are designed to avoid heavy imports (YOLO/torch) by using lazy imports and stubs.

### GitHub Actions

`.github/workflows/ci.yml` runs on pushes and PRs:

1. Sets up Python.
2. Installs `requirements-dev.txt`.
3. Runs `ruff`.
4. Runs `pytest`.

---

## Grounding for Future AI Changes

Before making significant changes (especially as an AI assistant):

1. Read `context/00_GOAL.md` to understand scope and non-goals.
2. Read `context/01_ARCHITECTURE.md` for the system view.
3. Read `context/02_COMPONENTS.md` for component details.
4. Skim `context/03_DECISIONS_LOG.md` for prior trade-offs.
5. Check `context/05_ROADMAP.md` to see where your change fits.

When you:

- Change an architectural decision, update `context/03_DECISIONS_LOG.md`.
- Add a new dependency or external service, document why.
- Adjust core flows (API, worker, stream, DB), update the notebooks and README as needed.

---

## Troubleshooting

**Q: The API cannot connect to Postgres or Redis**

- Ensure infra is running:

  ```bash
  docker compose -f infra/docker-compose.local.yml ps
  ```

- Check `SAFETYOPS_DATABASE_URL` and `SAFETYOPS_REDIS_URL` in `.env`.
- Confirm ports are not blocked or used by other services.

**Q: YOLO or torch imports fail**

- For running the system:
  - Install dependencies from `requirements.txt` (includes `ultralytics` and `torch`).
- For CI or constrained environments:
  - The code is written with lazy imports and fallbacks:
    - Failures are logged.
    - A stub PPE prediction is used so the pipeline continues to run.

**Q: Tests are slow or flaky**

- Ensure you are not accidentally pointing tests at real infra.
- Tests use mocks/fakes for Redis and do not require a running database.
- If you introduce new tests that touch heavy components, keep them isolated and fast.

---

## Exact Commands to Remember

```bash
# Install dev dependencies
make install

# Start infra (Postgres, Redis, MLflow, Prometheus, Grafana)
make up

# Run API
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Run worker
python -m services.worker.run

# Run UI
streamlit run apps/ui/main.py --server.port 8501

# Lint
make lint

# Test
make test
```

This README should be kept in sync with the `context/` docs and notebooks as the project evolves.