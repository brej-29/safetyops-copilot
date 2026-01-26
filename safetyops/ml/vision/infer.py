from __future__ import annotations

from pathlib import Path
from typing import Optional

from safetyops.core.logging import get_logger
from safetyops.core.settings import settings
from safetyops.domain.predictions import VisionPPEDetection

logger = get_logger(__name__)

_YOLO_MODEL = None


def _load_model():
    """Lazily load the YOLO model if available.

    This mirrors the behavior in the original yolo.py stub but centralizes
    configuration around SAFETYOPS_VISION_MODEL_PATH so that weights can be
    swapped (e.g. fine-tuned PPE model).
    """
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    try:
        from ultralytics import YOLO  # type: ignore[import]
    except Exception:
        logger.warning(
            "ultralytics.YOLO not available; using stub PPE predictions",
            exc_info=False,
        )
        _YOLO_MODEL = None
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
        _YOLO_MODEL = None

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

    timer = model_inference_seconds.labels(model="vision").time()
    try:
        results = model(str(image_path_obj), verbose=False)
    except Exception:
        timer.observe(0.0)
        logger.exception(
            "Error during YOLO PPE inference; falling back to stub",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()
    finally:
        timer.__exit__(None, None, None)

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

    persons = 0
    persons_with_ppe = 0

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
            is_person = "person" in label
            is_helmet = any(x in label for x in ["helmet", "hardhat"])
            is_vest = "vest" in label

            if is_person:
                persons += 1
            if is_person and (is_helmet or is_vest):
                persons_with_ppe += 1
    except Exception:
        logger.exception(
            "Failed to parse YOLO detections; falling back to stub",
            extra={"image_path": image_path},
        )
        return _stub_ppe_detection()

    if persons <= 0:
        return _stub_ppe_detection()

    compliance_score = max(0.0, min(1.0, persons_with_ppe / float(persons)))

    return VisionPPEDetection(
        compliance_score=compliance_score,
        num_persons=persons,
        num_persons_with_ppe=persons_with_ppe,
    )