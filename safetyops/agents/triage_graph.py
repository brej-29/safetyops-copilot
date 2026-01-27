from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from safetyops.core.logging import get_logger
from safetyops.core.settings import settings
from safetyops.db import EnrichedEvent, HourlyAggregate
from safetyops.db.session import get_session
from safetyops.domain.responses import CopilotTriageContextEvent
from safetyops.ml.nlp.classifier import classify_incident
from safetyops.ml.nlp.infer import predict_severity
from safetyops.runbooks import load_runbook_for_category

logger = get_logger(__name__)


class TriageState(TypedDict, total=False):
    incident_id: str
    text: str
    image_path: Optional[str]
    category: Optional[str]
    severity: Optional[str]
    risk_score: Optional[int]
    context_events: List[CopilotTriageContextEvent]
    aggregates: Dict[str, Any]
    playbook_markdown: str
    report_markdown: str


def _fetch_context(state: TriageState) -> TriageState:
    """Fetch recent related events and aggregates from the DB."""
    text = state.get("text") or ""
    baseline = classify_incident(text) if text else None
    category = state.get("category") or (baseline.category if baseline else None)
    severity = state.get("severity") or (baseline.severity if baseline else None)

    now = datetime.utcnow()
    window_start = now - timedelta(days=7)

    context_events: List[CopilotTriageContextEvent] = []
    aggregates: Dict[str, Any] = {"by_category_severity": {}, "recent_hours": []}

    with get_session() as session:
        # Recent events with same category (if known), otherwise all recent
        query = session.query(EnrichedEvent).filter(EnrichedEvent.created_at >= window_start)
        if category:
            query = query.filter(EnrichedEvent.category == category)
        query = query.order_by(EnrichedEvent.created_at.desc()).limit(20)
        rows = query.all()

        for row in rows:
            enrichment = row.enrichment or {}
            risk_score = enrichment.get("risk_score")
            context_events.append(
                CopilotTriageContextEvent(
                    id=row.id,
                    created_at=row.created_at,
                    category=row.category,
                    severity=row.severity,
                    risk_score=risk_score if isinstance(risk_score, int) else None,
                )
            )

        # Aggregates: counts by category, severity, hour over last 24h
        hour_start = now - timedelta(hours=24)
        hourly_rows = (
            session.query(HourlyAggregate)
            .filter(HourlyAggregate.date >= hour_start.date())
            .order_by(HourlyAggregate.date.desc(), HourlyAggregate.hour.desc())
            .limit(48)
            .all()
        )
        series = []
        for row in hourly_rows:
            ts = datetime.combine(row.date, datetime.min.time()).replace(hour=row.hour)
            series.append(
                {
                    "timestamp": ts.isoformat(),
                    "event_type": row.event_type,
                    "category": row.category,
                    "severity": row.severity,
                    "count": row.count,
                }
            )
            key = f"{row.category or 'unknown'}::{row.severity or 'unknown'}"
            aggregates["by_category_severity"].setdefault(key, 0)
            aggregates["by_category_severity"][key] += row.count

        aggregates["recent_hours"] = series

    state["category"] = category
    state["severity"] = severity
    state["context_events"] = context_events
    state["aggregates"] = aggregates
    return state


def _assess_risk(state: TriageState) -> TriageState:
    """Compute a simple risk score if not already set."""
    severity = state.get("severity") or "low"
    baseline_score = {"low": 40, "medium": 60, "high": 80}.get(severity, 40)

    # Boost based on recent aggregates for same category/severity
    category = state.get("category") or "other"
    key = f"{category}::{severity}"
    agg_counts = state.get("aggregates", {}).get("by_category_severity", {})
    volume = int(agg_counts.get(key, 0))
    volume_boost = min(20, volume * 2)

    risk_score = int(max(0, min(100, baseline_score + volume_boost)))
    state["risk_score"] = risk_score
    return state


def _plan_playbook(state: TriageState) -> TriageState:
    category = state.get("category") or "other"
    playbook_md = load_runbook_for_category(category)
    state["playbook_markdown"] = playbook_md
    return state


