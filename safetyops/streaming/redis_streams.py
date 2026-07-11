from __future__ import annotations

from typing import List, Optional

import redis
from redis.exceptions import ResponseError

from safetyops.core.exceptions import StreamingError
from safetyops.core.logging import get_logger
from safetyops.core.settings import settings
from safetyops.domain.events import EventEnvelope
from safetyops.streaming.base import BaseEventBus, StreamEvent

logger = get_logger(__name__)


class RedisStreamsEventBus(BaseEventBus):
    """Redis Streams-based implementation of the event bus."""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        stream_key: Optional[str] = None,
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
    ) -> None:
        self.stream_key = stream_key or settings.stream_key
        self.consumer_group = consumer_group or settings.consumer_group
        self.consumer_name = consumer_name or settings.consumer_name
        self._client = redis_client or redis.Redis.from_url(
            settings.redis_url,
            decode_responses=False,
            # redis-py >= 8 defaults socket_timeout to 5s, which races the
            # blocking XREADGROUP reads in consume(). Keep the socket timeout
            # comfortably above any block_ms used by the worker.
            socket_timeout=30,
            socket_connect_timeout=5,
        )

    def publish(self, event: EventEnvelope) -> str:
        payload = event.model_dump_json()
        try:
            message_id = self._client.xadd(self.stream_key, {"data": payload})
            if isinstance(message_id, bytes):
                message_id = message_id.decode()
            logger.info(
                "Published event to stream",
                extra={
                    "stream_key": self.stream_key,
                    "event_type": event.event_type.value,
                    "event_id": event.id,
                },
            )
            return message_id
        except Exception as exc:
            logger.exception(
                "Failed to publish event to Redis stream",
                extra={
                    "stream_key": self.stream_key,
                    "event_type": event.event_type.value,
                    "event_id": event.id,
                },
            )
            raise StreamingError("Failed to publish event") from exc

    def ensure_consumer_group(self) -> None:
        try:
            self._client.xgroup_create(
                name=self.stream_key,
                groupname=self.consumer_group,
                id="0-0",
                mkstream=True,
            )
            logger.info(
                "Created Redis consumer group",
                extra={"stream_key": self.stream_key, "consumer_group": self.consumer_group},
            )
        except ResponseError as exc:
            # Group already exists
            if "BUSYGROUP" in str(exc):
                logger.info(
                    "Redis consumer group already exists",
                    extra={"stream_key": self.stream_key, "consumer_group": self.consumer_group},
                )
                return
            logger.exception(
                "Error ensuring consumer group",
                extra={"stream_key": self.stream_key, "consumer_group": self.consumer_group},
            )
            raise StreamingError("Failed to ensure consumer group") from exc
        except Exception as exc:
            logger.exception(
                "Error ensuring consumer group",
                extra={"stream_key": self.stream_key, "consumer_group": self.consumer_group},
            )
            raise StreamingError("Failed to ensure consumer group") from exc

    def consume(self, count: int = 10, block_ms: int = 5000) -> List[StreamEvent]:
        try:
            response = self._client.xreadgroup(
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                streams={self.stream_key: ">"},
                count=count,
                block=block_ms,
            )
        except redis.exceptions.TimeoutError:
            # A blocking read that times out without messages is normal idle
            # behavior, not an error.
            return []
        except Exception as exc:
            logger.exception(
                "Failed to read from Redis stream",
                extra={"stream_key": self.stream_key, "consumer_group": self.consumer_group},
            )
            raise StreamingError("Failed to consume events") from exc

        if not response:
            return []

        events: List[StreamEvent] = []
        for _stream, messages in response:
            for message_id, fields in messages:
                raw_data = fields.get(b"data") or fields.get("data")
                if raw_data is None:
                    logger.warning(
                        "Received Redis message without 'data' field",
                        extra={"message_id": message_id},
                    )
                    continue

                if isinstance(message_id, bytes):
                    message_id_str = message_id.decode()
                else:
                    message_id_str = str(message_id)

                if isinstance(raw_data, (bytes, bytearray)):
                    payload_str = raw_data.decode()
                else:
                    payload_str = str(raw_data)

                try:
                    envelope = EventEnvelope.model_validate_json(payload_str)
                except Exception:
                    logger.exception(
                        "Failed to parse event envelope from Redis message",
                        extra={"message_id": message_id_str},
                    )
                    continue

                events.append(StreamEvent(message_id=message_id_str, envelope=envelope))

        return events

    def ack(self, message_id: str) -> None:
        try:
            self._client.xack(self.stream_key, self.consumer_group, message_id)
            logger.info(
                "Acknowledged Redis stream message",
                extra={
                    "stream_key": self.stream_key,
                    "consumer_group": self.consumer_group,
                    "message_id": message_id,
                },
            )
        except Exception as exc:
            logger.exception(
                "Failed to ack Redis stream message",
                extra={
                    "stream_key": self.stream_key,
                    "consumer_group": self.consumer_group,
                    "message_id": message_id,
                },
            )
            raise StreamingError("Failed to ack message") from exc