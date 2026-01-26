from __future__ import annotations

from typing import Any, Dict, List, Tuple

from safetyops.domain.events import EventEnvelope, EventType, TextEventPayload
from safetyops.streaming.redis_streams import RedisStreamsEventBus


class FakeRedis:
    def __init__(self) -> None:
        self.streams: Dict[str, List[Tuple[str, Dict[bytes, bytes]]]] = {}
        self.groups_created: List[Tuple[str, str]] = []
        self.acked: List[str] = []

    def xadd(self, key: str, fields: Dict[str, str]) -> str:
        message_id = f"{len(self.streams.get(key, []))}-0"
        stored_fields: Dict[bytes, bytes] = {
            (k.encode() if isinstance(k, str) else k): (v.encode() if isinstance(v, str) else v)
            for k, v in fields.items()
        }
        self.streams.setdefault(key, []).append((message_id, stored_fields))
        return message_id

    def xgroup_create(self, name: str, groupname: str, id: str = "0-0", mkstream: bool = True) -> None:
        self.groups_created.append((name, groupname))

    def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: Dict[str, str],
        count: int = 10,
        block: int = 0,
    ):
        key = next(iter(streams.keys()))
        messages = self.streams.get(key, [])
        if not messages:
            return []

        # Return all messages once, then clear.
        to_return = messages[:count]
        self.streams[key] = []

        formatted = []
        for message_id, fields in to_return:
            formatted.append((message_id.encode(), fields))
        return [(key.encode(), formatted)]

    def xack(self, key: str, groupname: str, message_id: str) -> None:
        self.acked.append(message_id)


def test_publish_and_consume_roundtrip() -> None:
    fake = FakeRedis()
    bus = RedisStreamsEventBus(redis_client=fake)

    bus.ensure_consumer_group()

    payload = TextEventPayload(text="test incident", metadata=None)
    envelope = EventEnvelope(event_type=EventType.TEXT, payload=payload)
    message_id = bus.publish(envelope)

    events = bus.consume()
    assert len(events) == 1
    event = events[0]
    assert event.envelope.id == envelope.id
    assert event.envelope.event_type == EventType.TEXT

    bus.ack(event.message_id)
    assert message_id in fake.acked or event.message_id in fake.acked