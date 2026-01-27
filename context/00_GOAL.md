# SafetyOps Copilot — Goal and Scope

## What we are building (v1)

SafetyOps Copilot is a **production-style safety operations assistant** focused on:

- Ingesting **site safety signals**:
  - `vision_event`: images/frames for PPE compliance (person + hardhat/vest).
  - `text_event`: free-text incident descriptions and reports.
- Pushing events into a **real-time Redis Streams bus**.
- Consuming events with a **worker service** that:
  - Runs **vision and text inference** (YOLO for PPE, rule-based text classifier for now).
  - Persists **raw and enriched events** into Postgres.
  - Maintains **simple aggregates** for dashboards.
- Exposing:
  - A **FastAPI service** for ingestion + health + metrics + basic querying.
  - A **Streamlit UI** for live monitoring, demo event production, and triage drafts.
- Integrating basic **monitoring and CI**:
  - `/health` and `/metrics` endpoints.
  - Prometheus scraping.
  - GitHub Actions (ruff + pytest).
  - Notebooks explaining data and modeling decisions.

The system is optimized for:

- **Local-first, free-first** development: everything should work on a laptop with Docker.
- **Clear separation of concerns** (API, worker, UI, shared `safetyops` package).
- **Extensibility** for more advanced ML and ops features in later prompts.

---

## Scope (v1)

Included:

- **Event types**
  - `vision_event` (hardhat/vest/person PPE detection via YOLO wrapper).
  - `text_event` (incident text classification + severity scoring via stub).
- **Streaming**
  - Single Redis Streams bus with consumer group abstraction.
- **Worker**
  - Event consumption loop.
  - Vision inference wrapper (YOLO, lazily imported) with PPE compliance heuristic.
  - Text classification stub (rule-based / baseline).
  - Persistence:
    - `raw_events`
    - `enriched_events`
    - `daily_aggregates`
- **API**
  - `/health`
  - `/metrics`
  - `/events/text`
  - `/events/vision`
  - `/events/recent`
  - `/aggregates/summary`
  - Structured logging with correlation IDs.
  - Centralized exception handling.
- **UI**
  - Tabs for:
    - Live feed of enriched events.
    - Incident triage (text input + latest triage view).
    - Ops dashboard with aggregates and simple charts.
  - Buttons to produce demo events.
- **Infra**
  - `docker-compose.local.yml` for:
    - Postgres
    - Redis
    - MLflow
    - Prometheus
    - Grafana (optional, minimal)
  - Prometheus config pointing at API metrics.
- **Notebooks**
  - Text EDA and modeling plan.
  - Vision EDA and evaluation plan.
  - End-to-end architecture and flow walkthrough.

---

## Non-goals (v1)

These are **explicitly out of scope** for Prompt 1 / initial implementation:

- **Production reliability features**
  - Horizontal scaling, HA Redis/Postgres clusters.
  - Full observability stack (logs/metrics/traces across environments).
  - Blue/green or canary deployments.
- **Advanced ML**
  - Training custom YOLO models or transformers.
  - LLM-based text triage (kept as a non-LLM stub for now).
  - Online learning or model drift adaptation.
- **Security & auth**
  - Authentication/authorization for API and UI.
  - Fine-grained RBAC and multi-tenant design.
- **Data governance**
  - Full audit trails and access policies.
  - Pseudonymization/anonymization of sensitive data.
- **Complex orchestration**
  - Kubernetes manifests, Helm charts, or multi-region deployments.
  - Integration with external data lakes or warehouses.

---

## Principles

- **Dogfooding for applied ML MLOps**
  - The project should feel like a realistic small production system.
  - Clear seams between components (API / worker / UI / infra).
- **Clarity over cleverness**
  - Simple, explicit data models.
  - Lightweight heuristics and stubs where full solutions would be complex.
- **Safety and ethics**
  - All data artifacts in the repo are **synthetic or anonymized**.
  - Clear documentation about limitations and assumptions.
- **AI-grounded workflow**
  - Future AI agents must read `context/*` before making changes.
  - Architectural decisions are captured in `03_DECISIONS_LOG.md`.