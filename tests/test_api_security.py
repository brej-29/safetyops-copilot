from __future__ import annotations

import fakeredis
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.security import reset_rate_limiter
from safetyops.core.settings import settings
from safetyops.streaming import RedisStreamsEventBus


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    bus = RedisStreamsEventBus(redis_client=fakeredis.FakeRedis())
    monkeypatch.setattr(api_main, "_event_bus", bus)
    reset_rate_limiter()
    with TestClient(api_main.app) as test_client:
        yield test_client
    reset_rate_limiter()


PAYLOAD = {"text": "Worker slipped near the dock"}


def test_write_endpoints_open_by_default(client: TestClient) -> None:
    resp = client.post("/events/text", json=PAYLOAD)
    assert resp.status_code == 202


def test_api_key_required_when_configured(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_key", "secret-key")

    assert client.post("/events/text", json=PAYLOAD).status_code == 401
    assert (
        client.post(
            "/events/text", json=PAYLOAD, headers={"X-API-Key": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/events/text", json=PAYLOAD, headers={"X-API-Key": "secret-key"}
        ).status_code
        == 202
    )


def test_api_key_does_not_gate_read_endpoints(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_key", "secret-key")
    assert client.get("/health").status_code == 200
    assert client.get("/events/recent").status_code == 200


def test_rate_limit_returns_429(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)

    statuses = [client.post("/events/text", json=PAYLOAD).status_code for _ in range(4)]
    assert statuses[:3] == [202, 202, 202]
    assert statuses[3] == 429


def test_rate_limit_covers_copilot_triage(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)

    first = client.post("/copilot/triage", json={"text": "Small fire near exit"})
    second = client.post("/copilot/triage", json={"text": "Small fire near exit"})
    assert first.status_code == 200
    assert second.status_code == 429
