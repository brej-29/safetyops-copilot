# Decisions Log (ADR-style) — SafetyOps Copilot

This file captures **architectural decisions** and their rationale.  
Future changes that materially alter behavior or architecture should **append** entries here.

---

## ADR-0001: Use Redis Streams as Event Bus

- **Status**: Accepted
- **Context**:
  - We need a simple, lightweight, real-time event stream for two event types (`vision_event`, `text_event`).
  - Local development and free-tier deployment are core constraints.
- **Decision**:
  - Use **Redis Streams** as the primary event bus.
  - Implement a small abstraction layer:
    - `BaseEventBus` interface
    - `RedisStreamsEventBus` implementation using `XADD` and `XREADGROUP`.
- **Consequences**:
  - Easy to run locally via Docker (`redis:alpine`).
  - Supports consumer groups and backpressure.
  - Tightly couples us to Redis semantics; switching to Kafka/NATS/RabbitMQ would require an additional adapter implementation but not API surface changes.

---

## ADR-0002: Use YOLO (ultralytics) for PPE Detection

- **Status**: Accepted
- **Context**:
  - We need a reasonable default for PPE detection (person + hardhat/vest).
  - The project is **demo/ops-focused**, not research-heavy.
- **Decision**:
  - Use **ultralytics YOLO**, defaulting to pre-trained `yolov8n`.
  - Wrap model loading and inference in `safetyops.ml.vision.yolo` with:
    - **Lazy imports** for `ultralytics` and `torch`.
    - A **stub fallback** if heavy dependencies are unavailable (e.g. CI, constrained machines).
- **Consequences**:
  - Out-of-the-box decent detection quality.
  - Heavy dependencies may slow installs on some environments; mitigated via lazy imports and tests that avoid importing YOLO directly.
  - Future: swap in custom-trained PPE models or different detectors behind the same interface.

---

## ADR-0003: Rule-based NLP Classifier (Stub)

- **Status**: Accepted
- **Context**:
  - We need to triage text incident reports into:
    - Categories (`fall`, `electrical`, `fire`, `chemical`, `other`).
    - Severity (`low`, `medium`, `high`).
  - Prompt 1 does not require a full ML model.
- **Decision**:
  - Implement a **rule-based classifier** in `safetyops.ml.nlp.classifier`.
  - Use simple keyword-based rules and deterministic scoring.
- **Consequences**:
  - Fully deterministic and testable.
  - Clearly documented baseline that can be replaced by a transformer/ML pipeline later.
  - Avoids dependency complexity for now while still giving realistic outputs.

---

## ADR-0004: Postgres as Primary Storage

- **Status**: Accepted
- **Context**:
  - Need durable storage for:
    - Raw events.
    - Enriched events (with ML predictions).
    - Aggregated counts for dashboards.
  - Must be easy to run locally and on free tiers.
- **Decision**:
  - Use **Postgres** as the main database.
  - Define ORM models via SQLAlchemy 2.x in `safetyops.db.models`.
  - Create an Alembic-ready structure for future migrations.
- **Consequences**:
  - Strong consistency and familiar SQL semantics.
  - Easy to extend schema as features evolve.
  - Single database keeps v1 simple; later versions might introduce analytical stores.

---

## ADR-0005: FastAPI + Streamlit for API and UI

- **Status**: Accepted
- **Context**:
  - Need:
    - An ingestion + query API with good typing and ecosystem.
    - A lightweight UI for operators with minimal boilerplate.
- **Decision**:
  - Use **FastAPI** for the API:
    - `apps/api` as the service package.
    - Centralized exception handling and structured logging.
  - Use **Streamlit** for the UI:
    - `apps/ui` with multiple tabs (Live Feed, Incident Triage, Ops Dashboard).
- **Consequences**:
  - Fast iteration and strong typing.
  - Streamlit is highly convenient for dashboards and supports free hosting options.
  - UI logic is Python-based, which fits the rest of the stack.

---

## ADR-0006: Local-first, Free-first Infra

- **Status**: Accepted
- **Context**:
  - The project should be easy to run on a laptop with Docker and extend later to free-tier clouds.
- **Decision**:
  - Provide `infra/docker-compose.local.yml` to run:
    - Postgres
    - Redis
    - MLflow
    - Prometheus
    - Grafana (minimal)
  - Run API/UI/worker **outside** of Docker in dev by default (host processes).
- **Consequences**:
  - Developers can run `docker compose` once and iterate on Python code locally.
  - Minimal vendor lock-in.
  - Later, containers can be defined for each service for deployment.

---

## ADR-0007: Context-First AI Workflow

- **Status**: Accepted
- **Context**:
  - Future work may be performed by AI agents (like this one).
  - We want changes to be coherent and well-documented.
