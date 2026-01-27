# Deploying SafetyOps Copilot UI to Streamlit Cloud

This guide explains how to deploy the **Streamlit UI** (`apps/ui/main.py`) to
Streamlit Community Cloud in a lightweight, free-friendly way.

The focus is on:

- Keeping the deployment simple.
- Avoiding heavy local services (Postgres, Redis, MLflow).
- Still demonstrating the Copilot triage workflow.

## 1. Prepare your repository

1. Push your SafetyOps Copilot repository to GitHub.
2. Ensure the `apps/ui/main.py` entrypoint is present in the repo.
3. Commit `requirements.txt` so Streamlit Cloud can install dependencies.

## 2. Create a new Streamlit Cloud app

1. Go to https://streamlit.io/cloud and sign in with GitHub.
2. Click **New app**.
3. Select the repo and branch containing SafetyOps Copilot.
4. Set the **main file path** to:

   ```text
   apps/ui/main.py
   ```

5. Click **Deploy**.

Streamlit Cloud will build the app using `requirements.txt`.

## 3. Configure environment variables

In the Streamlit Cloud app settings, define the following environment variables:

### Minimal "cloud" mode (no external API)

In this mode, the UI runs as a **standalone demo**. It does not require the
FastAPI API, Postgres, or Redis. Features are limited, but Copilot Chat will
still work against local Python logic.

Set:

- `DEPLOY_MODE=cloud`

Optional:

- `SAFETYOPS_OLLAMA_BASE_URL` and `SAFETYOPS_OLLAMA_MODEL` if you have a
  network-accessible Ollama instance and want LLM enhancement of reports
  (often left unset for free deployments).

With `DEPLOY_MODE=cloud`:

- The **Live Feed** and **Ops Dashboard** tabs will not show real-time data
  unless you also deploy the API somewhere and point the UI at it.
- The **Copilot Chat** tab can still work by calling the `/copilot/triage`
  endpoint if `SAFETYOPS_API_BASE_URL` is configured (see below).

### Using a remote API (recommended for richer demos)

For a richer experience, deploy the FastAPI API (for example on **Hugging Face
Spaces** or another host) and point the Streamlit UI at it.

Set:

- `DEPLOY_MODE=cloud`
- `SAFETYOPS_API_BASE_URL=https://your-api-host` (e.g. HF Space URL)

In this configuration:

- The UI will call the remote API for:
  - `/events/text`, `/events/vision`
  - `/events/recent`
  - `/aggregates/summary`
  - `/copilot/triage`
  - `/monitoring/drift/*`
  - `/metrics`
- The remote API instance is responsible for connecting to Redis/Postgres.

## 4. Optional: connect to managed Redis / Postgres

If you want the full pipeline in a free/cloud setting:

- Use a managed Redis service such as **Upstash**.
- Use a managed Postgres database (e.g. Railway, Render free tier, Supabase).

Configure environment variables on the **API** deployment (not required in
Streamlit UI-only mode):

- `SAFETYOPS_REDIS_URL` pointing to Upstash (or other managed Redis).
- `SAFETYOPS_DATABASE_URL` pointing to the managed Postgres.
- `SAFETYOPS_MLFLOW_TRACKING_URI` (optional) if you run MLflow elsewhere.

The Streamlit UI itself does not need direct DB/Redis access; it only talks to
the API.

## 5. Resource considerations

Streamlit Cloud free tier is CPU-only and memory-limited. To keep things
responsive:

- Avoid running heavy training jobs in the UI.
- Keep batch sizes and dataset sizes small for demos.
- Rely on:
  - Synthetic text data via `scripts/download_text_dataset.py`.
  - Pretrained models (DistilBERT and YOLOv8n) for inference.

## 6. Verifying the deployment

Once deployed:

1. Visit the Streamlit app URL.
2. Verify that:
   - **Live Feed** tab loads (may show limited data in cloud-only mode).
   - **Incident Triage** can submit incidents if API is connected.
   - **Copilot Chat** returns structured JSON and a markdown report.
   - **Monitoring** tab can fetch metrics/drift if the API exposes them.

If you see connection errors:

- Check `SAFETYOPS_API_BASE_URL` and ensure the API is reachable.
- Validate that CORS settings on the API (if modified) allow access from
  Streamlit Cloud.

## 7. Summary of key env vars

For Streamlit Cloud:

- `DEPLOY_MODE=cloud`
- `SAFETYOPS_API_BASE_URL` (optional but recommended for full features)
- `SAFETYOPS_OLLAMA_BASE_URL` / `SAFETYOPS_OLLAMA_MODEL` (optional LLM)

The backend (API) can be deployed separately with its own `.env` and may use
managed Redis/Postgres for a fully hosted experience.