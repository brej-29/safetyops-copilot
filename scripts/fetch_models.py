"""Fetch model artifacts at deploy/startup time.

- NLP: if SAFETYOPS_NLP_MODEL_HF_REPO is set (e.g. "your-user/safetyops-nlp")
  and no model is present locally, download it from the Hugging Face Hub into
  SAFETYOPS_NLP_MODEL_DIR.
- Vision: if SAFETYOPS_VISION_MODEL_PATH points at a missing file under
  models/, download the default PPE weights.

Every step is best-effort: on failure the runtime falls back to the rule-based
classifier / stub predictions, so a cold start never blocks the API.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def fetch_nlp_model() -> None:
    repo = os.getenv("SAFETYOPS_NLP_MODEL_HF_REPO")
    model_dir = Path(os.getenv("SAFETYOPS_NLP_MODEL_DIR", "models/nlp"))
    if not repo:
        logger.info("SAFETYOPS_NLP_MODEL_HF_REPO not set; skipping NLP model fetch")
        return
    if (model_dir / "config.json").exists():
        logger.info("NLP model already present at %s", model_dir)
        return
    try:
        from huggingface_hub import snapshot_download

        logger.info("Downloading NLP model %s -> %s", repo, model_dir)
        snapshot_download(repo_id=repo, local_dir=str(model_dir))
        logger.info("NLP model downloaded")
    except Exception:
        logger.exception("Failed to fetch NLP model; runtime will use the rule-based fallback")


def fetch_vision_model() -> None:
    model_path = Path(os.getenv("SAFETYOPS_VISION_MODEL_PATH", "models/vision/ppe_yolov8n.pt"))
    if model_path.exists():
        logger.info("Vision model already present at %s", model_path)
        return
    if "models" not in model_path.parts:
        # Bare names like yolov8n.pt are auto-downloaded by ultralytics itself.
        logger.info("Vision model path %s is not repo-managed; skipping", model_path)
        return
    try:
        from download_vision_model import DEFAULT_URL  # type: ignore[import]
        import urllib.request

        model_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading vision model -> %s", model_path)
        urllib.request.urlretrieve(DEFAULT_URL, model_path)
        logger.info("Vision model downloaded")
    except Exception:
        logger.exception("Failed to fetch vision model; runtime will use stub predictions")


if __name__ == "__main__":
    fetch_nlp_model()
    fetch_vision_model()
