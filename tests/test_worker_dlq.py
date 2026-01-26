from __future__ import annotations

from typing import Any, Dict, List

import redis

from safetyops.core.settings import settings
from services.worker.run import _send_to_dlq  # type: ignore[attr-defined]
from safetyops.domain.events import EventEnvelope, EventType, TextEventPayload


class FakeRedis:
    def __init__(self) -> None:
        self.xadd_calls: List[Dict[str, Any]] = []

    def xadd(self, name: str, fields: Dict[str, bytes]) -> None:
        self.xadd_calls.append({"name": name, "fields": fields})


def test_send_to_dlq_uses_configured_stream(monkeypatch) -> None:
    fake = FakeRedis()

    def fake_from_url(url: str, decode_responses: bool = False) -> FakeRedis:  # type: ignore[override]
        return fake

    monkeypatch.setattr(redis, "Redis", type("R", (), {"from_url": staticmethod(fake_from_url)}))  # type: ignore[arg-type]

    envelope = EventEnvelope(
        event_type=EventType.TEXT,
        payload=TextEventPayload(text="Test incident", metadata={}),
        source="test",
    )

    class DummyError(Exception):
        pass

    _send_to_dlq("1-0", envelope, DummyError("boom"))  # type: ignore[arg-type]

    assert fake.xadd_calls, "Expected at least one xadd call"
    call = fake.xadd_calls[0]
    assert call["name"] == settings.dlq_stream_key