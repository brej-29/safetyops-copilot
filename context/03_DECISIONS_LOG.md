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

## How to add a new decision

1. Increment the ADR ID (e.g., `ADR-0008`).
2. Use the same template:
   - Status
   - Context
   - Decision
   - Consequences
3. Keep the description **concise but explicit**.
4. Reference the change in relevant code comments or READMEs if needed.