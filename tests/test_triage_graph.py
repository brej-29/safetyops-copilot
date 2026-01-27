from __future__ import annotations

from safetyops.agents.triage_graph import run_triage_workflow


def test_triage_graph_deterministic_without_llm(monkeypatch) -> None:
    # Disable any LLM calls to keep the path deterministic in tests.
    class DummySettings:
        ollama_base_url = None
        ollama_model = None

    monkeypatch.setattr(
        "safetyops.agents.triage_graph.settings",
        DummySettings(),
        raising=False,
    )

    state = run_triage_workflow(
        incident_id=None,
        text="Worker slipped on wet floor and suffered minor injury.",
        image_path=None,
    )

    assert state["incident_id"] == "ad-hoc"
    assert state["category"] in {"fall", "other"}
    assert state["severity"] in {"low", "medium", "high"}
    assert isinstance(state.get("risk_score"), int)
    assert "report_markdown" in state
    assert "# Incident Triage Brief" in state["report_markdown"]