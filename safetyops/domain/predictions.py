from typing import Literal

from pydantic import BaseModel


class TextClassificationPrediction(BaseModel):
    """Prediction for an incident text event."""

    category: str
    severity: Literal["low", "medium", "high"]
    confidence: float


class VisionPPEDetection(BaseModel):
    """PPE compliance prediction for a vision event."""

    compliance_score: float
    num_persons: int
    num_persons_with_ppe: int