# 07 – Free Deploy Guide (SafetyOps Copilot)

This guide explains how to deploy SafetyOps Copilot on free tiers, with two main options:

- **Option 1 (simplest):** Deploy only the **Streamlit UI** in a single-process demo mode.
- **Option 2 (more realistic):** Deploy the **API** and **UI** separately, with managed Redis and Postgres.

The goal is to keep deployments easy, cheap (or free), and aligned with the existing code.

---

## A. Deployment Options

### Option 1 – Streamlit UI only (single-process demo)

**Best for:** quick demo, minimal infra, no external DB/Redis.

Approach:

- Deploy `apps/ui/main.py` to **Streamlit Community Cloud**.
- Run API-like operations **inside the same Streamlit process** or call a lightweight local API.
- Use **SQLite** for storage (via `SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db`).
- Optionally skip Redis and background worker entirely, relying on in-process logic.

Current repo:

- The UI is written to call a separate API over HTTP (`SAFETYOPS_API_BASE_URL`).
- For a pure single-process mode, you could:
  - Add a special `DEPLOY_MODE=single_process` branch in the UI that imports and calls core services directly.
  - Or run a lightweight FastAPI app inside the same process.
- This is not fully wired yet, but the **recommended path** is to:
  - Start with **Option 2** (API + UI) for clarity, or
  - Use this guide’s notes to evolve the project into a single-process mode later.

### Option 2 – API + UI + managed services (recommended)

**Best for:** a realistic architecture on free tiers.

Suggested stack:

- **API:** FastAPI app on **Hugging Face Spaces** (or similar).
- **UI:** Streamlit app on **Streamlit Community Cloud**.
- **Redis:** Upstash Redis (or another free hosted Redis).
- **Database:**
  - Prefer a free Postgres (e.g. Neon, Supabase), **or**
  - Use SQLite (`SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db`) knowing that storage is ephemeral on most free platforms.
- **Worker:** optional for a demo; for full streaming behavior, deploy it as:
  - A cron-like job (GitHub Actions / HF Space background process), or
  - A long-running process (HF Space with a worker entrypoint).

The rest of this guide assumes **Option 2**.

---

## B. Deploying the UI (Streamlit Community Cloud)

### B.1 Connect the GitHub repo

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. Click **New app**.
3. Select your fork or repo (e.g. `your-user/safetyops-copilot`).
4. Set:
   - **Branch:** the branch you are using (e.g. `main`).
   - **Main file:** `apps/ui/main.py`.

Streamlit will build and run the app using `requirements.txt`.

### B.2 Configure environment variables (secrets)

In your Streamlit app settings (Manage App → Settings → Secrets), set:

```toml
SAFETYOPS_API_BASE_URL = "https://<your-api-host>/"
SAFETYOPS_DEPLOY_MODE = "cloud"

# Optional, depending on how you deploy:
SAFETYOPS_REDIS_URL = "rediss://:<UPSTASH_PASSWORD>@<UPSTASH_HOST>:<PORT>"
SAFETYOPS_DATABASE_URL = "postgresql+psycopg2://user:password@host:port/dbname"
# or, for a simple demo:
# SAFETYOPS_DATABASE_URL = "sqlite:///./safetyops.db"
```

Notes:

- `SAFETYOPS_API_BASE_URL` must point to your deployed API (see Option 2/API section).
- You do **not** need to run Redis/Postgres directly from Streamlit; you only need the URL config if your UI talks to them indirectly via the API.
- If you only want Copilot triage without full streaming, you can:
  - Point the UI’s API base at a lightweight FastAPI Space that doesn’t depend on Redis.

### B.3 Test the UI deployment

Once Streamlit builds:

1. Open the app URL provided by Streamlit.
2. Ensure the **System Status** panel shows:
   - API = ✅ (or at least reachable).
3. Try:
   - Submitting an incident in **Incident Triage**.
   - Calling **Copilot Chat**.