def _write_report(state: TriageState) -> TriageState:
    text = state.get("text") or ""
    category = state.get("category") or "other"
    severity = state.get("severity") or "low"
    risk_score = state.get("risk_score") or 0
    context_events = state.get("context_events", [])
    playbook_md = state.get("playbook_markdown", "")

    context_summary_lines = []
    for ev in context_events[:5]:
        risk_str = ev.risk_score if ev.risk_score is not None else "n/a"
        context_summary_lines.append(
            f"- [{ev.created_at.isoformat()}] "
            f"{ev.category or 'unknown'} / {ev.severity or 'unknown'} "
            f"(risk={risk_str})"
        )
    context_summary = (
        "\n".join(context_summary_lines)
        if context_summary_lines
        else "No closely related events in the last 7 days."
    )

    report = f"""# Incident Triage Brief

## What happened

- **Summary:** {text or 'No free-text description provided.'}
- **Category:** {category}
- **Severity:** {severity}
- **Risk score (0–100):** {risk_score}

## Context

Recent related events:

{context_summary}

## Likely contributing factors

- Repeated occurrences of similar incidents increase the site risk.
- Severity level `{severity}` suggests this incident should be reviewed promptly.
- PPE and procedural compliance should be verified against the runbook.

## Recommended immediate actions (today)

{playbook_md}

## Preventive actions (next 30 days)

- Review trends in similar incidents and update local training if needed.
- Verify that runbook steps are realistic and actually followed on site.
- Schedule a focused safety walkthrough in the affected area.
- Confirm that reporting and near-miss capture processes are working.

## Compliance and logging

- Log this incident in the official safety / EHS system with
  category `{category}` and severity `{severity}`.
- Attach any relevant photos, witness statements, and follow-up notes.
- Ensure evidence of completed corrective actions is recorded.
"""
    state["report_markdown"] = report
    return state


def _enhance_with_llm(state: TriageState) -> TriageState:
    """Optionally rewrite the report using a local LLM (Ollama).

    If no LLM is configured or the call fails, the original report is returned.
    """
    base_url = settings.ollama_base_url
    model = settings.ollama_model
    report_md = state.get("report_markdown") or ""
    if not base_url or not model or not report_md:
        return state

    try:
        client = httpx.Client(base_url=base_url, timeout=10.0)
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a safety operations assistant. Rewrite the following incident "
                        "report to be concise, clear, and action-oriented. Keep markdown structure."
                    ),
                },
                {
                    "role": "user",
                    "content": report_md,
                },
            ],
        }
        response = client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if content:
            state["report_markdown"] = content
    except Exception:
        logger.exception("LLM enhancement failed; returning base report unchanged")

    return state


# LangGraph-style state machine ------------------------------------------------

_graph = StateGraph(TriageState)
_graph.add_node("fetch_context", _fetch_context)
_graph.add_node("assess_risk", _assess_risk)
_graph.add_node("plan_playbook", _plan_playbook)
_graph.add_node("write_report", _write_report)
_graph.add_node("enhance_with_llm", _enhance_with_llm)

_graph.set_entry_point("fetch_context")
_graph.add_edge("fetch_context", "assess_risk")
_graph.add_edge("assess_risk", "plan_playbook")
_graph.add_edge("plan_playbook", "write_report")
_graph.add_edge("write_report", "enhance_with_llm")
_graph.add_edge("enhance_with_llm", END)

_triage_app = _graph.compile()


def run_triage_workflow(
    incident_id: Optional[str],
    text: Optional[str],
    image_path: Optional[str],
) -> TriageState:
    """Entry point used by the API and UI.

    - If incident_id is provided and found in the DB, we enrich the input text
      and metadata from the stored event.
    - If only text is provided, we classify and triage that text.
    """
    resolved_text = text or ""
    resolved_incident_id = incident_id or ""

    if incident_id and not text:
        with get_session() as session:
            row = session.query(EnrichedEvent).filter_by(id=incident_id).one_or_none()
            if row is not None:
                resolved_text = str(
                    row.enrichment.get("text")
                    or row.enrichment.get("summary")
                    or ""
                )
                resolved_incident_id = row.id

    if not resolved_text:
        resolved_text = "No description provided."

    # Initial severity prediction for the focal incident
    severity_pred = predict_severity(resolved_text)
    initial_state: TriageState = {
        "incident_id": resolved_incident_id or "ad-hoc",
        "text": resolved_text,
        "image_path": image_path,
        "category": severity_pred.category,
        "severity": severity_pred.severity,
    }

    # Execute the LangGraph state machine
    final_state = _triage_app.invoke(initial_state)
    return final_state