from safetyops.domain.events import (
    EventEnvelope,
    EventType,
    TextEventPayload,
    TextEventRequest,
    VisionEventPayload,
    VisionEventRequest,
)


def test_text_event_request_and_envelope() -> None:
    req = TextEventRequest(text="Worker slipped on wet floor", metadata={"site": "A"})
    payload = TextEventPayload(**req.model_dump())
    envelope = EventEnvelope(event_type=EventType.TEXT, payload=payload)

    assert envelope.event_type == EventType.TEXT
    assert envelope.payload.text == req.text
    assert envelope.payload.metadata == req.metadata
    assert envelope.id
    assert envelope.created_at is not None


def test_vision_event_request_and_envelope() -> None:
    req = VisionEventRequest(image_path="data/sample/sample_ppe_image.jpg", metadata={"site": "B"})
    payload = VisionEventPayload(**req.model_dump())
    envelope = EventEnvelope(event_type=EventType.VISION, payload=payload)

    assert envelope.event_type == EventType.VISION
    assert envelope.payload.image_path == req.image_path
    assert envelope.payload.metadata == req.metadata