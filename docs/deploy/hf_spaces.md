# Deploying the FastAPI API to Hugging Face Spaces

This guide explains how to deploy the SafetyOps Copilot **FastAPI** service to
a CPU-only **Hugging Face Space**. The UI (Streamlit) can then call this API
from Streamlit Cloud or any other client.

## 1. Create a new Space

1. Go to https://huggingface.co/spaces.
2. Click **Create new Space**.
3. Choose:
   - **Space SDK**: Docker or FastAPI.
   - **Hardware**: CPU basic (free).
4. Name the space, e.g. `your-org/safetyops-api`.

Using the **FastAPI** template is the most straightforward:

- Select **FastAPI** as SDK.
- HF will scaffold a basic FastAPI app that you can replace.

## 2. Add your code

Clone the new Space repository locally:

```bash
git clone https://huggingface.co/spaces/your-org/safetyops-api
cd safetyops-api
```

Copy or add SafetyOps Copilot API code:

- Add the `apps/api/`, `safetyops/`, and `requirements.txt` files.
- Adjust the `main` entrypoint for the Space so that it runs:

  ```python
  from apps.api.main import app
  ```

Ensure `requirements.txt` includes all dependencies already used in the project.

## 3. Configure the Space

In the Space settings (`Settings` tab):

- Set the **App file** to the Python file exposing `app` (e.g. `apps/api/main.py`).
- Ensure `FastAPI` is selected as the SDK.

Hugging Face will automatically install dependencies from `requirements.txt`
and start the FastAPI app.

## 4. Environment variables

Set environment variables under the Space **Settings → Variables**:

Minimal configuration (demo mode):

- `SAFETYOPS_ENV=cloud`
- `SAFETYOPS_LOG_LEVEL=INFO`
- `SAFETYOPS_REDIS_URL` (if using a managed Redis, e.g. Upstash)
- `SAFETYOPS_DATABASE_URL` (managed Postgres, optional if you only demo triage)
- `SAFETYOPS_MLFLOW_TRACKING_URI` (optional)

For the full pipeline, managed Redis and Postgres are recommended. In a
lightweight demo, you can also:

- Stub or disable worker processing.
- Focus on `/copilot/triage` and `/events/text` endpoints.

## 5. Exposed endpoints

Once deployed, the API will expose:

- `/health` — health check.
- `/events/text`, `/events/vision` — ingestion.
- `/events/recent` — recent enriched events.
- `/aggregates/summary` — daily aggregates.
- `/copilot/triage` — multi-agent triage workflow.
- `/monitoring/drift/*` — drift report management.
- `/metrics` — Prometheus metrics (can be scraped by external Prometheus).

The Space URL will look like:

```text
https://your-org-safetyops-api.hf.space
```

Use this as `SAFETYOPS_API_BASE_URL` for the Streamlit UI.

## 6. Connecting from Streamlit UI

In your Streamlit Cloud app settings (for `apps/ui/main.py`):

- Set:

  ```text
  DEPLOY_MODE=cloud
  SAFETYOPS_API_BASE_URL=https://your-org-safetyops-api.hf.space
  ```

- Optionally configure:

  ```text
  SAFETYOPS_OLLAMA_BASE_URL
  SAFETYOPS_OLLAMA_MODEL
  ```

if you have an LLM endpoint accessible from HF Spaces.

## 7. Resource considerations

HF Spaces CPU Basic is sufficient for:

- DistilBERT and YOLOv8n inference on small workloads.
- The triage graph and drift report generation (on small datasets).

To keep things responsive:

- Do not trigger heavy training jobs (`safetyops.ml.nlp.train` or
  `safetyops.ml.vision.train`) inside the Space.
- Use the synthetic dataset and pre-fine-tuned models for demos.

## 8. Summary

- Host the API on HF Spaces (FastAPI).
- Host the UI on Streamlit Cloud.
- Connect them via `SAFETYOPS_API_BASE_URL`.
- Use managed Redis/Postgres if you want full streaming and persistence, or
  stay in a reduced demo mode focusing on triage and analysis.