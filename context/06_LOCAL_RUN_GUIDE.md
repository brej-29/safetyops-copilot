# 06 – Local Run Guide (SafetyOps Copilot)

This guide walks you through running the full SafetyOps Copilot stack locally on macOS, Linux, and Windows. It mirrors the actual code, Makefile targets, and Docker Compose configuration in this repo.

---

## 1. Overview

### What runs locally

Using the local stack you can run:

- **FastAPI API** (`apps/api/main.py`)
  - Ingests text and vision events
  - Exposes `/health`, `/metrics`, `/events/*`, `/copilot/triage`, `/system/status`
- **Worker service** (`services/worker/run.py`)
  - Consumes events from Redis Streams
  - Runs NLP + vision inference
  - Persists events and aggregates to the database
- **Streamlit UI** (`apps/ui/main.py`)
  - Live feed of enriched events
  - Incident triage and Copilot chat
  - Ops dashboard and monitoring
  - System Status panel (API/DB/Redis/worker heartbeat)
- **Infra services (via Docker Compose)**
  - Postgres (local DB)
  - Redis (stream + DLQ)
  - MLflow server
  - Prometheus
  - Grafana

### Ports (defaults)

- API (FastAPI): `http://localhost:8000`
- UI (Streamlit): `http://localhost:8501`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`
- MLflow: `http://localhost:5000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

### When everything is working

You should be able to:

- Open the UI at `http://localhost:8501`
- See green system status (API, DB, Redis, worker heartbeat)
- Produce demo events and watch them appear in the live feed
- Call Copilot triage and get a markdown incident brief

---

## 2. Prerequisites

### Required

- **Git**
  - Any recent version is fine.
- **Python 3.10+**
  - Recommended: Python **3.10–3.11**.
- **pip**
  - Comes with Python, or install via your OS package manager.
- **Docker Desktop or Docker Engine**
  - Used for Postgres, Redis, MLflow, Prometheus, Grafana.
  - Ensure `docker` and `docker compose` work from your shell.

### Optional but recommended

- **make**
  - macOS: `brew install make`
  - Ubuntu/Debian: `sudo apt-get install make`
  - Windows: via WSL2 (recommended) or Git Bash (optional).
- **VS Code** (or any IDE)
- **WSL2** (Windows)
  - Strongly recommended for a smoother Docker + Python experience.

---

## 3. Setup Steps (all platforms)

### 3.1 Clone the repository

```bash
git clone <your-fork-or-origin> safetyops-copilot
cd safetyops-copilot
```

### 3.2 Create a virtual environment

#### macOS / Linux (bash/zsh)

```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> If `python` maps to Python 2 on your system, use `python3` instead.

### 3.3 Install dependencies

With **make**:

```bash
make install
```

Without **make**:

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 3.4 Create `.env` from `.env.example`

```bash
cp .env.example .env
```

The defaults in `.env.example` are aligned with `infra/docker-compose.local.yml`:

- Postgres at `postgresql+psycopg2://safetyops:safetyops@localhost:5432/safetyops`
- Redis at `redis://localhost:6379`
- API base URL for UI at `http://localhost:8000`

For a **quick demo without Docker/Postgres**, you can instead set in `.env`:

```bash
SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db
```

> SQLite is fine for local experimentation but not for production.

---

## 4. Run Using Makefile (Recommended)

The Makefile exposes common commands. You can list them with:

```bash
make help
```

You should see targets like `install`, `up`, `down`, `api`, `worker`, `ui`, `lint`, `fmt`, `test`, `seed`, `produce-demo`.

### 4.1 Start infra (Postgres, Redis, MLflow, Prometheus, Grafana)

```bash
make up
```

This runs `docker compose -f infra/docker-compose.local.yml up -d` and starts:

- Postgres (`localhost:5432`)
- Redis (`localhost:6379`)
- API container (if you choose to run inside Docker)
- Worker container
- UI container
- MLflow (`localhost:5000`)
- Prometheus (`localhost:9090`)
- Grafana (`localhost:3000`)

### 4.2 Run API locally (host machine)

In a **new terminal** with the venv activated:

```bash
make api
# Equivalent:
# uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output: Uvicorn logs with `Started server process` and `Application startup complete.`

### 4.3 Run worker locally

In another terminal:

```bash
make worker
# Equivalent:
# python -m services.worker.run
```

Expected output: log line similar to:

```text
Starting SafetyOps worker {"env": "local", "stream_key": "safetyops:events", ...}
```

### 4.4 Run UI (Streamlit)

In another terminal:

```bash
make ui
# Equivalent:
# streamlit run apps/ui/main.py --server.port 8501
```

Then open: <http://localhost:8501>

You should see:

- The SafetyOps Copilot title.
- Tabs: Live Feed, Incident Triage, Copilot Chat, Ops Dashboard, Monitoring.
- A **System Status** panel in the Live Feed tab.

### 4.5 Seed demo data

With Postgres running (via `make up`) and the API/worker configured to talk to it:

```bash
make seed
# Equivalent:
# python scripts/seed_demo_data.py
```

This seeds a handful of demo text incidents and aggregates into the database.

### 4.6 Produce demo events

To push additional demo events through Redis Streams:

```bash
make produce-demo
# Equivalent:
# python scripts/produce_demo_events.py
```

You can also produce demo events from within the UI (Live Feed tab).

### 4.7 Lint and tests

Run Ruff lint:

```bash
make lint
# or:
ruff check .
```

Auto-fix lint issues where possible:

```bash
make fmt
# or:
ruff check --fix .
```

Run tests:

```bash
make test
# or:
pytest
```

CI runs `ruff check .` and `pytest` using `requirements-dev.txt`.

---

## 5. Run WITHOUT Make (bash + PowerShell)

If `make` is not available, you can run everything with Docker + Python commands.

### 5.1 Docker Compose (infra)

#### macOS / Linux (bash/zsh)

Start infra:

```bash
docker compose -f infra/docker-compose.local.yml up -d
```

Stop infra:

```bash
docker compose -f infra/docker-compose.local.yml down
```

#### Windows (PowerShell)

Start infra:

```powershell
docker compose -f infra/docker-compose.local.yml up -d
```

Stop infra:

```powershell
docker compose -f infra/docker-compose.local.yml down
```

> Make sure Docker Desktop is running before you run these commands.

### 5.2 Python services (host machine)

Assuming your venv is active and dependencies installed:

#### API (FastAPI)

macOS / Linux:

```bash
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell:

