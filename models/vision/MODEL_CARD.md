# SafetyOps Copilot Vision Model (YOLOv8 PPE)

## Overview

This directory is intended to hold configuration and notes for the YOLOv8 model
used for **PPE (Personal Protective Equipment) detection** in SafetyOps Copilot.

By default, the system uses the publicly available:

- Base model: `yolov8n.pt` (Ultralytics YOLOv8 nano)

The model is downloaded automatically by the `ultralytics` library on first use
and is **not** committed to the repository.

## Task

The YOLOv8 model detects objects such as:

- `person`
- PPE-related classes (depending on the chosen dataset and training):
  - `helmet` / `hardhat`
  - `vest` / `jacket`
  - Other site-specific PPE classes

The SafetyOps wrapper uses these detections to estimate a **PPE compliance
score** for each image:

- `num_persons`: number of detected persons.
- `num_persons_with_ppe`: persons likely wearing required PPE.
- `compliance_score`: `num_persons_with_ppe / max(num_persons, 1)` clipped to `[0, 1]`.

## Training (optional)

For v1, the default setup relies on pretrained YOLOv8n weights. You can
optionally fine-tune on a PPE dataset.

Training entry point:

```bash
python -m safetyops.ml.vision.train \
    --data-root data/vision/ppe \
    --epochs 10
```

This script is designed for use in a **GPU environment** (e.g. Google Colab).
See:

- `docs/vision_colab.md` for a Colab-oriented walkthrough.
- `scripts/download_vision_dataset.py` for guidance on preparing a YOLO-format
  PPE dataset.

## Inference

The runtime wrapper is:

- `safetyops.ml.vision.infer.run_ppe_inference(image_path: str | None)`

Behavior:

- Lazily imports `ultralytics.YOLO`.
- Loads the weights configured via `SAFETYOPS_VISION_MODEL_PATH` (defaults to
  `yolov8n.pt`).
- Returns a `VisionPPEDetection` object with PPE compliance scores.
- If `ultralytics` or weights are unavailable, falls back to a deterministic
  stub so that tests and constrained environments still work.

## Limitations

- Pretrained YOLOv8n is **not** specialized for your site; it is a general
  object detector.
- PPE label coverage depends entirely on the dataset you choose for fine-tuning.
- Image-based assessments must always be supplemented with human review and
  site-specific policies.

## Responsible use

As with all vision-based safety tools:

- Treat outputs as **advisory** signals rather than ground truth.
- Validate performance on representative data before relying on it.
- Ensure privacy and compliance requirements for any captured imagery.