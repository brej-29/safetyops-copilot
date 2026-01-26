# Components — SafetyOps Copilot

This document zooms into each major component and how it should be used and extended.

---

## 1. API Service (`apps/api`)

### Responsibilities

- Provide a **stable ingestion API** for:
  - `POST /events/text`
  - `POST /events/vision`
- Provide **read APIs** for:
  - `GET /events/recent`
  - `GET /aggregates/summary`
- Expose **health** and **metrics** endpoints:
  - `GET /health`
  - `GET /metrics`
- Implement **structured logging** and **centralized exception handling**.

### Key internals

- Uses `safetyops.core.settings.Settings` for configuration.
- Uses `safetyops.core.logging` for:
  - JSON-ish structured logging.
  - `correlation_id` context per request (from header or generated).
- Pydantic models in `safetyops.domain`:
  - `TextEventRequest`, `VisionEventRequest`
  - `EventEnvelope`
  - Response models for enriched events and aggregates.
- Interacts with:
  - `safetyops.streaming.BaseEventBus` (Redis implementation in production).
  - SQLAlchemy session helpers (`safetyops.db.session`) for read endpoints.
  - Prometheus metrics (`safetyops.monitoring.metrics`).

---

## 2. Worker Service (`services/worker`)

### Responsibilities

- Consume events from the streaming bus.
- Run **ML inference**:
  - Vision (YOLO PPE).
  - Text (rule-based classifier).
- Persist:
  - Raw event (`raw_events` table).
  - Enriched event (`enriched_events` table).
  - Aggregate counts (`daily_aggregates` table).
- Emit Prometheus metrics.

### Key internals

- Entrypoint: `python -m services.worker.run`.
- Uses:
  - `safetyops.streaming.RedisStreamsEventBus` for `consume` and `ack`.
  - SQLAlchemy models in `safetyops.db.models`.
  - ML wrappers:
    - `safetyops.ml.vision.yolo`
    - `safetyops.ml.nlp.classifier`
  - Prometheus metrics in `safetyops.monitoring.metrics`.

### Error handling

- Per-event `try/except Exception` with:
  - Detailed logging (including correlation_id and event id).
  - Metrics for failures.
- The worker loop continues even if individual events fail.

---

## 3. UI Service (`apps/ui`)

### Responsibilities

- Provide an operator-facing dashboard with three tabs:

1. **Live Feed**
   - Button(s) to produce demo events (calls API).
   - Table of recent enriched events (auto-refresh).

2. **Incident Triage**
   - Text area for incident description.
   - Submit button that calls `POST /events/text`.
   - Shows the latest triage result for context.

3. **Ops Dashboard**
   - Visualizes aggregates from `GET /aggregates/summary`.
   - Uses simple matplotlib charts.
   - Includes placeholder links for future monitoring (drift, health).

### Implementation notes

- Implemented with **Streamlit** (`apps/ui/main.py`).
- Uses `httpx` to call the API (base URL from environment or default `http://localhost:8000`).
- Designed to be **simple, responsive, and free-tier friendly**.

---

## 4. Streaming (`safetyops/streaming`)

### Interface

`BaseEventBus` defines:

- `publish(event: EventEnvelope) -> str`
- `ensure_consumer_group() -> None`
- `consume(count: int = 10, block_ms: int = 5000) -> list[StreamEvent]`
- `ack(message_id: str) -> None`

Where `StreamEvent` is a small dataclass containing:

- `message_id`
- `envelope` (`EventEnvelope`)

### Redis Streams implementation

`RedisStreamsEventBus`:

- Wraps a `redis.Redis` client.
- Uses env-configured:
  - `REDIS_URL`
  - `STREAM_KEY`
  - `CONSUMER_GROUP`
  - `CONSUMER_NAME`
- Writes a single field (`data`) per message containing event JSON.
- Ensures consumer group on startup (idempotent).
- Converts between Redis responses and Pydantic `EventEnvelope`.

---

## 5. Database (`safetyops/db`)

### Models (`models.py`)

- `RawEvent`
  - `id` (UUID string, PK)
  - `event_type`
  - `payload` (JSON)
  - `created_at` (UTC, indexed)
  - `correlation_id` (nullable, indexed)

- `EnrichedEvent`
  - `id` (UUID string, PK)
  - `raw_event_id` (FK → `RawEvent.id`)
  - `event_type`
  - `enrichment` (JSON predictions)
  - `created_at` (UTC, indexed)
  - `severity` (nullable, indexed)
  - `category` (nullable, indexed)

- `DailyAggregate`
  - `id` (PK, integer)
  - `date` (date, indexed)
  - `event_type` (indexed)
  - `severity` (indexed)
  - `count` (integer)

### Session / engine helpers

- `safetyops.db.session` exposes:
  - `get_engine()`
  - `SessionLocal` factory.
  - `get_session()` context manager / FastAPI dependency.

### Migrations

- Alembic scaffold:
  - `alembic.ini` at repo root.
  - `safetyops/db/migrations/` with `env.py` and `versions/` directory.
- Initial tables defined via ORM models; migrations can be generated later.

---

## 6. ML (`safetyops/ml`)

### Vision (`safetyops/ml/vision/yolo.py`)

- Lazy import of `ultralytics.YOLO` and `torch`.
- Provides a function/class like:

  - `run_ppe_inference(image_path: str) -> VisionPPEDetection`

- PPE heuristic:

  - Identifies detections for:
    - `person`
    - `helmet` / `hardhat`
    - `vest` / `safety vest`
  - Estimates:
    - number of persons.
    - number of persons with PPE.
    - compliance score ∈ [0, 1].

- If YOLO or torch are unavailable:
  - Logs a warning.
  - Returns a **stub** detection (e.g., a neutral or random-ish score) so the system still functions.

### NLP (`safetyops/ml/nlp/classifier.py`)

- Rule-based or sklearn-style baseline, but implemented as a **lightweight stub**:

  - `classify_incident(text: str) -> TextClassificationPrediction`

- Example categories:

  - `fall`
  - `electrical`
  - `fire`
  - `chemical`
  - `other`

- Severity:

  - `low` / `medium` / `high` based on keyword patterns.

- This is intentionally simple and deterministic for now; later prompts can replace it with a proper model (e.g., transformer fine-tune).

---

## 7. Monitoring (`safetyops/monitoring`)

### Metrics helpers

- Uses `prometheus_client` to define:

  - `EVENTS_PUBLISHED`
  - `WORKER_PROCESSED`
  - `WORKER_PROCESSING_TIME`

- The API exposes `/metrics` using `prometheus_client.generate_latest`.
- The worker calls metrics increment/observe functions around processing logic.

---

## 8. Context and Notebooks

- `context/*` describes:
  - Goals, architecture, components, decisions, workflow, and roadmap.
- `notebooks/*`:
  - EDA and decision explanations for text and vision.
  - End-to-end walkthrough of the system.

Future contributors (human or AI) must **consult these first** to maintain coherence.