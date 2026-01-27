from __future__ import annotations

from typing import Optional

from safetyops.domain.predictions import VisionPPEDetection
from safetyops.ml.vision.infer import run_ppe_inference as _run_ppe_inference


def run_ppe_inference(image_path: Optional[str]) -> VisionPPEDetection:
    """Backward-compatible wrapper that delegates to the new inference module.

    Existing imports of `safetyops.ml.vision.yolo.run_ppe_inference` will
    continue to work, while the actual implementation now lives in
    `safetyops.ml.vision.infer`.
    """
    return _run_ppe_inference(image_path)