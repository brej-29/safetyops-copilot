from __future__ import annotations

from typing import List

from safetyops.core import configure_logging, get_logger
from safetyops.domain.events import EventEnvelope, EventType, TextEventPayload, VisionEventPayload
from safetyops.streaming import RedisStreamsEventBus

logger = get_logger(__name__)


def _sample_text_events() -> List[str]:
    return [
        "Worker slipped on wet floor near loading bay.",
        "Minor electrical shock when handling exposed wire.",
        "Small fire in storage area; extinguished quickly.",
        "Chemical spill in lab; area evacuated.",
        "Routine safety inspection with no incidents reported.",
    ]


def produce_demo_events(n_text: int = 5, n_vision: int = 3) -> None:
    configure_logging()
    bus = RedisStreamsEventBus()
    bus.ensure_consumer_group()

    texts = _sample_text_events()
    for i in range(n_text):
        payload = TextEventPayload(text=texts[i % len(texts)], metadata={"source": "demo-script"})
        envelope = EventEnvelope(event_type=EventType.TEXT, payload=payload, source="script")
        bus.publish(envelope)
        logger.info("Published demo text event", extra={"event_id": envelope.id})

    for i in range(n_vision):
        payload = VisionEventPayload(
            image_path="data/sample/sample_ppe_image.jpg",  # placeholder path
            metadata={"source": "demo-script"},
        )
        envelope = EventEnvelope(event_type=EventType.VISION, payload=payload, source="script")
        bus.publish(envelope)
        logger.info("Published demo vision event", extra={"event_id": envelope.id})

    logger.info("Finished producing demo events", extra={"n_text": n_text, "n_vision": n_vision})


def main() -> None:
    produce_demo_events()


if __name__ == "__main__":
    main()