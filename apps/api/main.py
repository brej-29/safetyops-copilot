from __future__ import annotations

import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    EnrichedEventResponse,
    HealthResponse,
)
from safetyops.monitoring import EVENTS_PUBLISHED
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
    EVENTS_PUBLISHED.labels(event_type=envelope.event_type.value).inc()

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
    EVENTS_PUBLISHED.labels(event_type=envelope.event_type.value).inc()

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