```powershell
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Worker

macOS / Linux:

```bash
python -m services.worker.run
```

Windows PowerShell:

```powershell
python -m services.worker.run
```

#### UI (Streamlit)

macOS / Linux:

```bash
streamlit run apps/ui/main.py --server.port 8501
```

Windows PowerShell:

```powershell
streamlit run apps/ui/main.py --server.port 8501
```

---

## 6. How to Verify Everything

### 6.1 API health

Once the API is running:

- Health check: <http://localhost:8000/health>

Expected response:

```json
{"status": "ok", "version": "0.1.0"}
```

- OpenAPI docs: <http://localhost:8000/docs>

### 6.2 System status

In the UI (Live Feed tab):

- The **System Status** panel should show:
  - ✅ API
  - ✅ Database (if DB is reachable)
  - ✅ Redis (if Redis is reachable)
  - Worker heartbeat timestamp and age (seconds) if the worker is running.

You can also call the system status endpoint directly:

- <http://localhost:8000/system/status>

### 6.3 UI

Open:

- <http://localhost:8501>

You should see:

- Live Feed with an empty table initially.
- Buttons to produce demo events and refresh.
- System Status section.

### 6.4 MLflow, Prometheus, Grafana

If you started infra via Docker Compose:

- MLflow: <http://localhost:5000>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>

These are optional for basic demos; you can ignore them if you are only interested in ingestion + triage.

### 6.5 Basic “happy path” demo

1. Ensure infra is up (`make up` or docker compose up).
2. Run API, worker, and UI (locally or via the containers).
3. Open the UI at <http://localhost:8501>.
4. In the **Live Feed** tab:
   - Click **Produce demo events** (or run `make produce-demo` in a terminal).
   - Wait a few seconds; the Live Feed auto-refreshes.
   - You should see enriched events appear.
5. In the **Incident Triage** or **Copilot Chat** tabs:
   - Submit a description (e.g. “Worker slipped on wet floor near loading bay.”).
   - You should see a triaged response and a markdown incident brief.

---

## 7. Troubleshooting

### Ports already in use

Symptoms:

- Docker or Uvicorn complains that a port is already in use (e.g. 8000, 5432, 6379).

What to do:

- Check which process is using the port:
  - macOS / Linux:

    ```bash
    lsof -i :8000
    ```

  - Windows PowerShell:

    ```powershell
    netstat -ano | Select-String 8000
    ```

- Stop the conflicting process or change the port in your command/env.

### Docker not running

Symptoms:

- `docker compose ...` fails with connection errors.
- Infra containers do not start.

What to do:

- Ensure Docker Desktop is running.
- On Linux, ensure your user can run Docker commands or use `sudo`:

  ```bash
  sudo docker compose -f infra/docker-compose.local.yml up -d
  ```

### Redis/Postgres connection errors

Symptoms:

- API or worker logs mention inability to connect to Redis or Postgres.
- `scripts/doctor.py` reports failures.

What to do:

1. Run the doctor:

   ```bash
   python scripts/doctor.py
   ```

2. Ensure infra is running:

   ```bash
   docker compose -f infra/docker-compose.local.yml ps
   ```

3. Check `.env`:

   - `SAFETYOPS_REDIS_URL` should usually be `redis://localhost:6379`.
   - `SAFETYOPS_DATABASE_URL` should match the Docker Compose Postgres service:

     ```text
     postgresql+psycopg2://safetyops:safetyops@localhost:5432/safetyops
     ```

   - For a Docker-free demo, set:

     ```text
     SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db
     ```

### YOLO / torch not found

Symptoms:

- Import errors around `ultralytics` or `torch` when running worker or experiments.

What to do:

- For full vision inference:

  ```bash
  pip install -r requirements.txt
  ```

- In CI or constrained environments:
  - The worker and tests use lazy imports and a **stub PPE inference** if YOLO cannot load.
  - This means tests and API can still run without downloading large model weights.

### Streamlit cannot reach the API

Symptoms:

- UI shows errors like “Failed to fetch recent events” or “System status check failed”.

What to do:

- Ensure the API is running:

  ```bash
  curl http://localhost:8000/health
  ```

- Check `SAFETYOPS_API_BASE_URL` in `.env`:
  - For local runs: `SAFETYOPS_API_BASE_URL=http://localhost:8000`.
  - If UI is running in Docker and API on host, you may need to adjust the host/IP.

### Windows-specific notes

- Use PowerShell (or VS Code’s integrated terminal) for commands.
- Activate the venv with:

  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

- If execution policy blocks scripts:

  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- Be mindful of path separators when editing `.env` or config (Windows can still use `sqlite:///./safetyops.db` URLs normally).

---

## 8. Next Steps

Once you are comfortable with the local setup:

- Explore the architecture docs in `context/01_ARCHITECTURE.md`.
- Review the decisions in `context/03_DECISIONS_LOG.md`.
- When ready to deploy on free tiers, see `context/07_FREE_DEPLOY_GUIDE.md`.