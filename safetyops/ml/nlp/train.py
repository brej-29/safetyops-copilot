from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import mlflow
import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from safetyops.core.logging import get_logger
from safetyops.core.settings import settings

logger = get_logger(__name__)


DATA_PATH_DEFAULT = Path("data/text/incidents_msha.csv")
MODEL_NAME = "distilbert-base-uncased"
LABELS = ["low", "medium", "high"]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for label, i in LABEL2ID.items()}


@dataclass
class IncidentRecord:
    text: str
    severity: str


BatchEncoding = Dict[str, torch.Tensor]


class IncidentDataset(Dataset[BatchEncoding]):
    def __init__(
        self,
        records: List[IncidentRecord],
        tokenizer: AutoTokenizer,
        max_length: int = 128,
    ) -> None:
        self.records = records
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        record = self.records[idx]
        encoding = self.tokenizer(
            record.text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
        )
        encoding["labels"] = torch.tensor(LABEL2ID[record.severity], dtype=torch.long)
        return {k: torch.tensor(v) for k, v in encoding.items()}


def load_dataset(path: Path) -> List[IncidentRecord]:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. "
            "Run `python scripts/download_msha_dataset.py` first."
        )

    records: List[IncidentRecord] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            severity = (row.get("severity") or "").strip().lower()
            if not text or severity not in LABEL2ID:
                continue
            records.append(IncidentRecord(text=text, severity=severity))
    if not records:
        raise ValueError(f"No valid records found in dataset at {path}")
    return records


def train_val_split(
    records: List[IncidentRecord], val_fraction: float = 0.2, seed: int = 42
) -> Tuple[List[IncidentRecord], List[IncidentRecord]]:
    rnd = random.Random(seed)
    shuffled = records[:]
    rnd.shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * val_fraction))
    val_records = shuffled[:n_val]
    train_records = shuffled[n_val:]
    return train_records, val_records


def compute_metrics(eval_pred: Tuple[np.ndarray, np.ndarray]) -> Dict[str, float]:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)

    acc = accuracy_score(labels, preds)
    precision_macro = precision_score(labels, preds, average="macro", zero_division=0)
    recall_macro = recall_score(labels, preds, average="macro", zero_division=0)
    f1_macro = f1_score(labels, preds, average="macro", zero_division=0)

    precision_weighted = precision_score(labels, preds, average="weighted", zero_division=0)
    recall_weighted = recall_score(labels, preds, average="weighted", zero_division=0)
    f1_weighted = f1_score(labels, preds, average="weighted", zero_division=0)

    return {
        "accuracy": float(acc),
        "precision_macro": float(precision_macro),
        "recall_macro": float(recall_macro),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(precision_weighted),
        "recall_weighted": float(recall_weighted),
        "f1_weighted": float(f1_weighted),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune DistilBERT on incident severity data (MSHA narratives by default).",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(DATA_PATH_DEFAULT),
        help="Path to CSV dataset with columns: text, category, severity.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=settings.nlp_model_dir,
        help="Directory to save the fine-tuned model artifacts.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Per-device batch size.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=5e-5,
        help="Learning rate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed.",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Load an existing model and run evaluation only (no training).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data_path = Path(args.data_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Loading dataset",
        extra={"data_path": str(data_path)},
    )
    records = load_dataset(data_path)
    train_records, val_records = train_val_split(records, val_fraction=0.2, seed=args.seed)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_dataset = IncidentDataset(train_records, tokenizer=tokenizer)
    val_dataset = IncidentDataset(val_records, tokenizer=tokenizer)

    num_labels = len(LABELS)

    # In eval-only mode, evaluate the previously fine-tuned model rather than
    # the base pretrained checkpoint.
    model_source = MODEL_NAME
    if args.eval_only and (output_dir / "config.json").exists():
        model_source = str(output_dir)

    logger.info(
        "Initializing model",
        extra={"model_name": model_source, "num_labels": num_labels},
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        model_source,
        num_labels=num_labels,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    training_kwargs = dict(
        output_dir=str(output_dir / "hf_runs"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        logging_dir=str(output_dir / "logs"),
        seed=args.seed,
    )
    # Keep compatibility across transformers versions: rename or drop kwargs
    # that the installed TrainingArguments does not accept.
    import inspect

    supported = set(inspect.signature(TrainingArguments.__init__).parameters)
    if "eval_strategy" not in supported and "evaluation_strategy" in supported:
        training_kwargs["evaluation_strategy"] = training_kwargs.pop("eval_strategy")
    training_kwargs = {k: v for k, v in training_kwargs.items() if k in supported}

    training_args = TrainingArguments(**training_kwargs)

    # MLflow >= 3.14 requires a database backend; sqlite keeps it local-first.
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri or "sqlite:///mlflow.db")
    mlflow.set_experiment("safetyops_nlp_severity")

    with mlflow.start_run():
        mlflow.log_params(
            {
                "model_name": MODEL_NAME,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "learning_rate": args.learning_rate,
                "seed": args.seed,
                "dataset_path": str(data_path),
            }
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
        )

        if not args.eval_only:
            logger.info("Starting training run")
            trainer.train()
        else:
            logger.info("Running eval-only; skipping training")

        logger.info("Evaluating model")
        eval_metrics = trainer.evaluate()
        logger.info("Evaluation metrics", extra={"metrics": eval_metrics})
        mlflow.log_metrics(eval_metrics)

        logger.info("Saving model and tokenizer", extra={"output_dir": str(output_dir)})
        trainer.save_model(str(output_dir))
        tokenizer.save_pretrained(str(output_dir))

        # Log artifacts to MLflow
        mlflow.log_artifacts(str(output_dir), artifact_path="nlp_model")

    logger.info("Training pipeline completed", extra={"output_dir": str(output_dir)})


if __name__ == "__main__":
    main()