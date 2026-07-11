"""Upload the fine-tuned NLP model to the Hugging Face Hub.

Usage:
    python scripts/upload_nlp_model.py --repo your-user/safetyops-nlp-severity

Auth: uses HF_TOKEN if set, otherwise the token cached by
`huggingface-cli login` / `hf auth login` (must have write scope).

Uploads the contents of models/nlp (excluding training checkpoints/logs) to a
model repo, creating it if needed. Deployments then set
SAFETYOPS_NLP_MODEL_HF_REPO to pull it at startup (scripts/fetch_models.py).
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", required=True, help="Hub repo id, e.g. user/safetyops-nlp-severity"
    )
    parser.add_argument("--model-dir", default="models/nlp")
    parser.add_argument("--private", action="store_true", help="Create the repo as private")
    args = parser.parse_args()

    from huggingface_hub import get_token

    token = os.getenv("HF_TOKEN") or get_token()
    if not token:
        raise SystemExit(
            "No Hugging Face credentials found. Run `hf auth login` or set HF_TOKEN."
        )

    model_dir = Path(args.model_dir)
    if not (model_dir / "config.json").exists():
        raise SystemExit(f"No trained model found at {model_dir}. Run training first.")

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=args.repo, repo_type="model", private=args.private, exist_ok=True)
    api.upload_folder(
        repo_id=args.repo,
        folder_path=str(model_dir),
        ignore_patterns=["hf_runs/*", "logs/*", "*.bin.lock", "eval_results.json"],
    )
    logger.info("Uploaded %s to https://huggingface.co/%s", model_dir, args.repo)


if __name__ == "__main__":
    main()