- **Decision**:
  - Establish `context/` as the **source of truth** for goals, architecture, components, and decisions.
  - Require AI and human contributors to:
    1. Read `context/*` before significant changes.
    2. Update `03_DECISIONS_LOG.md` when architecture-level choices change.
- **Consequences**:
  - Keeps the repo self-documenting and resilient to drift.
  - Forces explicit trade-offs and rationales for major changes.

---

## ADR-0008: Synthetic NLP Dataset + DistilBERT Severity Model

- **Status**: Accepted
- **Context**:
  - We need an NLP model that can be trained and run on free-tier hardware.
  - No suitable open incident/safety dataset is guaranteed, and licensing can be complex.
- **Decision**:
  - Generate a small **synthetic incident dataset** with category and severity labels via
    `scripts/download_text_dataset.py`.
  - Fine-tune `distilbert-base-uncased` on **severity** only (`low`, `medium`, `high`).
  - Keep category classification rule-based in v1.
  - Log metrics and artifacts to MLflow and save the model under `models/nlp/`.
- **Consequences**:
  - Training is lightweight and reproducible on laptops and free GPUs.
  - The model is clearly marked as synthetic / non-production in the model card.
  - Real deployments can swap in a production-grade dataset and retrain.

---

## ADR-0009: YOLOv8 PPE Inference with Optional Colab Training

- **Status**: Accepted
- **Context**:
  - We want realistic PPE detection without bundling large image datasets.
- **Decision**:
  - Use Ultralytics **YOLOv8n** (`yolov8n.pt`) as the default PPE model.
  - Implement `safetyops.ml.vision.infer.run_ppe_inference` with lazy imports and a stub fallback.
  - Provide an optional `safetyops.ml.vision.train` script and `docs/vision_colab.md` to fine-tune
    on a YOLO-format PPE dataset in Google Colab.
- **Consequences**:
  - Inference works out-of-the-box on CPU with automatic weight download.
  - Users with a GPU can train custom PPE models without bloating the repo.
  - The worker and UI remain robust even when YOLO is unavailable (stub path).

---

## ADR-0010: LangGraph-Inspired Triage Workflow with Local LLM Fallback

- **Status**: Accepted
- **Context**:
  - SafetyOps Copilot needs a multi-step reasoning pipeline for incident triage, not just
    single-shot model calls.
  - We want an architecture that can later be upgraded to full LangGraph / multi-agent flows.
- **Decision**:
  - Implement a triage workflow in `safetyops.agents.triage_graph` composed of:
    - Context fetch (recent events, aggregates).
    - Risk assessment.
    - Runbook lookup from local markdown playbooks.
    - Report writer that produces a structured markdown brief.
    - Optional LLM enhancer that calls a local **Ollama** instance if configured via env vars.
  - Expose this via `POST /copilot/triage`.
- **Consequences**:
  - Triage remains deterministic and fully functional without any LLM.
  - If an LLM is available, it can refine the human-facing report without changing core logic.
  - The design is compatible with future LangGraph upgrades if we add explicit graph definitions.

---

## ADR-0011: Evidently-Based Drift Reports

- **Status**: Accepted
- **Context**:
  - We need basic model monitoring and drift detection that works from Postgres + CSV data.
- **Decision**:
  - Use **Evidently** to compare:
    - Reference data from the synthetic training CSV.
    - Recent production enriched text events from Postgres.
  - Generate HTML reports under `artifacts/drift_reports/` and expose them via:
    - `POST /monitoring/drift/run`
    - `GET /monitoring/drift/latest`
- **Consequences**:
  - Drift analysis is scriptable and can be triggered via API/UI.
  - Reports are static HTML files that are easy to store and share.
  - Future: add richer monitoring (per-feature, per-site) without changing the interface.

---

## ADR-0012: DLQ and Idempotent Worker with Redis Streams

- **Status**: Accepted
- **Context**:
  - The real-time worker must be resilient to failures and restarts.
- **Decision**:
  - Store the Redis **stream message ID** on `RawEvent.stream_message_id` to enforce
    idempotent processing.
  - Add a Redis **DLQ stream** (`safetyops:events:dlq`) and:
    - Retry processing with exponential backoff.
    - After N failures, push the event + error info to the DLQ.
  - Expose:
    - `GET /dlq/recent` to inspect DLQ entries.
    - `POST /reprocess/{message_id}` to replay messages back into the main stream.
- **Consequences**:
  - Multiple workers can safely process the same stream without double-enrichment.
  - Operators have visibility into failed events and a way to reprocess them.
  - The design stays compatible with the existing Redis Streams abstraction.

---

