from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TEXT = "text_event"
    VISION = "vision_event"


class TextEventPayload(BaseModel):
    text: str
    metadata: Dict[str, Any] | None = None


class VisionEventPayload(BaseModel):
    # Path to an image on disk (e.g. under data/sample or uploads).
    image_path: str | None = None
    metadata: Dict[str, Any] | None = None


class TextEventRequest(BaseModel):
    """API input model for text events."""

    text: str
    metadata: Dict[str, Any] | None = None


class VisionEventRequest(BaseModel):
    """API input model for vision events."""

    image_path: str | None = None
    metadata: Dict[str, Any] | None = None


class EventEnvelope(BaseModel):
    """Normalized event envelope stored in the stream and DB."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
    source: str | None = None
    payload: Union[TextEventPayload, VisionEventPayload]