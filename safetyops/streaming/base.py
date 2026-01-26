from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from safetyops.domain.events import EventEnvelope


@dataclass
class StreamEvent:
    """Event as read from the stream, with its message id."""

    message_id: str
    envelope: EventEnvelope


class BaseEventBus(ABC):
    """Abstract event bus interface."""

    @abstractmethod
    def publish(self, event: EventEnvelope) -> str:
        """Publish an event to the stream and return the message id."""

    @abstractmethod
    def ensure_consumer_group(self) -> None:
        """Ensure that the consumer group exists (idempotent)."""

    @abstractmethod
    def consume(self, count: int = 10, block_ms: int = 5000) -> List[StreamEvent]:
        """Consume a batch of events from the stream."""

    @abstractmethod
    def ack(self, message_id: str) -> None:
        """Acknowledge successful processing of a message."""