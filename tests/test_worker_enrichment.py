from __future__ import annotations

from safetyops.ml.nlp.classifier import classify_incident
from safetyops.ml.vision import yolo


def test_classify_incident_rule_based() -> None:
    pred_fall = classify_incident("Worker slipped and fell from ladder")
    assert pred_fall.category == "fall"
    assert pred_fall.severity in {"low", "medium", "high"}
    assert 0.0 <= pred_fall.confidence <= 1.0

    pred_fire = classify_incident("Small fire in storage area, extinguished quickly")
    assert pred_fire.category == "fire"


def test_run_ppe_inference_stub(monkeypatch) -> None:
    # Avoid loading YOLO weights in tests by forcing the stub path.
    monkeypatch.setattr(yolo, "_load_model", lambda: None)
    result = yolo.run_ppe_inference(image_path=None)

    assert 0.0 <= result.compliance_score <= 1.0
    assert result.num_persons >= 0
    assert result.num_persons_with_ppe >= 0