from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from safetyops.domain.events import EventType


class HealthResponse(BaseModel):
    status: str
    version: str


class SystemStatusResponse(BaseModel):
    api_ok: bool
    database_ok: bool
    database_error: str | None = None
    redis_ok: bool
    redis_error: str | None = None
    worker_last_heartbeat: datetime | None = None
    worker_seconds_since_heartbeat: float | None = None


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


class CopilotTriageRequest(BaseModel):
    incident_id: Optional[str] = None
    text: Optional[str] = None
    image_path: Optional[str] = None


class CopilotTriageContextEvent(BaseModel):
    id: str
    created_at: datetime
    category: Optional[str]
    severity: Optional[str]
    risk_score: Optional[int]


class CopilotTriageResponse(BaseModel):
    incident_id: str
    category: Optional[str]
    severity: Optional[str]
    risk_score: Optional[int]
    context_events: List[CopilotTriageContextEvent]
    aggregates: Dict[str, Any]
    report_markdown: str