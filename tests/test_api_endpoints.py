from __future__ import annotations

import fakeredis
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from safetyops.core.settings import settings
from safetyops.streaming import RedisStreamsEventBus


@pytest.fixture()
def fake_redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


@pytest.fixture()
def client(monkeypatch, fake_redis) -> TestClient:
    bus = RedisStreamsEventBus(redis_client=fake_redis)
    monkeypatch.setattr(api_main, "_event_bus", bus)
    with TestClient(api_main.app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_create_text_event_publishes_to_stream(client: TestClient, fake_redis) -> None:
    before = fake_redis.xlen(settings.stream_key)
    resp = client.post(
        "/events/text",
        json={"text": "Worker slipped on wet floor", "metadata": {"source": "test"}},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["event_id"]
    assert body["message_id"]
    assert fake_redis.xlen(settings.stream_key) == before + 1


def test_create_vision_event_with_path(client: TestClient, fake_redis) -> None:
    before = fake_redis.xlen(settings.stream_key)
    resp = client.post(
        "/events/vision",
        data={"image_path": "data/sample/sample_ppe_image.jpg"},
    )
    assert resp.status_code == 202
    assert resp.json()["image_path"] == "data/sample/sample_ppe_image.jpg"
    assert fake_redis.xlen(settings.stream_key) == before + 1


def test_recent_events_returns_list(client: TestClient) -> None:
    resp = client.get("/events/recent")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_aggregates_rejects_non_positive_days(client: TestClient) -> None:
    resp = client.get("/aggregates/summary", params={"days": 0})
    assert resp.status_code == 400


def test_copilot_triage_requires_input(client: TestClient) -> None:
    resp = client.post("/copilot/triage", json={})
    assert resp.status_code == 400


def test_copilot_triage_with_text(client: TestClient) -> None:
    resp = client.post(
        "/copilot/triage",
        json={"text": "Worker slipped from a ladder and fractured an arm."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "fall"
    assert body["severity"] in {"low", "medium", "high"}
    assert 0 <= body["risk_score"] <= 100
    assert "# Incident Triage Brief" in body["report_markdown"]
