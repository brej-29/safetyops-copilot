"""Unit tests for PPE detection aggregation across YOLO label schemes."""

from __future__ import annotations

import pytest

import safetyops.ml.vision.infer as vision_infer


class _FakeBoxes:
    def __init__(self, class_indices: list[int]) -> None:
        # Mimic ultralytics boxes.data rows: [x1, y1, x2, y2, conf, cls]
        self.data = [[0.0, 0.0, 1.0, 1.0, 0.9, float(idx)] for idx in class_indices]


class _FakeResult:
    def __init__(self, names: dict[int, str], class_indices: list[int]) -> None:
        self.names = names
        self.boxes = _FakeBoxes(class_indices)


class _FakeModel:
    def __init__(self, names: dict[int, str], class_indices: list[int]) -> None:
        self._result = _FakeResult(names, class_indices)

    def __call__(self, image_path: str, verbose: bool = False) -> list[_FakeResult]:
        return [self._result]


@pytest.fixture()
def sample_image(tmp_path):
    image = tmp_path / "img.jpg"
    image.write_bytes(b"fake")
    return str(image)


def _run_with_model(monkeypatch, model: _FakeModel, image_path: str):
    monkeypatch.setattr(vision_infer, "_load_model", lambda: model)
    return vision_infer.run_ppe_inference(image_path)


def test_hardhat_head_detector(monkeypatch, sample_image) -> None:
    # keremberke-style model: heads labeled Hardhat / NO-Hardhat
    names = {0: "Hardhat", 1: "NO-Hardhat"}
    model = _FakeModel(names, [0, 0, 1])  # 2 compliant heads, 1 bare head

    result = _run_with_model(monkeypatch, model, sample_image)
    assert result.num_persons == 3
    assert result.num_persons_with_ppe == 2
    assert result.compliance_score == pytest.approx(2 / 3)


def test_person_plus_equipment_detector(monkeypatch, sample_image) -> None:
    names = {0: "person", 1: "helmet", 2: "vest"}
    model = _FakeModel(names, [0, 0, 0, 1, 2])  # 3 persons, 1 helmet, 1 vest

    result = _run_with_model(monkeypatch, model, sample_image)
    assert result.num_persons == 3
    assert result.num_persons_with_ppe == 2
    assert result.compliance_score == pytest.approx(2 / 3)


def test_person_only_coco_model_is_neutral(monkeypatch, sample_image) -> None:
    names = {0: "person", 2: "car"}
    model = _FakeModel(names, [0, 0, 2])

    result = _run_with_model(monkeypatch, model, sample_image)
    assert result.num_persons == 2
    assert result.num_persons_with_ppe == 0
    assert result.compliance_score == 0.5


def test_no_detections_falls_back_to_stub(monkeypatch, sample_image) -> None:
    names = {0: "person"}
    model = _FakeModel(names, [])

    result = _run_with_model(monkeypatch, model, sample_image)
    assert result.model_dump() == vision_infer._stub_ppe_detection().model_dump()


def test_missing_image_uses_stub(monkeypatch) -> None:
    model = _FakeModel({0: "person"}, [0])
    monkeypatch.setattr(vision_infer, "_load_model", lambda: model)

    result = vision_infer.run_ppe_inference("does/not/exist.jpg")
    assert result.model_dump() == vision_infer._stub_ppe_detection().model_dump()
