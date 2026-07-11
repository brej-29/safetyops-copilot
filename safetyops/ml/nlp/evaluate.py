"""Evaluate incident-severity classifiers on the held-out MSHA test set.

Compares:
- the rule-based keyword baseline (safetyops.ml.nlp.classifier), and
- the fine-tuned DistilBERT model (if present in the model directory),

printing per-class classification reports and confusion matrices, and writing
a JSON summary next to the model.

Run:
    python -m safetyops.ml.nlp.evaluate
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List

from sklearn.metrics import classification_report, confusion_matrix, f1_score

from safetyops.core.logging import configure_logging, get_logger
from safetyops.core.settings import settings
from safetyops.ml.nlp.classifier import classify_incident

logger = get_logger(__name__)

LABELS = ["low", "medium", "high"]
TEST_PATH_DEFAULT = Path("data/text/incidents_msha_test.csv")


def load_test_set(path: Path) -> tuple[List[str], List[str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Test set not found at {path}. Run `python scripts/download_msha_dataset.py` first."
        )
    texts: List[str] = []
    labels: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = (row.get("text") or "").strip()
            severity = (row.get("severity") or "").strip().lower()
            if text and severity in LABELS:
                texts.append(text)
                labels.append(severity)
    return texts, labels


def predict_baseline(texts: List[str]) -> List[str]:
    return [classify_incident(t).severity for t in texts]


def predict_model(texts: List[str], model_dir: Path, batch_size: int = 32) -> List[str]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model.eval()

    id2label = {i: label for i, label in enumerate(LABELS)}
    if getattr(model.config, "id2label", None):
        id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}

    preds: List[str] = []
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded = tokenizer(
                batch,
                truncation=True,
                padding=True,
                max_length=128,
                return_tensors="pt",
            )
            logits = model(**encoded).logits
            for idx in logits.argmax(dim=-1).tolist():
                preds.append(id2label[idx])
    return preds


def summarize(name: str, y_true: List[str], y_pred: List[str]) -> dict:
    report = classification_report(
        y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS).tolist()
    macro_f1 = f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)

    print(f"\n=== {name} ===")
    print(classification_report(y_true, y_pred, labels=LABELS, zero_division=0))
    print(f"Confusion matrix (rows=true, cols=pred, order={LABELS}):")
    for label, row in zip(LABELS, matrix):
        print(f"  {label:>6}: {row}")

    return {
        "macro_f1": round(float(macro_f1), 4),
        "accuracy": round(float(report["accuracy"]), 4),
        "per_class": {
            label: {
                "precision": round(report[label]["precision"], 4),
                "recall": round(report[label]["recall"], 4),
                "f1": round(report[label]["f1-score"], 4),
            }
            for label in LABELS
        },
        "confusion_matrix": matrix,
        "labels": LABELS,
    }


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-path", type=str, default=str(TEST_PATH_DEFAULT))
    parser.add_argument("--model-dir", type=str, default=settings.nlp_model_dir)
    parser.add_argument(
        "--output-json",
        type=str,
        default=str(Path(settings.nlp_model_dir) / "eval_results.json"),
    )
    args = parser.parse_args()

    texts, labels = load_test_set(Path(args.test_path))
    logger.info("Loaded test set", extra={"rows": len(texts), "path": args.test_path})

    results: dict = {"test_path": args.test_path, "n_samples": len(texts)}
    results["rule_based_baseline"] = summarize(
        "Rule-based baseline", labels, predict_baseline(texts)
    )

    model_dir = Path(args.model_dir)
    if (model_dir / "config.json").exists():
        results["distilbert"] = summarize(
            f"DistilBERT ({model_dir})", labels, predict_model(texts, model_dir)
        )
    else:
        print(f"\nNo fine-tuned model found at {model_dir}; skipping model evaluation.")

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote evaluation summary to {output_path}")


if __name__ == "__main__":
    main()
