# YOLOv8 PPE Training in Google Colab

This guide describes how to fine-tune a YOLOv8 model for PPE detection using a
free GPU environment such as **Google Colab**. The goal is to keep the main
SafetyOps Copilot repository lightweight while still enabling realistic vision
experiments.

## 1. Start a Colab notebook

1. Go to https://colab.research.google.com/
2. Create a new notebook.
3. In the menu, choose: `Runtime` → `Change runtime type` → `T4 GPU` (or any
   available GPU).

## 2. Clone your SafetyOps Copilot repo

```python
!git clone &quot;https://github.com/&lt;your-org&gt;/safetyops-copilot.git&quot;
%cd safetyops-copilot
```

If you are working from a fork or private repo, adjust the URL accordingly.

## 3. Install dependencies

```python
!pip install -r requirements.txt
```

Ultralytics and Torch will be installed as part of the base requirements.

## 4. Prepare a PPE dataset

Follow `scripts/download_vision_dataset.py` and `data/vision/README.md` in the
repository for guidance. In summary:

1. Obtain a YOLO-format PPE dataset (e.g. from Kaggle).
2. Upload it to the Colab session or mount Google Drive.
3. Arrange the files into:

   ```text
   data/vision/ppe/images/
   data/vision/ppe/labels/
   ```

Each image in `images/` should have a corresponding label file in `labels/`
with YOLO bounding box definitions.

## 5. Run the training script

From a Colab cell:

```python
!python -m safetyops.ml.vision.train \
    --data-root data/vision/ppe \
    --epochs 10 \
    --img-size 640 \
    --batch-size 16
```

Parameters you can adjust:

- `--data-root`: path to your YOLO dataset root.
- `--epochs`: number of training epochs (start small, e.g. 5–10).
- `--img-size`: input image size (640 is YOLOv8 default).
- `--batch-size`: depends on GPU memory (try 8 or 16).

The script will:

- Use Ultralytics YOLOv8 to launch training.
- Save YOLO checkpoints under `artifacts/vision/` by default.

## 6. Download the trained weights

Once training completes, download the best checkpoint (e.g. `best.pt`) from
the Colab file browser. Place it in your local environment, for example:

```text
models/vision/yolov8n_ppe.pt
```

Then set the corresponding environment variable:

```bash
export SAFETYOPS_VISION_MODEL_PATH=models/vision/yolov8n_ppe.pt
```

(or add it to your `.env` file).

## 7. Use the custom weights locally

With `SAFETYOPS_VISION_MODEL_PATH` pointing to your fine-tuned weights,
the `safetyops.ml.vision.infer.run_ppe_inference` function and the worker
service will automatically use your custom PPE model:

- No code changes needed.
- If the file is missing, the system falls back to the default `yolov8n.pt`
  or a stub, so development and CI remain robust.

## 8. Notes and best practices

- Start with a small number of epochs and inspect results before training
  longer.
- Monitor overfitting by watching validation metrics and example predictions.
- Ensure your dataset reflects the PPE and environments you care about.
- Consider versioning your weights using DVC or another artifact management
  tool if you iterate frequently.