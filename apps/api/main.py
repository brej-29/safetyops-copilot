from __future__ import annotations

import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import List

import redis
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from safetyops.agents.triage_graph import run_triage_workflow
from safetyops.core import configure_logging, get_logger, set_correlation_id, settings
from safetyops.core.exceptions import SafetyOpsError
from safetyops.db import DailyAggregate, EnrichedEvent, init_db
from safetyops.db.session import get_session
from safetyops.domain.events import (
    EventEnvelope,
    EventType,
    TextEventPayload,
    TextEventRequest,
    VisionEventPayload,
)
from safetyops.domain.responses import (
    AggregateSummaryItem,
    AggregateSummaryResponse,
    CopilotTriageRequest,
    CopilotTriageResponse,
    CopilotTriageContextEvent,
    EnrichedEventResponse,
    HealthResponse,
)
from safetyops.monitoring import EVENTS_INGESTED
from safetyops.streaming import RedisStreamsEventBus

configure_logging()
logger = get_logger(__name__)
app = FastAPI(title=settings.app_name, version=settings.app_version)

_event_bus = RedisStreamsEventBus()


@app.on_event("startup")
def on_startup() -> None:
    """Initialize DB schema for local dev and ensure consumer group exists."""
    init_db()
    try:
        _event_bus.ensure_consumer_group()
    except SafetyOpsError:
        # Logged in the event bus implementation; we surface it via /health.
        logger.exception("Failed to ensure Redis consumer group on startup")


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Attach a correlation_id to the request and log context."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    set_correlation_id(correlation_id)
    try:
        response = await call_next(request)
    finally:
        # Clear correlation id after request is processed
        set_correlation_id(None)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(SafetyOpsError)
