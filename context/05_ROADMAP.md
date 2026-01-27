# Roadmap — SafetyOps Copilot

This roadmap tracks major milestones for SafetyOps Copilot.

---

## Phase 1 — Foundational Pipeline (complete)

**Goal:** Stand up a realistic but lightweight real-time safety monitoring pipeline with clear extension points.

- [x] Define project structure and shared package (`safetyops`).
- [x] Implement FastAPI API for event ingestion, health, metrics, and basic querying.
- [x] Implement Redis Streams event bus and worker service for enrichment.
- [x] Integrate YOLO-based vision PPE stub and rule-based NLP classifier.
- [x] Persist raw/enriched events and daily aggregates in Postgres.
- [x] Add Streamlit UI with Live Feed, Incident Triage, and Ops Dashboard.
- [x] Add Prometheus metrics and basic Grafana placeholders.
- [x] Provide Docker Compose for local infra (Postgres, Redis, MLflow, Prometheus, Grafana).
- [x] Add tests for event models, streaming, and enrichment.
- [x] Document architecture, decisions, and local run commands.

---

## Phase 2 — ML & AI Copilot Enhancements (this prompt)

**Goal:** Turn the pipeline into a more capable Copilot with real models, richer monitoring, and multi-agent workflows.

- [x] NLP fine-tuning pipeline (DistilBERT) with MLflow tracking and local model registry.
- [x] Real YOLOv8 PPE inference wrapper and optional GPU training script + Colab guide.
- [x] Multi-step triage workflow with DB context, risk scoring, runbook retrieval, and optional LLM enhancement.
- [x] Expanded Prometheus metrics and Evidently-based drift reports.
- [x] Stronger Streamlit UI:
  - [x] Live stream view with auto-refresh.
  - [x] Copilot Chat tab for triage interaction.
  - [x] Monitoring tab for drift and metrics summary.
- [x] MLOps polish:
  - [x] DVC `dvc.yaml` with stages for data download and training.
  - [x] Clear MLflow integration in the NLP training pipeline.
- [x] Deployment guides for free tiers (Streamlit Cloud, HF Spaces) and `DEPLOY_MODE` switch.

---

## Phase 3 — Future Enhancements (future prompts)

Potential next steps (not yet implemented):

- [ ] Replace synthetic NLP data with curated, de-identified real datasets.
- [ ] Introduce more sophisticated triage graphs (full LangGraph agents, tools, and memory).
- [ ] Add per-site, per-line, or per-task analytics in the dashboard.
- [ ] Deeper integration with external ticketing/incident systems.
- [ ] Automated regression suites for ML models (data slices, fairness, calibration).
- [ ] Production-ready deployment templates for specific platforms (Kubernetes, serverless, etc.).oadmap — SafetyOps Copilot

This roadmap is split into:

- **Prompt 1 (current)** — foundational system.
- **Prompt 2 and beyond** — extensions and production-hardening.

---

## 1. Prompt 1 — Foundations (this implementation)

### Core deliverables

- Repo structure:
  - `context/`, `apps/`, `services/`, `safetyops/`, `infra/`, `notebooks/`, `scripts/`, `data/`.
- Dependencies and tooling:
  - `requirements.txt`, `requirements-dev.txt`.
  - `ruff` + basic lint config.
  - `pytest` and lightweight unit tests.
- Infra:
  - `infra/docker-compose.local.yml` with:
    - Postgres
    - Redis
    - MLflow
    - Prometheus
    - Grafana (minimal)
- API (FastAPI, `apps/api`):
  - `/health`, `/metrics`
  - `/events/text`, `/events/vision`
  - `/events/recent`, `/aggregates/summary`
  - Structured logging, correlation IDs, exception handlers.
- Worker (`services/worker`):
  - Redis Streams consumer using `BaseEventBus`.
  - YOLO PPE wrapper (lazy) + rule-based text classifier.
  - Persistence to Postgres (`raw_events`, `enriched_events`, `daily_aggregates`).
  - Prometheus metrics.
- UI (Streamlit, `apps/ui`):
  - Tabs: Live Feed, Incident Triage, Ops Dashboard.
  - Demo event generation.
- Notebooks:
  - `00_text_eda.ipynb`
  - `01_vision_eda.ipynb`
  - `02_end_to_end_walkthrough.ipynb`
- CI:
  - GitHub Actions workflow:
    - Install dependencies.
    - Run ruff.
    - Run pytest.

---

## 2. Prompt 2 — Enhancements (planned)

**High-level ideas (can be refined later):**

### 2.1 ML and Modeling

- **Text**
  - Replace rule-based classifier with:
    - Lightweight transformer (e.g., DistilBERT) fine-tuned on incident data.
  - Add calibration and confidence-aware thresholds.
  - Introduce explainability (LIME/SHAP/IG) hooks.

- **Vision**
  - Curate a small PPE dataset.
  - Fine-tune YOLO on PPE-specific labels.
  - Add better heuristics for multi-person scenes.
  - Integrate model performance metrics into MLflow.

### 2.2 Monitoring and Ops

- Expand Prometheus metrics:
  - Error rate, latency percentiles, queue/backlog depth.
- Add basic alerting rules (Prometheus) and dashboards (Grafana).
- Pipe selected metrics to Ops Dashboard in Streamlit.

### 2.3 Data and Storage

- Introduce soft deletion and retention policies for events.
- Add richer schemas:
  - Site/location metadata.
  - Operator annotations and feedback loop for labels.
- Consider read models / materialized views to serve dashboards.

### 2.4 Workflow Integration

- Webhook or event integrations with:
  - Slack/Teams for incident notifications.
  - Ticketing tools (e.g., Jira) for high-severity alerts.
- Simple RBAC or API keys for ingestion endpoints.

---

## 3. Later Phases — Production Hardening

Ideas for beyond Prompt 2:

- **Scalability**
  - Containerization of API/UI/worker.
  - Horizontal scaling of worker processes (multiple consumer instances).
  - Evaluation of managed Redis/Postgres offerings.

- **Resilience**
  - Retries with backoff for transient errors (Redis/Postgres).
  - Dead-letter stream or table for failed events.
  - Graceful shutdown with in-flight work completion.

- **Security and Compliance**
  - Authentication on API and UI.
  - Audit logs and more detailed traceability.
  - Data anonymization and compliance controls.

- **Advanced Analytics**
  - Drift detection for text and vision models.
  - Risk scoring across sites and time windows.
  - Integration with BI tools.

---

## 4. How to Use this Roadmap

When starting a new task:

1. Verify whether it fits under **Prompt 1** (foundational), **Prompt 2** (enhancement), or later.
2. If you introduce a feature beyond current scope:
   - Document it here, updating or adding bullets.
   - Add an ADR entry in `context/03_DECISIONS_LOG.md` if architectural.
3. Keep the roadmap **living but concise**:
   - Remove items when fully delivered.
   - Add concrete subtasks only when they are planned or in progress.