"""Download PPE-capable YOLOv8 weights for vision inference.

Fetches a community hard-hat detection model from Hugging Face
(keremberke/yolov8n-hard-hat-detection, labels: Hardhat / NO-Hardhat) and
stores it under models/vision/. Point SAFETYOPS_VISION_MODEL_PATH at the
downloaded file to enable real PPE compliance scoring:

    SAFETYOPS_VISION_MODEL_PATH=models/vision/ppe_yolov8n.pt

Without PPE-capable weights, the default COCO model can count persons but
cannot see hard hats, so compliance falls back to a neutral score.
"""

from __future__ import annotations

import argparse
import logging
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_URL = (
    "https://huggingface.co/keremberke/yolov8n-hard-hat-detection/resolve/main/best.pt"
)
DEFAULT_OUT = Path("models/vision/ppe_yolov8n.pt")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", type=str, default=DEFAULT_URL)
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        logger.info("Model already present; skipping download: %s", out_path)
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading PPE model from %s", args.url)
    urllib.request.urlretrieve(args.url, out_path)
    logger.info("Saved PPE model to %s (%d bytes)", out_path, out_path.stat().st_size)


if __name__ == "__main__":
    main()
