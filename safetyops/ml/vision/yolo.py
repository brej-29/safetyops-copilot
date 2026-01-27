from __future__ import annotations

from typing import Optional

from safetyops.domain.predictions import VisionPPEDetection


def run_ppe_inference(image_path: Optional[str]) -> VisionPPEDetection:
    """Backward-compatible wrapper that delegates to the new inference module.

    Existing imports of `safetyops.ml.vision.yolo.run_ppe_inference` will
    continue to work, while the actual implementation now lives in
    `safetyops.ml.vision.infer`.
    """
    # Import inside the function so that tests can freely monkeypatch
    # safetyops.ml.vision.infer without interfering with module import order.
    from safetyops.ml.vision.infer import run_ppe_inference as _run  # type: ignore[import]

    return _run(image_path)