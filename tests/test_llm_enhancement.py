from __future__ import annotations

from typing import Any, Dict

import httpx

import safetyops.agents.triage_graph as triage_graph
from safetyops.agents.triage_graph import _enhance_with_llm


class _SettingsStub:
    llm_base_url = "https://api.groq.com/openai"
    llm_api_key = "test-key"
    llm_model = "llama-3.3-70b-versatile"
    ollama_base_url = None
    ollama_model = None


class _RecordingClient:
    """Stands in for httpx.Client; records constructor args and the request."""

    last_init: Dict[str, Any] = {}
    last_request: Dict[str, Any] = {}
    response_content = "Rewritten report"

    def __init__(self, **kwargs) -> None:
        type(self).last_init = kwargs

    def post(self, path: str, json: Dict[str, Any]) -> httpx.Response:
        type(self).last_request = {"path": path, "json": json}
        return httpx.Response(
            status_code=200,
            json={
                "choices": [
                    {"message": {"content": type(self).response_content}}
                ]
            },
            request=httpx.Request("POST", "http://test"),
        )


def test_enhance_with_llm_calls_openai_compatible_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(triage_graph, "settings", _SettingsStub())
    monkeypatch.setattr(triage_graph.httpx, "Client", _RecordingClient)

    state = _enhance_with_llm({"report_markdown": "# Original report"})

    assert state["report_markdown"] == "Rewritten report"
    assert _RecordingClient.last_init["base_url"] == "https://api.groq.com/openai"
    assert _RecordingClient.last_init["headers"]["Authorization"] == "Bearer test-key"
    assert _RecordingClient.last_request["path"] == "/v1/chat/completions"
    assert _RecordingClient.last_request["json"]["model"] == "llama-3.3-70b-versatile"


def test_enhance_with_llm_no_auth_header_without_key(monkeypatch) -> None:
    class NoKeySettings(_SettingsStub):
        llm_api_key = None

    monkeypatch.setattr(triage_graph, "settings", NoKeySettings())
    monkeypatch.setattr(triage_graph.httpx, "Client", _RecordingClient)

    _enhance_with_llm({"report_markdown": "# Original report"})

    assert "Authorization" not in _RecordingClient.last_init["headers"]


def test_enhance_with_llm_keeps_report_on_failure(monkeypatch) -> None:
    class FailingClient:
        def __init__(self, **kwargs) -> None:
            pass

        def post(self, path, json):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(triage_graph, "settings", _SettingsStub())
    monkeypatch.setattr(triage_graph.httpx, "Client", FailingClient)

    state = _enhance_with_llm({"report_markdown": "# Original report"})
    assert state["report_markdown"] == "# Original report"


def test_enhance_with_llm_skips_when_unconfigured(monkeypatch) -> None:
    class UnsetSettings(_SettingsStub):
        llm_base_url = None
        llm_model = None

    monkeypatch.setattr(triage_graph, "settings", UnsetSettings())
    state = _enhance_with_llm({"report_markdown": "# Original report"})
    assert state["report_markdown"] == "# Original report"
