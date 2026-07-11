"""End-to-end pipeline test: API publish -> stream consume -> worker
enrichment -> Postgres/SQLite persistence -> API read model.

Uses fakeredis for the stream and the shared SQLite test database, so it
exercises the real event bus serialization, worker processing (including the
Prometheus inference timer), aggregates, and the query endpoints.
"""

from __future__ import annotations

import uuid

import fakeredis
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from safetyops.streaming import RedisStreamsEventBus
from services.worker.run import process_event


@pytest.fixture()
def fake_redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


@pytest.fixture()
def bus(fake_redis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(redis_client=fake_redis)


@pytest.fixture()
def client(monkeypatch, bus) -> TestClient:
    monkeypatch.setattr(api_main, "_event_bus", bus)
    with TestClient(api_main.app) as test_client:
        yield test_client


def _drain_and_process(bus: RedisStreamsEventBus) -> list:
    events = bus.consume(count=10, block_ms=1)
    for stream_event in events:
        process_event(stream_event.envelope, stream_event.message_id)
        bus.ack(stream_event.message_id)
    return events


def test_text_event_end_to_end(client: TestClient, bus: RedisStreamsEventBus) -> None:
    marker = f"integration-{uuid.uuid4()}"
    resp = client.post(
        "/events/text",
        json={
            "text": f"Worker slipped from scaffolding and was hospitalized ({marker})",
            "metadata": {"source": "integration-test"},
        },
    )
    assert resp.status_code == 202
    event_id = resp.json()["event_id"]

    events = _drain_and_process(bus)
    assert len(events) == 1

    recent = client.get("/events/recent", params={"limit": 200}).json()
    ours = [ev for ev in recent if ev["id"] == event_id]
    assert len(ours) == 1
    enriched = ours[0]
    assert enriched["event_type"] == "text_event"
    assert enriched["category"] == "fall"
    assert enriched["severity"] == "high"  # "hospitalized" keyword
    assert 0 <= enriched["enrichment"]["risk_score"] <= 100
    assert marker in enriched["enrichment"]["text"]

    summary = client.get("/aggregates/summary").json()
    assert any(
        item["event_type"] == "text_event" and item["count"] >= 1
        for item in summary["items"]
    )


def test_vision_event_end_to_end_uses_stub_without_yolo(
    client: TestClient, bus: RedisStreamsEventBus
) -> None:
    resp = client.post("/events/vision", data={"image_path": "does/not/exist.jpg"})
    assert resp.status_code == 202
    event_id = resp.json()["event_id"]

    _drain_and_process(bus)

    recent = client.get("/events/recent", params={"limit": 200}).json()
    ours = [ev for ev in recent if ev["id"] == event_id]
    assert len(ours) == 1
    enriched = ours[0]
    assert enriched["event_type"] == "vision_event"
    assert enriched["category"] == "ppe_compliance"
    assert 0.0 <= enriched["enrichment"]["compliance_score"] <= 1.0


def test_processing_is_idempotent(client: TestClient, bus: RedisStreamsEventBus) -> None:
    resp = client.post("/events/text", json={"text": "Small fire near the exit door"})
    assert resp.status_code == 202
    event_id = resp.json()["event_id"]

    events = bus.consume(count=10, block_ms=1)
    assert len(events) == 1
    stream_event = events[0]

    # Process the same stream message twice; the second call must be a no-op.
    process_event(stream_event.envelope, stream_event.message_id)
    process_event(stream_event.envelope, stream_event.message_id)

    recent = client.get("/events/recent", params={"limit": 200}).json()
    ours = [ev for ev in recent if ev["id"] == event_id]
    assert len(ours) == 1


def test_drift_current_data_sees_processed_text_events(
    client: TestClient, bus: RedisStreamsEventBus
) -> None:
    from safetyops.monitoring.drift import _load_current_data

    marker = f"drift-{uuid.uuid4()}"
    client.post("/events/text", json={"text": f"Chemical spill in lab ({marker})"})
    _drain_and_process(bus)

    df = _load_current_data()
    assert (df["text"].str.contains(marker)).any()
