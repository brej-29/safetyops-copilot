from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from safetyops.db.base import Base


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    enriched_event: Mapped["EnrichedEvent"] = relationship(
        "EnrichedEvent",
        back_populates="raw_event",
        uselist=False,
    )


class EnrichedEvent(Base):
    __tablename__ = "enriched_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    raw_event_id: Mapped[str] = mapped_column(String, ForeignKey("raw_events.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    enrichment: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    severity: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    raw_event: Mapped[RawEvent] = relationship("RawEvent", back_populates="enriched_event")


class DailyAggregate(Base):
    __tablename__ = "daily_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)