If you see errors like “Failed to fetch recent events”, confirm:

- `SAFETYOPS_API_BASE_URL` is correct.
- The API deployment is up and responds on `/health` and `/system/status`.

---

## C. Deploying the API (Hugging Face Spaces)

### C.1 Choose Space type

Go to <https://huggingface.co/spaces> and create a new Space:

- **Space type:** `Docker` or `Python`.
  - **Python Space** is simpler if you rely on `requirements.txt`.
  - **Docker Space** gives more control but requires a `Dockerfile`.

For this project, a **Python Space** is sufficient.

### C.2 Files needed

Ensure the repo has:

- `requirements.txt` – already present and used by CI.
- `apps/api/main.py` – FastAPI app with `app = FastAPI(...)`.

HF Spaces will install dependencies from `requirements.txt` by default.

### C.3 Entry point

For a Python Space, set:

- **SDK:** `fastapi`
- **Python file path:** `apps/api/main.py`
- **App variable:** `app`

This tells Hugging Face to run:

```python
from apps.api.main import app
```

### C.4 Environment variables in Space settings

In the Space’s **Settings → Variables and secrets**:

Set, at minimum:

```text
SAFETYOPS_ENV = cloud
SAFETYOPS_DEPLOY_MODE = cloud

# Database – choose one:
SAFETYOPS_DATABASE_URL = postgresql+psycopg2://user:password@host:5432/dbname
# or:
# SAFETYOPS_DATABASE_URL = sqlite:///./safetyops.db

# Redis (optional, but required for full streaming/worker flows):
SAFETYOPS_REDIS_URL = rediss://:<UPSTASH_PASSWORD>@<UPSTASH_HOST>:<PORT>
SAFETYOPS_STREAM_KEY = safetyops:events
SAFETYOPS_CONSUMER_GROUP = safetyops-workers
SAFETYOPS_CONSUMER_NAME = worker-1
SAFETYOPS_DLQ_STREAM_KEY = safetyops:events:dlq

SAFETYOPS_ARTIFACTS_DIR = artifacts
SAFETYOPS_NLP_MODEL_DIR = models/nlp
SAFETYOPS_VISION_MODEL_PATH = yolov8n.pt
SAFETYOPS_METRICS_NAMESPACE = safetyops
```

For a free, minimal demo, you can:

- Use **SQLite** (`sqlite:///./safetyops.db`) as the DB.
- Skip Redis and any routes that depend on streaming, or rely on the stubbed behavior.

### C.5 Health check

Once the Space builds:

1. Visit the Space URL (e.g. `https://<user>-safetyops-api.hf.space`).
2. Check `/health`:

   - `https://<user>-safetyops-api.hf.space/health`

You should get:

```json
{"status": "ok", "version": "0.1.0"}
```

3. Check `/system/status`:

   - Confirms database and Redis availability.

---

## D. Cloud Environment Variables (Summary)

The table below lists the key environment variables used in cloud deployments.

| Variable                  | Purpose                                           | Typical cloud value / note                                  |
|---------------------------|---------------------------------------------------|-------------------------------------------------------------|
| `SAFETYOPS_API_BASE_URL` | Base URL for API used by the UI                  | Streamlit: `https://<user>-safetyops-api.hf.space`         |
| `SAFETYOPS_DEPLOY_MODE`  | `local` vs `cloud` behavior hints                | `cloud`                                                     |
| `SAFETYOPS_ENV`          | Environment name (`local`, `cloud`, `staging`)   | `cloud` or `prod`                                          |
| `SAFETYOPS_REDIS_URL`    | Redis connection URL                             | Upstash or other managed Redis URL                         |
| `SAFETYOPS_DATABASE_URL` | SQLAlchemy DB URL                                 | Neon/Supabase Postgres URL or `sqlite:///./safetyops.db`   |
| `SAFETYOPS_STREAM_KEY`   | Redis Stream key for events                      | `safetyops:events`                                         |
| `SAFETYOPS_CONSUMER_GROUP` | Redis consumer group name                      | `safetyops-workers`                                        |
| `SAFETYOPS_CONSUMER_NAME` | Redis consumer name                             | `worker-1`                                                 |
| `SAFETYOPS_DLQ_STREAM_KEY` | DLQ Redis Stream key                           | `safetyops:events:dlq`                                     |
| `SAFETYOPS_ARTIFACTS_DIR` | Local path for artifacts (drift reports, etc.) | `artifacts` (ensure the path is writable in the platform)  |
| `SAFETYOPS_NLP_MODEL_DIR` | NLP model directory                             | `models/nlp` or similar                                    |
| `SAFETYOPS_VISION_MODEL_PATH` | YOLO weights path                         | `yolov8n.pt` (must be accessible to the runtime)           |
| `SAFETYOPS_METRICS_NAMESPACE` | Prefix for metrics                          | `safetyops`                                                |

