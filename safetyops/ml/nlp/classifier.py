from __future__ import annotations

from safetyops.domain.predictions import TextClassificationPrediction


def classify_incident(text: str) -> TextClassificationPrediction:
    """Classify an incident text into a category and severity.

    This is a rule-based baseline intended as a stub for v1. It can be
    replaced by a learned model in later iterations.
    """
    lowered = text.lower()

    if any(word in lowered for word in ["fall", "slip", "trip"]):
        category = "fall"
    elif any(word in lowered for word in ["electric", "voltage", "wire", "shock"]):
        category = "electrical"
    elif any(word in lowered for word in ["fire", "smoke", "burn"]):
        category = "fire"
    elif any(word in lowered for word in ["chemical", "spill", "acid", "gas"]):
        category = "chemical"
    else:
        category = "other"

    if any(word in lowered for word in ["fatal", "critical", "severe", "hospital"]):
        severity = "high"
        confidence = 0.95
    elif any(word in lowered for word in ["injury", "hurt", "fracture", "shock"]):
        severity = "medium"
        confidence = 0.85
    else:
        severity = "low"
        confidence = 0.7

    return TextClassificationPrediction(category=category, severity=severity, confidence=confidence)