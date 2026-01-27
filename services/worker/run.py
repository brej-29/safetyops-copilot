from __future__ import annotations

import signal
import time
from typing import Optional

import redis
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from safetyops.core import configure_logging, get_logger, settings
from safetyops.db import DailyAggregate, EnrichedEvent, HourlyAggregate, RawEvent, init_db
from safetyops.db.session import get_session
from safetyops.domain.events import EventEnvelope, EventType
from safetyops.ml.nlp.infer import predict_severity
from safetyops.ml.vision.yolo import run_ppe_inference
from safetyops.monitoring import DLQ_MESSAGES, EVENTS_PROCESSED, WORKER_PROCESSING_TIME
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


def _compute_risk_score(severity: str, compliance_score: Optional[float], created_ts: float) -> int:
    """Compute a simple 0-100 risk score.

    Combines:
    - severity (low/medium/high)
    - PPE compliance (if available)
    - recency (events in the last 24h get a modest boost)
    """
    now = time.time()
    age_seconds = max(0.0, now - created_ts)

    if severity == "high":
        base = 80
    elif severity == "medium":
        base = 60
    else:
        base = 40

    ppe_penalty = 0.0
    if compliance_score is not None:
        ppe_penalty = (1.0 - max(0.0, min(1.0, compliance_score))) * 20.0

    if age_seconds < 3600:  # last hour
        recency_boost = 10.0
    elif age_seconds < 86400:  # last day
        recency_boost = 5.0
    else:
        recency_boost = 0.0

    score = base + ppe_penalty + recency_boost
    return int(max(0, min(100, round(score))))


def _get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=False)


def _send_to_dlq(message_id: str, envelope: EventEnvelope, error: Exception) -> None:
    client = _get_redis_client()
    payload = {
        "event_id": envelope.id,
        "event_type": envelope.event_type.value,
        "envelope": envelope.model_dump_json(),
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    # Store JSON as bytes for consistency with main stream
    import json

    data = json.dumps(payload).encode("utf-8")
    client.xadd(settings.dlq_stream_key, {"data": data})
    DLQ_MESSAGES.inc()
    logger.error(
        "Sent message to DLQ",
        extra={
            "dlq_stream": settings.dlq_stream_key,
            "message_id": message_id,
            "event_id": envelope.id,
        },
    )


def process_event(envelope: EventEnvelope, message_id: str) -> None:
    """Process a single event: persist raw, enrich, persist enriched, update aggregates."""
    from safetyops.monitoring.metrics import model_inference_seconds

    with get_session() as session:
        # Idempotency: if we've already processed this stream message, skip.
        existing = session.query(RawEvent).filter_by(stream_message_id=message_id).one_or_none()
        if existing is not None:
            logger.info(
                "Skipping already-processed message",
                extra={"message_id": message_id, "event_id": existing.id},
            )
            return

        raw = RawEvent(
            id=envelope.id,
            event_type=envelope.event_type.value,
            payload=(
                envelope.payload.model_dump()
                if hasattr(envelope.payload, "model_dump")
                else {}
            ),
            created_at=envelope.created_at,
            correlation_id=envelope.correlation_id,
            stream_message_id=message_id,
        )
        session.add(raw)

        if envelope.event_type == EventType.TEXT:
            # NLP severity model with rule-based fallback
            nlp_timer = model_inference_seconds.labels(model="nlp").time()
            try:
                prediction = predict_severity(envelope.payload.text)  # type: ignore[attr-defined]
            finally:
                nlp_timer.__exit__(None, None, None)
            enrichment_data = prediction.model_dump()
            enrichment_data["text"] = envelope.payload.text  # type: ignore[attr-defined]
            category = prediction.category
            severity = prediction.severity
            compliance_score: Optional[float] = None
        else:
            image_path: Optional[str] = getattr(envelope.payload, "image_path", None)  # type: ignore[attr-defined]
            vision_prediction = run_ppe_inference(image_path=image_path)
            enrichment_data = vision_prediction.model_dump()
            category = "ppe_compliance"
            severity = _severity_from_compliance(vision_prediction.compliance_score)
            compliance_score = vision_prediction.compliance_score

        risk_score = _compute_risk_score(
            severity=severity,
            compliance_score=compliance_score,
            created_ts=envelope.created_at.timestamp(),
        )
        enrichment_data["risk_score"] = risk_score

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

        daily = (
            session.query(DailyAggregate)
            .filter_by(
                date=agg_date,
                event_type=envelope.event_type.value,
                severity=severity,
                category=category,
            )
            .one_or_none()
        )
        if daily is None:
            daily = DailyAggregate(
                date=agg_date,
                event_type=envelope.event_type.value,
                severity=severity,
                category=category,
                count=1,
            )
            session.add(daily)
        else:
            daily.count += 1

        hourly = (
            session.query(HourlyAggregate)
            .filter_by(
                date=agg_date,
                hour=envelope.created_at.hour,
                event_type=envelope.event_type.value,
                severity=severity,
                category=category,
            )
            .one_or_none()
        )
        if hourly is None:
            hourly = HourlyAggregate(
                date=agg_date,
                hour=envelope.created_at.hour,
                event_type=envelope.event_type.value,
                severity=severity,
                category=category,
                count=1,
            )
            session.add(hourly)
        else:
            hourly.count += 1


def run_worker_loop(poll_batch_size: int = 10, block_ms: int = 5000) -> None:
    """Main worker loop."""
    configure_logging()
    logger.info(
        "Starting SafetyOps worker",
        extra={
            "env": settings.env,
            "stream_key": settings.stream_key,
            "consumer_group": settings.consumer_group,
        },
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

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                reraise=True,
            )
            def _process_with_retry() -> None:
                process_event(envelope, stream_event.message_id)

            try:
                _process_with_retry()
                event_bus.ack(stream_event.message_id)
                EVENTS_PROCESSED.labels(
                    event_type=envelope.event_type.value,
                    status="success",
                ).inc()
            except RetryError as exc:
                error = exc.last_attempt.exception()
                logger.exception(
                    "Exhausted retries processing event; sending to DLQ",
                    extra={
                        "event_id": envelope.id,
                        "event_type": envelope.event_type.value,
                        "message_id": stream_event.message_id,
                    },
                )
                _send_to_dlq(stream_event.message_id, envelope, error or exc)
                EVENTS_PROCESSED.labels(
                    event_type=envelope.event_type.value,
                    status="dlq",
                ).inc()
            except Exception as exc:
                logger.exception(
                    "Unexpected error processing event (no retries applied)",
                    extra={
                        "event_id": envelope.id,
                        "event_type": envelope.event_type.value,
                        "message_id": stream_event.message_id,
                    },
                )
                _send_to_dlq(stream_event.message_id, envelope, exc)
                EVENTS_PROCESSED.labels(
                    event_type=envelope.event_type.value,
                    status="error",
                ).inc()
            finally:
                elapsed = time.perf_counter() - start
                WORKER_PROCESSING_TIME.labels(event_type=envelope.event_type.value).observe(elapsed)


def main() -> None:
    run_worker_loop()


if __name__ == "__main__":
    main()