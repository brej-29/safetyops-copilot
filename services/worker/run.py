from __future__ import annotations

import signal
import time
from typing import Optional

from safetyops.core import configure_logging, get_logger, settings
from safetyops.db import DailyAggregate, EnrichedEvent, RawEvent, init_db
from safetyops.db.session import get_session
from safetyops.domain.events import EventEnvelope, EventType
from safetyops.ml.nlp.classifier import classify_incident
from safetyops.ml.vision.yolo import run_ppe_inference
from safetyops.monitoring import WORKER_PROCESSED, WORKER_PROCESSING_TIME
from safetyops.streaming import RedisStreamsEventBus

logger = get_logger(__name__)

_shutdown = False


def _handle_signal(signum, frame) -> None:  # type: ignore[override]
    global _shutdown
    logger.info("Received shutdown signal", extra={"signal": signum})
    _shutdown = True


def _ensure_schema_and_group(event_bus: RedisStreamsEventBus) -> None:
    init_db()
    event_bus.ensure_consumer_group()


def _severity_from_compliance(score: float) -> str:
    if score >= 0.8:
        return "low"
    if score >= 0.5:
        return "medium"
    return "high"


def process_event(envelope: EventEnvelope) -> None:
    """Process a single event: persist raw, enrich, persist enriched, update aggregates."""
    with get_session() as session:
        raw = RawEvent(
            id=envelope.id,
            event_type=envelope.event_type.value,
            payload=envelope.payload.model_dump() if hasattr(envelope.payload, "model_dump") else {},
            created_at=envelope.created_at,
            correlation_id=envelope.correlation_id,
        )
        session.add(raw)

        if envelope.event_type == EventType.TEXT:
            prediction = classify_incident(envelope.payload.text)  # type: ignore[attr-defined]
            enrichment_data = prediction.model_dump()
            category = prediction.category
            severity = prediction.severity
        else:
            image_path: Optional[str] = getattr(envelope.payload, "image_path", None)  # type: ignore[attr-defined]
            prediction = run_ppe_inference(image_path=image_path)
            enrichment_data = prediction.model_dump()
            category = "ppe_compliance"
            severity = _severity_from_compliance(prediction.compliance_score)

        enriched = EnrichedEvent(
            id=envelope.id,
            raw_event_id=envelope.id,
            event_type=envelope.event_type.value,
            enrichment=enrichment_data,
            created_at=envelope.created_at,
            correlation_id=envelope.correlation_id,
            category=category,
            severity=severity,
        )
        session.add(enriched)

        agg_date = envelope.created_at.date()
        aggregate = (
            session.query(DailyAggregate)
            .filter_by(date=agg_date, event_type=envelope.event_type.value, severity=severity)
            .one_or_none()
        )
        if aggregate is None:
            aggregate = DailyAggregate(
                date=agg_date,
                event_type=envelope.event_type.value,
                severity=severity,
                count=1,
            )
            session.add(aggregate)
        else:
            aggregate.count += 1


def run_worker_loop(poll_batch_size: int = 10, block_ms: int = 5000) -> None:
    """Main worker loop."""
    configure_logging()
    logger.info(
        "Starting SafetyOps worker",
        extra={"env": settings.env, "stream_key": settings.stream_key, "consumer_group": settings.consumer_group},
    )

    event_bus = RedisStreamsEventBus()
    _ensure_schema_and_group(event_bus)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not _shutdown:
        events = event_bus.consume(count=poll_batch_size, block_ms=block_ms)
        if not events:
            continue

        for stream_event in events:
            envelope = stream_event.envelope
            start = time.perf_counter()
            try:
                process_event(envelope)
                event_bus.ack(stream_event.message_id)
                WORKER_PROCESSED.labels(
                    event_type=envelope.event_type.value,
                    result="success",
                ).inc()
            except Exception:
                logger.exception(
                    "Error processing event",
                    extra={"event_id": envelope.id, "event_type": envelope.event_type.value},
                )
                WORKER_PROCESSED.labels(
                    event_type=envelope.event_type.value,
                    result="error",
                ).inc()
            finally:
                elapsed = time.perf_counter() - start
                WORKER_PROCESSING_TIME.labels(event_type=envelope.event_type.value).observe(elapsed)


def main() -> None:
    run_worker_loop()


if __name__ == "__main__":
    main()