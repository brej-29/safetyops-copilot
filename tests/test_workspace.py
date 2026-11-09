from __future__ import annotations

import fakeredis
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api import workspace
from safetyops.db import init_db
from safetyops.domain.assessment import assess_observation
from safetyops.streaming import RedisStreamsEventBus


@pytest.fixture()
def clients(monkeypatch):
    init_db()
    workspace._windows.clear()
    monkeypatch.setattr(
        api_main, "_event_bus", RedisStreamsEventBus(redis_client=fakeredis.FakeRedis())
    )
    with TestClient(api_main.app) as a, TestClient(api_main.app) as b:
        a.post("/api/workspace")
        b.post("/api/workspace")
        yield a, b
        a.delete("/api/workspace")
        b.delete("/api/workspace")


def observe(client, text="A worker slipped on the access platform and suffered a fracture."):
    response = client.post(
        "/api/workspace/observations", json={"text": text, "location": "North site"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def action(client, oid):
    return client.post(
        "/api/workspace/actions",
        json={
            "observation_id": oid,
            "title": "Verify controls and document inspection",
            "owner": "Site lead",
            "due_date": "2026-11-20",
        },
    )


def test_workspace_isolation_cookie_and_no_cache(clients):
    a, b = clients
    row = observe(a)
    assert a.get("/api/workspace").json()["observations"][0]["id"] == row["id"]
    assert b.get("/api/workspace").json()["observations"] == []
    assert action(b, row["id"]).status_code == 404
    assert a.get("/api/workspace").headers["cache-control"] == "no-store"
    assert "credential" not in a.get("/api/workspace").text
    cookie = a.post("/api/workspace").json()
    assert set(cookie) == {"id"}


def test_action_closure_revision_and_audit(clients):
    a, b = clients
    row = observe(a)
    saved = action(a, row["id"]).json()
    path = "/api/workspace/actions/" + saved["id"]
    assert (
        b.patch(
            path, json={"status": "closed", "revision": 1, "closure_note": "Verified"}
        ).status_code
        == 404
    )
    assert a.patch(path, json={"status": "closed", "revision": 1}).status_code == 422
    closed = a.patch(
        path,
        json={
            "status": "closed",
            "revision": 1,
            "closure_note": "Inspection completed; verification recorded in site log.",
        },
    )
    assert closed.status_code == 200
    assert closed.json()["revision"] == 2
    assert closed.json()["history"][-1]["status"] == "closed"
    assert a.patch(path, json={"status": "open", "revision": 1}).status_code == 409
    assert a.get("/api/workspace").json()["actions"][0]["closure_note"].startswith("Inspection")


def test_recurrence_scoped_and_persistence(clients):
    a, b = clients
    first = observe(a)
    second = observe(a)
    other = observe(b)
    assert second["assessment"]["risk_score"] == first["assessment"]["risk_score"] + 3
    assert other["assessment"]["score_breakdown"]["related_observations_7d"] == 0
    assert len(a.get("/api/workspace").json()["observations"]) == 2


def test_origin_validation_and_deletion(clients):
    a, _ = clients
    assert (
        a.post(
            "/api/workspace/observations",
            headers={"Origin": "https://evil.example"},
            json={"text": "A sufficiently detailed observation"},
        ).status_code
        == 403
    )
    assert a.post("/api/workspace", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert a.post("/api/workspace/observations", json={"text": " " * 30}).status_code == 422
    observe(a)
    assert a.delete("/api/workspace").status_code == 204
    assert a.get("/api/workspace").status_code == 401


def test_unauthenticated_workspace_read():
    client = TestClient(api_main.app)
    assert client.get("/api/workspace").status_code == 401


def test_explainable_floor_and_bounded_priority():
    result = assess_observation("A worker was unconscious after a fall.", recurrence=100)
    assert result["severity"] == "high"
    assert result["risk_score"] == 100
    assert result["model_source"] == "rules"
    assert result["model_confidence"] is None
    assert result["review_required"] is True
    assert result["score_breakdown"]["recurrence_points"] == 15


def test_public_pages_and_crawl_boundaries():
    client = TestClient(api_main.app)
    for path in ("/", "/app", "/guides/incident-triage", "/guides/shift-handover", "/privacy"):
        response = client.get(path)
        assert response.status_code == 200
        assert "<h1" in response.text
    assert "noindex" in client.get("/app").headers["x-robots-tag"]
    assert "/app" not in client.get("/sitemap.xml").text
    assert "Disallow: /api/" in client.get("/robots.txt").text
    assert "model_source" in client.get("/llms.txt").text
    assert client.get("/assets/unknown").status_code == 404


def test_public_workspace_rate_limit(clients):
    a, _ = clients
    workspace._windows.clear()
    for _ in range(40):
        assert a.post("/api/workspace").status_code == 200
    assert a.post("/api/workspace").status_code == 429
    workspace._windows.clear()


def test_cloud_cookie_is_secure_behind_http_proxy(monkeypatch):
    init_db()
    workspace._windows.clear()
    monkeypatch.setattr(workspace.settings, "deploy_mode", "cloud")
    client = TestClient(api_main.app, base_url="http://testserver")
    response = client.post("/api/workspace")
    assert response.status_code == 200
    assert "; Secure" in response.headers["set-cookie"]
    assert "; HttpOnly" in response.headers["set-cookie"]


def test_first_save_does_not_wait_for_optional_model(monkeypatch):
    import safetyops.ml.nlp.infer as inference

    monkeypatch.setattr(inference, "_MODEL", None)
    monkeypatch.setattr(inference, "_TOKENIZER", None)

    def forbidden_load():
        raise AssertionError("Public first save must not load a model synchronously")

    monkeypatch.setattr(inference, "_load_model", forbidden_load)
    result = assess_observation(
        "A worker slipped on the access platform.", allow_model_loading=False
    )
    assert result["model_source"] == "rules"
    assert result["review_required"] is True
