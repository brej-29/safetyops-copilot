<div align="center">
  <h1>🦺 safetyops-copilot</h1>
  <p><i>Production-style safety-incident pipeline with a LangGraph triage Copilot,
  a DistilBERT severity model fine-tuned on 273k real accident reports, and
  YOLOv8 PPE detection — deployed live on free-tier cloud infrastructure.</i></p>
</div>

<br>

<div align="center">
  <img alt="Language" src="https://img.shields.io/badge/Language-Python-blue">
  <img alt="Backend" src="https://img.shields.io/badge/Backend-FastAPI-009688">
  <img alt="Streaming" src="https://img.shields.io/badge/Streaming-Redis%20Streams-DC382D">
  <img alt="Database" src="https://img.shields.io/badge/Database-PostgreSQL-336791">
  <img alt="ML" src="https://img.shields.io/badge/ML-DistilBERT%20%7C%20YOLOv8-ff9800">
  <img alt="Agent" src="https://img.shields.io/badge/Agent-LangGraph-1C3C3C">
  <img alt="Frontend" src="https://img.shields.io/badge/Frontend-Streamlit-ff4b4b">
  <img alt="Tests" src="https://img.shields.io/badge/Tests-36%20passing-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-black">
</div>

<br>

**🚀 [Live demo](https://safetyops-copilot.streamlit.app/)** — try it with sample incident reports and site photos, no setup required.

A production-style **SafetyOps Copilot** for monitoring safety incidents from:

- **Vision events**: PPE compliance checks (person + hardhat/vest) via YOLO inference.
- **Text events**: free-text incident reports categorized and severity-scored.

The system is designed to be:

- **Local-first, free-first** – runs on a laptop with Docker and CPU-only dependencies, and deploys entirely on free cloud tiers (Cloud Run, Neon, Upstash, Streamlit Cloud).
- **Production-shaped** – clear separation between API, worker, UI, and infra; event-driven with retries, a dead-letter queue, and idempotent processing.
- **Honestly evaluated** – the severity model is trained and tested on real public accident data, with baseline comparisons and documented limitations, not synthetic demo metrics.

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
- `requirements/` – per-service dependency files:
  - `base.txt` – shared runtime deps for the `safetyops` package.
  - `api.txt`, `worker.txt`, `ui.txt` – slim installs per service.
  - `ml.txt` – heavy ML deps (torch, transformers, ultralytics, mlflow); optional — inference falls back to rule-based/stub predictions without it.
- `requirements.txt` – full install (all of the above); `requirements-dev.txt` – all services (no heavy ML) plus pytest/ruff/fakeredis.
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

- Python **3.10–3.12** (3.11 recommended; heavy ML deps are not yet reliable on 3.13+)
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
     - **Text**: fine-tuned DistilBERT severity model (`safetyops.ml.nlp.infer`),
       falling back to the rule-based classifier when the model or its heavy
       dependencies are absent.
     - **Vision**: YOLO PPE wrapper (`safetyops.ml.vision.infer`) with:
       - Lazy import of `ultralytics` and `torch`.
       - Fallback stub if the model is unavailable (logged once).
   - Store an `EnrichedEvent` row.
   - Update `DailyAggregate` for `(date, event_type, severity)`.
   - Acknowledge the message to Redis.

Metrics (Prometheus) capture publish and processing counts/timings.

---

## Models and Results

### Text severity (DistilBERT, real data)

`distilbert-base-uncased` fine-tuned on **real MSHA accident narratives**
(273k public mine-safety reports; labels derived from the reported
`DEGREE_INJURY` outcome — see [ADR-0015](context/03_DECISIONS_LOG.md) and
[models/nlp/MODEL_CARD.md](models/nlp/MODEL_CARD.md)).

Held-out test set (1,605 balanced samples):

| Model               | Accuracy | Macro-F1 | High-severity recall |
|---------------------|----------|----------|----------------------|
| Rule-based baseline | 0.40     | 0.34     | 0.16                 |
| **DistilBERT**      | **0.78** | **0.78** | **0.88**             |

Reproduce:

```bash
pip install -r requirements/ml.txt
python scripts/download_msha_dataset.py
python -m safetyops.ml.nlp.train
python -m safetyops.ml.nlp.evaluate
```

### PPE detection (YOLOv8)

Hard-hat compliance scoring uses the community
[`keremberke/yolov8n-hard-hat-detection`](https://huggingface.co/keremberke/yolov8n-hard-hat-detection)
weights (mAP@0.5 ≈ 0.81 reported by the author on the hard-hat dataset):

```bash
python scripts/download_vision_model.py
export SAFETYOPS_VISION_MODEL_PATH=models/vision/ppe_yolov8n.pt
```

Details and limitations: [models/vision/MODEL_CARD.md](models/vision/MODEL_CARD.md).

### Copilot LLM enhancement (optional)

Incident briefs can be rewritten by any OpenAI-compatible endpoint (Groq free
tier, OpenAI, or local Ollama):

```bash
SAFETYOPS_LLM_BASE_URL=https://api.groq.com/openai
SAFETYOPS_LLM_API_KEY=gsk_...
SAFETYOPS_LLM_MODEL=llama-3.3-70b-versatile
```

Unconfigured or failing LLM calls degrade gracefully to the template report.

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
| `SAFETYOPS_LLM_BASE_URL`        | *(unset)*                                                         | OpenAI-compatible LLM endpoint (Groq/Ollama/...) |
| `SAFETYOPS_LLM_API_KEY`         | *(unset)*                                                         | API key for the LLM endpoint (if required)       |
| `SAFETYOPS_LLM_MODEL`           | *(unset)*                                                         | LLM model name (e.g. `llama-3.3-70b-versatile`)  |
| `SAFETYOPS_OLLAMA_BASE_URL`     | *(unset)*                                                         | Deprecated alias for `SAFETYOPS_LLM_BASE_URL`    |
| `SAFETYOPS_OLLAMA_MODEL`        | *(unset)*                                                         | Deprecated alias for `SAFETYOPS_LLM_MODEL`       |
| `SAFETYOPS_API_KEY`             | *(unset)*                                                         | If set, write endpoints require `X-API-Key`      |
| `SAFETYOPS_RATE_LIMIT_PER_MINUTE` | `0`                                                             | Per-IP write-request limit (0 = disabled)        |
| `SAFETYOPS_NLP_MODEL_HF_REPO`   | *(unset)*                                                         | HF Hub repo to fetch the NLP model from at startup |
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

- For real model inference:
  - Install the heavy ML dependencies: `pip install -r requirements/ml.txt`.
- For CI or constrained environments:
  - The code is written with lazy imports and fallbacks:
    - Failures are logged.
    - Text events fall back to the rule-based classifier; vision events use a stub PPE prediction so the pipeline continues to run.

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