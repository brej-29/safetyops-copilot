from __future__ import annotations

import argparse
from pathlib import Path

from safetyops.core.logging import get_logger
from safetyops.core.settings import settings

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optional YOLOv8 PPE fine-tuning script.")
    parser.add_argument(
        "--data-root",
        type=str,
        required=True,
        help="Path to YOLO-format dataset root with `images/` and `labels/` subdirs.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs.",
    )
    parser.add_argument(
        "--img-size",
        type=int,
        default=640,
        help="Image size for training.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size.",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="yolov8n.pt",
        help="Base YOLOv8 weights to fine-tune (e.g. yolov8n.pt).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path(settings.artifacts_dir) / "vision"),
        help="Directory to store training outputs/checkpoints.",
    )
    return parser.parse_args()


def main() -> None:
    """Launch YOLOv8 training.

    This is intentionally a thin wrapper around Ultralytics' training API and
    is meant to be run in a GPU environment (e.g. Google Colab). It is not
    used in CI.
    """
    args = parse_args()

    try:
        from ultralytics import YOLO  # type: ignore[import]
    except Exception:
        logger.error(
            "ultralytics is not installed. Install it with `pip install ultralytics` "
            "and run this script in an environment with GPU support.",
        )
        raise

    data_root = Path(args.data_root)
    if not data_root.exists():
        raise FileNotFoundError(f"Data root {data_root} does not exist")

    images_dir = data_root / "images"
    labels_dir = data_root / "labels"
    if not images_dir.exists() or not labels_dir.exists():
        raise FileNotFoundError(
            f"Expected YOLO dataset structure under {data_root}: images/ and labels/ directories."
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Starting YOLOv8 training",
        extra={
            "data_root": str(data_root),
            "weights": args.weights,
            "epochs": args.epochs,
            "img_size": args.img_size,
            "batch_size": args.batch_size,
            "output_dir": str(output_dir),
        },
    )

    # Ultralytics expects a YAML config or a dict-like `data` argument. For a
    # simple setup we can pass a dict directly.
    data_config = {
        "path": str(data_root),
        "train": "images",
        "val": "images",
        "names": [],  # will be inferred from labels if available
    }

    model = YOLO(args.weights)
    model.train(
        data=data_config,
        epochs=args.epochs,
        imgsz=args.img_size,
        batch=args.batch_size,
        project=str(output_dir),
        name="ppe_yolov8",
    )

    logger.info(
        "Completed YOLOv8 training run",
        extra={"output_dir": str(output_dir)},
    )


if __name__ == "__main__":
    main()