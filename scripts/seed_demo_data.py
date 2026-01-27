from __future__ import annotations

from datetime import datetime, timedelta, timezone

from safetyops.core import configure_logging, get_logger
from safetyops.db import DailyAggregate, EnrichedEvent, RawEvent, init_db
from safetyops.db.session import get_session
from safetyops.domain.events import EventEnvelope, EventType, TextEventPayload
from safetyops.ml.nlp.classifier import classify_incident

logger = get_logger(__name__)


def main() -> None:
    """Seed the database with a small set of demo events and aggregates.

    This is primarily for local experimentation and UI testing.
    """
    configure_logging()
    init_db()

    now = datetime.now(timezone.utc)
    examples = [
        "Worker slipped on wet floor near loading bay.",
        "Minor electrical shock when handling exposed wire.",
        "Small fire in storage area; extinguished quickly.",
        "Chemical spill in lab; area evacuated.",
        "Routine safety inspection with no incidents reported.",
    ]

    with get_session() as session:
        for idx, text in enumerate(examples):
            envelope = EventEnvelope(
                event_type=EventType.TEXT,
                payload=TextEventPayload(text=text, metadata={"source": "seed-script"}),
                created_at=now - timedelta(minutes=idx * 5),
            )
            prediction = classify_incident(text)
            enrichment = prediction.model_dump()

            raw = RawEvent(
                id=envelope.id,
                event_type=envelope.event_type.value,
                payload=envelope.payload.model_dump(),
                created_at=envelope.created_at,
                correlation_id=envelope.correlation_id,
            )
            session.add(raw)

            enriched = EnrichedEvent(
                id=envelope.id,
                raw_event_id=envelope.id,
                event_type=envelope.event_type.value,
                enrichment=enrichment,
                created_at=envelope.created_at,
                correlation_id=envelope.correlation_id,
                category=prediction.category,
                severity=prediction.severity,
            )
            session.add(enriched)

            agg_date = envelope.created_at.date()
            aggregate = (
                session.query(DailyAggregate)
                .filter_by(date=agg_date, event_type=envelope.event_type.value, severity=prediction.severity)
                .one_or_none()
            )
            if aggregate is None:
                aggregate = DailyAggregate(
                    date=agg_date,
                    event_type=envelope.event_type.value,
                    severity=prediction.severity,
                    count=1,
                )
                session.add(aggregate)
            else:
                aggregate.count += 1

    logger.info("Seeded demo data into database")


if __name__ == "__main__":
    main()