## ADR-0013: Free-First Deployments (Streamlit Cloud + HF Spaces)

- **Status**: Accepted
- **Context**:
  - Target users should be able to run SafetyOps Copilot end-to-end on free tiers.
- **Decision**:
  - Introduce `DEPLOY_MODE` (`local` | `cloud`) in settings.
  - Provide deployment docs:
    - `docs/deploy/streamlit_cloud.md` for Streamlit Cloud UI.
    - `docs/deploy/hf_spaces.md` for FastAPI on Hugging Face Spaces.
  - In `cloud` mode:
    - Prefer calling a remote API via `SAFETYOPS_API_BASE_URL`.
    - Avoid assuming local Docker-only services.
- **Consequences**:
  - A minimal demo can run with only the UI on Streamlit Cloud.
  - More complete setups can combine HF Spaces API + managed Redis/Postgres.
  - Local Docker Compose remains the recommended mode for full-featured development.

---

## ADR-0014: Per-Service Requirements Files

- **Status**: Accepted
- **Context**:
  - A single `requirements.txt` forced every environment (CI, UI-only deploys)
    to install torch/ultralytics/transformers (~2+ GB), which breaks free-tier
    deployments and slows CI.
- **Decision**:
  - Split dependencies into `requirements/{base,api,worker,ui,ml}.txt`.
  - `ml.txt` is optional; NLP and vision inference lazily import their heavy
    dependencies and fall back to the rule-based classifier / stub predictions.
  - `requirements-dev.txt` installs all services without `ml.txt`.
- **Consequences**:
  - CI runs torch-free; deployments install only what each service needs.
  - Real model inference requires an explicit `pip install -r requirements/ml.txt`.

---

## ADR-0015: Real Training Data from MSHA Accident Narratives

- **Status**: Accepted
- **Context**:
  - The NLP severity model was trained on synthetic data, which undermines the
    credibility of reported metrics.
  - OSHA Severe Injury Reports contain real narratives but, by definition,
    only severe outcomes — there is no "low" class.
  - MSHA open data (accidents since 2000) has ~273k narratives with a
    DEGREE_INJURY outcome spanning the full severity spectrum.
- **Decision**:
  - Derive labels from `DEGREE_INJURY_CD`: fatality/permanent disability →
    `high`; lost or restricted workdays → `medium`; no lost time → `low`.
    Ambiguous codes (illness, natural causes, non-employees) are excluded.
  - Balance-sample to the smallest class and hold out a stratified test set
    (`scripts/download_msha_dataset.py`).
  - Evaluate the fine-tuned model against the rule-based baseline on the
    held-out set (`safetyops/ml/nlp/evaluate.py`).
- **Consequences**:
  - Metrics are real and reproducible; the baseline comparison is honest.
  - The training domain is mining; transfer to other industries is a
    documented limitation in the model card.

---

## ADR-0016: OpenAI-Compatible LLM Endpoint for Copilot Enhancement

- **Status**: Accepted
- **Context**:
  - Report enhancement only supported local Ollama, which cannot run on
    free-tier cloud deployments.
- **Decision**:
  - Configure via `SAFETYOPS_LLM_BASE_URL`, `SAFETYOPS_LLM_API_KEY`,
    `SAFETYOPS_LLM_MODEL`; POST to `{base_url}/v1/chat/completions`.
  - Works with Groq (free tier), OpenAI, or local Ollama; `ollama_*` settings
    remain as deprecated aliases.
- **Consequences**:
  - Deployed demos get genuinely LLM-written incident briefs at no cost.
  - Failures still degrade gracefully to the template-based report.

---

## ADR-0017: Community Hard-Hat Weights for PPE Detection

- **Status**: Accepted
- **Context**:
  - COCO `yolov8n.pt` has no PPE classes, so compliance scoring was
    effectively fake (helmets could never be detected). Fine-tuning requires a
    GPU, which is out of scope for local-first setup.
- **Decision**:
  - Use `keremberke/yolov8n-hard-hat-detection` (labels `Hardhat` /
    `NO-Hardhat`) fetched by `scripts/download_vision_model.py`.
  - The inference wrapper supports three label schemes (hard-hat heads,
    person+equipment, person-only) and reports neutral compliance when the
    loaded weights cannot see PPE.
- **Consequences**:
  - Vision demos produce real PPE compliance scores out of the box.
  - Hard hats only; other PPE types remain future fine-tuning work.

---

## How to add a new decision

1. Increment the ADR ID (e.g., `ADR-0014`).
2. Use the same template:
   - Status
   - Context
   - Decision
   - Consequences
3. Keep the description **concise but explicit**.
4. Reference the change in relevant code comments or READMEs if needed.