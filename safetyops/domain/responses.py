from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel

from safetyops.domain.events import EventType


class HealthResponse(BaseModel):
    status: str
    version: str


class EnrichedEventResponse(BaseModel):
    id: str
    event_type: EventType
    created_at: datetime
    correlation_id: str | None = None
    category: str | None = None
    severity: str | None = None
    enrichment: Dict[str, Any]


class AggregateSummaryItem(BaseModel):
    event_type: EventType
    severity: str | None
    count: int


class AggregateSummaryResponse(BaseModel):
    items: List[AggregateSummaryItem]