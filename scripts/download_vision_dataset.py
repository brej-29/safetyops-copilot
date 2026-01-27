from __future__ import annotations

from pathlib import Path


INSTRUCTIONS_PATH = Path("data/vision/README.md")


INSTRUCTIONS_TEXT = """\
# Vision PPE Dataset Instructions

This project is designed to work with a YOLO-format Personal Protective Equipment (PPE)
detection dataset. To keep the repository lightweight and friendly to free tiers,
**no large image datasets are committed**.

## Recommended approach

1. Create a free Kaggle account (https://www.kaggle.com/) if you do not already have one.
2. Search for a PPE detection dataset, for example:
   - "PPE Detection" / "Hardhat Workers" / "Safety Helmet" datasets.
3. Download the dataset locally and unpack it.

You are looking for either:

- A dataset that is already in **YOLO format** (images plus `labels/` text files), or
- A dataset that provides bounding box annotations that can be converted to YOLO format.

## Expected layout

Place your prepared dataset under:

- `data/vision/ppe/images/`  (JPEG/PNG images)
- `data/vision/ppe/labels/`  (YOLO txt label files)

For example:

- `data/vision/ppe/images/img_0001.jpg`
- `data/vision/ppe/labels/img_0001.txt`

Each label file should contain one detection per line:

`<class_id> <x_center> <y_center> <width> <height>`

All coordinates are normalized to `[0, 1]` relative to image width/height.

## Using with YOLOv8

Once your dataset is prepared, you can:

- Run the optional training script:

  ```bash
  python -m safetyops.ml.vision.train \\
      --data-root data/vision/ppe \\
      --epochs 10
  ```

  (Recommended to run in a free GPU environment such as Google Colab; see
  `docs/vision_colab.md`.)

- Or simply rely on the default pretrained YOLOv8n weights (`yolov8n.pt`) for
  inference, which are automatically downloaded by the `ultralytics` library.

## Tiny samples for tests

To keep the repository portable, tests and examples use **stubbed detections**
when real images are not available. If you wish, you can add a **very small**
hand-crafted sample (a few images) under `data/sample/vision/` for local
experimentation, but this is optional and should remain small.
"""


def main() -> None:
    """Create lightweight instructions for obtaining a PPE dataset.

    This script is intentionally conservative: it does *not* attempt to
    download large datasets automatically (which often require authentication
    or have licensing restrictions). Instead, it writes a clear README that
    explains how to obtain and lay out a YOLO-format PPE dataset.
    """
    INSTRUCTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not INSTRUCTIONS_PATH.exists():
        INSTRUCTIONS_PATH.write_text(INSTRUCTIONS_TEXT, encoding="utf-8")
        print(f"Wrote vision dataset instructions to {INSTRUCTIONS_PATH}")
    else:
        print(f"Instructions already exist at {INSTRUCTIONS_PATH}")


if __name__ == "__main__":
    main()