> For Streamlit Cloud and HF Spaces, remember that the filesystem can be **ephemeral**. Use SQLite only for demos; serious deployments should use managed Postgres.

---

## E. Free-Tier-Friendly Notes

### E.1 Ephemeral storage

- HF Spaces and Streamlit Community Cloud often provide ephemeral disk.
- Do **not** rely on local files for:
  - Long-term drift reports.
  - Large model weights.
- For demos:
  - It’s acceptable to generate reports in a local `artifacts` directory.
  - But expect them to be lost if the container restarts.

### E.2 Models and inference

- The project defaults to **YOLOv8n** (`yolov8n.pt`) and a lightweight DistilBERT model.
- To keep deployments light:
  - Avoid training in the cloud.
  - Prefer **lazy loading** (already implemented) and fallbacks:
    - If YOLO fails to load, the code logs a warning and uses stub PPE predictions.
    - This keeps tests and demos fast on CPU-only machines.

### E.3 Optional components

For free-tier demos, you can safely **skip**:

- Prometheus
- Grafana
- MLflow

They are useful locally (via Docker Compose) but rarely needed in a small cloud demo. You can:

- Only deploy API + UI.
- Turn off drift report generation if Evidently or heavy dependencies are problematic.

---

## F. Post-Deploy Checklist

### F.1 Verify API

On your API host (HF Spaces or similar):

1. Check `/health`:

   ```text
   https://<your-api-host>/health
   ```

2. Check `/system/status` for:
   - `database_ok` and `redis_ok` if you configured them.
   - Worker heartbeat is optional; it requires a deployed worker process.

### F.2 Verify UI

On Streamlit Community Cloud:

1. Open the app.
2. Confirm:

   - System Status can reach the API (`API` indicator is ✅).
   - No hard errors on startup.

3. In **Incident Triage**:
   - Submit a sample description.
   - Confirm that a triage result and markdown brief appear.

### F.3 Run a demo flow

If you have Redis + worker deployed:

1. Trigger demo events:
   - Via the UI (Live Feed → “Produce demo events”), or
   - Via a one-off script/cron hitting the API `/events/text` and `/events/vision`.

2. Ensure the worker is running and connected to the same Redis and DB.

3. In the UI:

   - Live Feed should show enriched events.
   - Ops Dashboard should display aggregates.
   - Monitoring tab can surface drift reports and metrics if enabled.

If you do **not** deploy the worker:

- Focus on text-only Copilot triage and API endpoints that don’t require streaming.

---

## G. Where to Evolve Next

Once you have a working free-tier deployment:

- Consider adding:
  - A `DEPLOY_MODE=single_process` path for Streamlit-only deployments (no external API).
  - Background tasks in HF Spaces for the worker loop.
  - Persisting drift reports and metrics to cloud object storage (e.g. S3-compatible buckets).

Keep any changes aligned with the existing `context/` docs and update:

- `context/03_DECISIONS_LOG.md` for new architectural decisions.
- `context/05_ROADMAP.md` as you expand capabilities.