async def safetyops_exception_handler(request: Request, exc: SafetyOpsError) -> JSONResponse:
    logger.error(
        "SafetyOpsError during request",
        extra={"path": request.url.path, "error_type": exc.__class__.__name__},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_type": exc.__class__.__name__},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception during request",
        extra={"path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def _get_db_session() -> Session:
    """FastAPI dependency that yields a DB session."""
    # get_session is a contextmanager that manages commit/rollback
    with get_session() as session:
        yield session


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Simple health endpoint."""
    return HealthResponse(status="ok", version=settings.app_version)


@app.get("/metrics")
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post("/events/text", status_code=202)
def create_text_event(request: Request, body: TextEventRequest) -> dict:
    """Ingest a text event and publish it to the stream."""
    correlation_id = request.headers.get("X-Correlation-ID")
    payload = TextEventPayload(text=body.text, metadata=body.metadata)
    envelope = EventEnvelope(
        event_type=EventType.TEXT,
        correlation_id=correlation_id,
        source="api",
        payload=payload,
    )

    message_id = _event_bus.publish(envelope)
    EVENTS_INGESTED.labels(event_type=envelope.event_type.value).inc()

    return {"event_id": envelope.id, "message_id": message_id}


@app.post("/events/vision", status_code=202)
async def create_vision_event(
    request: Request,
    image_path: str | None = Form(default=None),
    image_file: UploadFile | None = File(default=None),
) -> dict:
    """Ingest a vision event (image upload or path) and publish it to the stream."""
    correlation_id = request.headers.get("X-Correlation-ID")

    resolved_image_path: str | None = image_path
    if image_file is not None:
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_path = uploads_dir / image_file.filename
        content = await image_file.read()
        try:
            file_path.write_bytes(content)
        except OSError as exc:
            logger.exception(
                "Failed to persist uploaded image",
                extra={"path": str(file_path)},
            )
            raise HTTPException(status_code=500, detail="Failed to persist uploaded image") from exc
        resolved_image_path = str(file_path)

    payload = VisionEventPayload(image_path=resolved_image_path, metadata=None)
    envelope = EventEnvelope(
        event_type=EventType.VISION,
        correlation_id=correlation_id,
        source="api",
        payload=payload,
    )

    message_id = _event_bus.publish(envelope)
    EVENTS_INGESTED.labels(event_type=envelope.event_type.value).inc()

    return {"event_id": envelope.id, "message_id": message_id, "image_path": resolved_image_path}


@app.get("/events/recent", response_model=List[EnrichedEventResponse])
def get_recent_events(
    limit: int = 50,
    session: Session = Depends(_get_db_session),
) -> List[EnrichedEventResponse]:
    """Return recent enriched events from Postgres."""
    stmt = (
        select(EnrichedEvent)
        .order_by(EnrichedEvent.created_at.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).scalars().all()

    return [
        EnrichedEventResponse(
            id=row.id,
            event_type=row.event_type,
            created_at=row.created_at,
            correlation_id=row.correlation_id,
            category=row.category,
            severity=row.severity,
            enrichment=row.enrichment,
        )
        for row in rows
    ]


@app.get("/aggregates/summary", response_model=AggregateSummaryResponse)
def get_aggregate_summary(
    days: int = 7,
    session: Session = Depends(_get_db_session),
) -> AggregateSummaryResponse:
    """Return simple counts by type and severity over a recent day window."""
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be positive")

    start_date = date.today() - timedelta(days=days - 1)
    stmt = (
        select(
            DailyAggregate.event_type,
            DailyAggregate.severity,
            func.sum(DailyAggregate.count),
        )
        .where(DailyAggregate.date >= start_date)
        .group_by(DailyAggregate.event_type, DailyAggregate.severity)
    )
    rows = session.execute(stmt).all()

    items = [
        AggregateSummaryItem(
            event_type=row[0],
            severity=row[1],
            count=row[2] or 0,
        )
        for row in rows
    ]
    return AggregateSummaryResponse(items=items)


@app.post("/monitoring/drift/run")
def run_drift_report() -> dict:
    """Trigger Evidently drift analysis and return the path to the report."""
    from safetyops.monitoring.drift import run_drift_analysis

    try:
        path = run_drift_analysis()
    except Exception as exc:
        logger.exception("Failed to run drift analysis")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"report_path": str(path)}


@app.get("/monitoring/drift/latest")
def get_latest_drift_report() -> dict:
    """Return the latest available drift report path, if any."""
    from safetyops.monitoring.drift import get_latest_report_path

    path = get_latest_report_path()
    if path is None:
        return {"report_path": None}
    return {"report_path": str(path)}


@app.get("/dlq/recent")
def get_recent_dlq_messages(limit: int = 50) -> dict:
    """Return recent messages from the DLQ Redis stream."""
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")

    client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
    try:
        # Use XREVRANGE to get most recent messages first
        entries = client.xrevrange(settings.dlq_stream_key, max="+", min="-", count=limit)
    except Exception as exc:
        logger.exception("Failed to read from DLQ stream")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    messages = []
    for message_id, fields in entries:
        raw_data = fields.get(b"data") or fields.get("data")
        if isinstance(raw_data, (bytes, bytearray)):
            payload_str = raw_data.decode("utf-8")
        else:
            payload_str = str(raw_data)
        messages.append(
            {
                "message_id": message_id.decode() if isinstance(message_id, bytes) else message_id,
                "data": payload_str,
            }
        )

    return {"messages": messages}


@app.post("/reprocess/{message_id}")
def reprocess_from_dlq(message_id: str) -> dict:
    """Reprocess a message that previously failed and was sent to the DLQ.

    The message is read from the DLQ stream and re-published to the main stream
    so that a worker can pick it up again.
    """
    client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
    try:
        entries = client.xrange(settings.dlq_stream_key, min=message_id, max=message_id)
    except Exception as exc:
        logger.exception("Failed to read specific message from DLQ", extra={"message_id": message_id})
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not entries:
        raise HTTPException(status_code=404, detail="DLQ message not found")

    _, fields = entries[0]
    raw_data = fields.get(b"data") or fields.get("data")
    if isinstance(raw_data, (bytes, bytearray)):
        payload_str = raw_data.decode("utf-8")
    else:
        payload_str = str(raw_data)

    import json

    try:
        payload = json.loads(payload_str)
        envelope_json = payload.get("envelope")
        if isinstance(envelope_json, str):
            envelope = EventEnvelope.model_validate_json(envelope_json)
        else:
            envelope = EventEnvelope.model_validate(envelope_json)
    except Exception as exc:
        logger.exception("Failed to parse DLQ payload for reprocessing", extra={"message_id": message_id})
        raise HTTPException(status_code=500, detail="Invalid DLQ payload; cannot reprocess") from exc

    new_message_id = _event_bus.publish(envelope)
    return {"reprocessed_event_id": envelope.id, "new_message_id": new_message_id}


@app.post("/copilot/triage", response_model=CopilotTriageResponse)
def copilot_triage(request_body: CopilotTriageRequest) -> CopilotTriageResponse:
    """Run the Copilot triage workflow for an incident ID or free-text description."""
    if not request_body.incident_id and not (request_body.text and request_body.text.strip()):
        raise HTTPException(status_code=400, detail="Provide either incident_id or text")

    state = run_triage_workflow(
        incident_id=request_body.incident_id,
        text=request_body.text,
        image_path=request_body.image_path,
    )

    context_events = [
        CopilotTriageContextEvent(
            id=ev.id,
            created_at=ev.created_at,
            category=ev.category,
            severity=ev.severity,
            risk_score=ev.risk_score,
        )
        for ev in state.get("context_events", [])
    ]

    return CopilotTriageResponse(
        incident_id=state.get("incident_id", request_body.incident_id or "ad-hoc"),
        category=state.get("category"),
        severity=state.get("severity"),
        risk_score=state.get("risk_score"),
        context_events=context_events,
        aggregates=state.get("aggregates", {}),
        report_markdown=state.get("report_markdown", ""),
    )