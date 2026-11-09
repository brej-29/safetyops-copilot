"""Explainable assessment shared by the website and MCP tools."""

from __future__ import annotations

import re

from safetyops.ml.nlp.infer import predict_severity
from safetyops.runbooks import load_runbook_for_category

RULE_VERSION = "2026-11-09.1"
HIGH_SIGNALS = {
    "fatal": "fatal outcome mentioned",
    "unconscious": "loss of consciousness mentioned",
    "hospital": "hospital treatment mentioned",
    "severe": "severe harm mentioned",
    "electrocution": "electrocution mentioned",
    "explosion": "explosion mentioned",
    "critical": "critical condition mentioned",
}
MEDIUM_SIGNALS = {"injury", "injured", "fracture", "shock", "burn", "bleeding"}
FOLLOW_UP = {
    "fall": "Review access, housekeeping and fall-prevention controls",
    "electrical": "Arrange a competent-person review of electrical controls",
    "fire": "Review fire prevention and the site response procedure",
    "chemical": "Review chemical handling controls with the responsible lead",
    "ppe_noncompliance": "Verify suitable PPE and document the follow-up inspection",
    "other": "Review the observation and agree corrective measures",
}


def assess_observation(text: str, recurrence: int = 0, *, allow_model_loading: bool = True) -> dict:
    prediction = predict_severity(text, allow_model_loading=allow_model_loading)
    words = set(re.findall(r"[a-z]+", text.lower()))
    reasons = [reason for word, reason in HIGH_SIGNALS.items() if word in words]
    floor = "high" if reasons else "medium" if words & MEDIUM_SIGNALS else "low"
    order = {"low": 0, "medium": 1, "high": 2}
    severity = max((prediction.severity, floor), key=order.get)
    category = prediction.category
    if category == "other" and words & {"ppe", "hardhat", "helmet", "vest"}:
        category = "ppe_noncompliance"
    source = getattr(prediction, "model_source", "rules")
    base = {"low": 25, "medium": 55, "high": 85}[severity]
    recurrence = max(0, recurrence)
    boost = min(15, recurrence * 3)
    if not reasons:
        reasons = ["Text severity prediction; review against the actual site conditions"]
    return {
        "category": category,
        "severity": severity,
        "risk_score": base + boost,
        "model_source": source,
        "model_confidence": prediction.confidence if source == "distilbert" else None,
        "rule_version": RULE_VERSION,
        "reasons": reasons,
        "score_breakdown": {
            "severity_points": base,
            "recurrence_points": boost,
            "related_observations_7d": recurrence,
        },
        "suggested_action": FOLLOW_UP.get(category, FOLLOW_UP["other"]),
        "runbook_markdown": load_runbook_for_category(category),
        "review_required": True,
        "limitations": (
            "Draft decision support. Priority is a heuristic, not an accident probability. "
            "A person must review the site conditions and local procedures."
        ),
    }
