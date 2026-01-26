from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from safetyops.core.logging import get_logger
from safetyops.core.settings import settings
from safetyops.domain.predictions import TextClassificationPrediction
from safetyops.ml.nlp.classifier import classify_incident as rule_based_classify

logger = get_logger(__name__)


_MODEL = None
_TOKENIZER = None
_LABELS = ["low", "medium", "high"]


def _get_model_dir() -> Path:
    return Path(settings.nlp_model_dir)


def _load_model() -> tuple[Optional[AutoModelForSequenceClassification], Optional[AutoTokenizer]]:
    """Lazily load the fine-tuned DistilBERT model, if available.

    If the model directory is missing or loading fails, returns (None, None)
    and the caller should fall back to the rule-based classifier.
    """
    global _MODEL, _TOKENIZER

    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER

    model_dir = _get_model_dir()
    if not model_dir.exists():
        logger.info(
            "NLP model directory not found; using rule-based classifier",
            extra={"model_dir": str(model_dir)},
        )
        return None, None

    try:
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    except Exception:
        logger.exception(
            "Failed to load NLP model; falling back to rule-based classifier",
            extra={"model_dir": str(model_dir)},
        )
        return None, None

    _MODEL = model
    _TOKENIZER = tokenizer
    logger.info("Loaded fine-tuned NLP model", extra={"model_dir": str(model_dir)})
    return _MODEL, _TOKENIZER


def predict_severity(text: str) -> TextClassificationPrediction:
    """Predict incident category and severity for the given text.

    - If a fine-tuned DistilBERT model is available, use it for severity.
    - Always derive the category from the existing rule-based classifier.
    - If the model is unavailable, fall back entirely to the rule-based
      implementation.
    """
    model, tokenizer = _load_model()
    if model is None or tokenizer is None:
        return rule_based_classify(text)

    try:
        encoded = tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=128,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = model(**encoded)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)[0]
            pred_idx = int(torch.argmax(probs).item())
            severity = _LABELS[pred_idx]
            confidence = float(probs[pred_idx].item())
    except Exception:
        logger.exception(
            "Error during NLP model inference; falling back to rule-based classifier",
        )
        return rule_based_classify(text)

    # Category still comes from the rule-based classifier for v1
    baseline = rule_based_classify(text)

    return TextClassificationPrediction(
        category=baseline.category,
        severity=severity,
        confidence=confidence,
    )