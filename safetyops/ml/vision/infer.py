from __future__ import annotations

from pathlib import Path
from typing import Optional

from safetyops.core.logging import get_logger
from safetyops.core.settings import settings
from safetyops.domain.predictions import VisionPPEDetection

logger = get_logger(__name__)

_YOLO_MODEL = None
_LOAD_FAILED = False


def _load_model():
    """Lazily load the YOLO model if available.

    This mirrors the behavior in the original yolo.py stub but centralizes
    configuration around SAFETYOPS_VISION_MODEL_PATH so that weights can be
    swapped (e.g. fine-tuned PPE model). A failed load is cached so we don't
    retry (and log a warning) on every event.
    """
    global _YOLO_MODEL, _LOAD_FAILED
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL
    if _LOAD_FAILED:
        return None

    try:
        from ultralytics import YOLO  # type: ignore[import]
    except Exception:
        logger.warning(
            "ultralytics.YOLO not available; using stub PPE predictions",
            exc_info=False,
        )
        _LOAD_FAILED = True
        return None

    model_path = Path(settings.vision_model_path)
    try:
        _YOLO_MODEL = YOLO(str(model_path))
        logger.info(
            "Loaded YOLO model for PPE inference",
            extra={"model_path": str(model_path)},
        )
    except Exception:
        logger.warning(
            "Failed to load YOLO model; using stub PPE predictions",
            exc_info=True,
        )
        _LOAD_FAILED = True
        return None

    return _YOLO_MODEL


def _stub_ppe_detection() -> VisionPPEDetection:
    """Fallback PPE detection used when YOLO is unavailable.

    This ensures the worker and UI can still function in constrained
    environments and in CI.
    """
    return VisionPPEDetection(
        compliance_score=0.5,
        num_persons=1,
        num_persons_with_ppe=0,
    )


def run_ppe_inference(image_path: Optional[str]) -> VisionPPEDetection:
    """Run YOLO-based PPE inference, falling back to a stub if needed.

    The current heuristic is intentionally simple:
    - Count 'person' detections.
    - Count detections that look like helmets/hardhats or vests.
    - Estimate compliance_score = persons_with_ppe / max(persons, 1).
    """
    from safetyops.monitoring.metrics import model_inference_seconds

    model = _load_model()
    if model is None or not image_path:
        logger.info(
            "Using stub PPE inference",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()

    image_path_obj = Path(image_path)
    if not image_path_obj.exists():
        logger.warning(
            "Image path does not exist; using stub PPE inference",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()

    try:
        with model_inference_seconds.labels(model="vision").time():
            results = model(str(image_path_obj), verbose=False)
    except Exception:
        logger.exception(
            "Error during YOLO PPE inference; falling back to stub",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()

    try:
        result = results[0]
    except Exception:
        logger.warning(
            "Unexpected YOLO results structure; falling back to stub",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()

    try:
        names = result.names  # type: ignore[attr-defined]
        boxes = result.boxes  # type: ignore[attr-defined]
    except Exception:
        logger.warning(
            "YOLO result missing expected attributes; falling back to stub",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()

    # Supported label schemes:
    # - Hard-hat head detectors (e.g. keremberke/yolov8n-hard-hat-detection):
    #   each detection is a head labeled "Hardhat" or "NO-Hardhat".
    # - Person + equipment detectors (custom fine-tunes): separate "person",
    #   "helmet"/"hardhat", and "vest" classes.
    # - Person-only models (COCO): persons can be counted but PPE cannot be
    #   assessed, so compliance stays neutral.
    persons = 0
    ppe_heads = 0
    bare_heads = 0
    equipment = 0

    try:
        # ultralytics boxes.data is typically a tensor: [x1, y1, x2, y2, conf, cls]
        data = getattr(boxes, "data", None)
        if data is None:
            return _stub_ppe_detection()

        for row in data:
            try:
                cls_idx = int(row[-1].item())  # type: ignore[call-arg]
            except Exception:
                try:
                    cls_idx = int(row[-1])
                except Exception:
                    continue

            label = str(names.get(cls_idx, "")).lower()
            has_hat = "hardhat" in label or "helmet" in label
            is_negated = has_hat and ("no-" in label or "no_" in label or label.startswith("no "))

            if is_negated:
                bare_heads += 1
            elif has_hat:
                ppe_heads += 1
            elif "vest" in label:
                equipment += 1
            elif "person" in label:
                persons += 1
    except Exception:
        logger.exception(
            "Failed to parse YOLO detections; falling back to stub",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()

    if persons > 0:
        if ppe_heads + equipment > 0:
            # Person + equipment detector: approximate one PPE item per person.
            num_persons = persons
            num_with_ppe = min(persons, ppe_heads + equipment)
        else:
            logger.info(
                "Model detected persons but no PPE classes; compliance is neutral",
                extra={"image_path": image_path, "persons": persons},
            )
            return VisionPPEDetection(
                compliance_score=0.5,
                num_persons=persons,
                num_persons_with_ppe=0,
            )
    elif ppe_heads + bare_heads > 0:
        # Head detector: every detection is a person; hard-hat heads comply.
        num_persons = ppe_heads + bare_heads
        num_with_ppe = ppe_heads
    else:
        return _stub_ppe_detection()

    compliance_score = max(0.0, min(1.0, num_with_ppe / float(num_persons)))

    return VisionPPEDetection(
        compliance_score=compliance_score,
        num_persons=num_persons,
        num_persons_with_ppe=num_with_ppe,
    )