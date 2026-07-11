# SafetyOps Copilot Vision Model (YOLOv8 PPE)

## Overview

This directory holds the PPE detection weights used by SafetyOps Copilot.

The recommended model is a community hard-hat detector:

- Model: [`keremberke/yolov8n-hard-hat-detection`](https://huggingface.co/keremberke/yolov8n-hard-hat-detection)
- Architecture: YOLOv8 nano (~6 MB)
- Classes: `Hardhat`, `NO-Hardhat` (each detection is a worker's head)
- Training data: the public [hard-hat detection dataset](https://huggingface.co/datasets/keremberke/hard-hat-detection)
  (~5k construction-site images)
- Reported by the model author: mAP@0.5 ≈ 0.811 on the dataset's validation split

Download it with:

```bash
python scripts/download_vision_model.py
# then point the runtime at it:
export SAFETYOPS_VISION_MODEL_PATH=models/vision/ppe_yolov8n.pt
```

Weights are **not** committed to the repository.

## Task and compliance scoring

The runtime wrapper (`safetyops.ml.vision.infer.run_ppe_inference`) supports
three label schemes and derives a PPE compliance estimate from whichever the
loaded weights provide:

1. **Hard-hat head detectors** (recommended, e.g. the model above):
   - `num_persons` = detected heads (`Hardhat` + `NO-Hardhat`)
   - `num_persons_with_ppe` = `Hardhat` detections
2. **Person + equipment detectors** (custom fine-tunes with separate
   `person`, `helmet`/`hardhat`, `vest` classes):
   - compliance approximates one PPE item per detected person
3. **Person-only models** (COCO `yolov8n.pt`): persons are counted but PPE
   cannot be assessed, so `compliance_score` stays neutral at `0.5`.

In all cases: `compliance_score = num_persons_with_ppe / max(num_persons, 1)`,
clipped to `[0, 1]`. The worker maps compliance to severity
(`>= 0.8 low`, `>= 0.5 medium`, otherwise `high`).

## Fine-tuning (optional)

To fine-tune YOLOv8 on your own PPE dataset (GPU recommended, e.g. Colab):

```bash
python -m safetyops.ml.vision.train --data-root data/vision/ppe --epochs 10
```

See `docs/vision_colab.md` and `scripts/download_vision_dataset.py`.

## Fallback behavior

- `ultralytics` missing, weights missing, or load failure → deterministic stub
  prediction (`compliance_score=0.5`), logged once (failed loads are cached).
- Missing image path → stub prediction.

Aggregation logic is unit-tested in `tests/test_vision_aggregation.py`.

## Limitations

- The hard-hat model detects **hard hats only** — vests, goggles, and other
  PPE are not assessed.
- Trained on construction-site imagery; expect degraded accuracy in other
  domains (e.g. labs, warehouses) and on unusual viewpoints.
- Head-count is a proxy for person-count; occluded workers may be missed.
- Image-based assessments must always be supplemented with human review and
  site-specific policies.

## Responsible use

As with all vision-based safety tools:

- Treat outputs as **advisory** signals rather than ground truth.
- Validate performance on representative data before relying on it.
- Ensure privacy and compliance requirements for any captured imagery.
