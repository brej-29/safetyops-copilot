"""Ingestion endpoint protection: optional API key and per-client rate limit.

Both controls are opt-in via settings so local development stays frictionless:

- ``SAFETYOPS_API_KEY``: when set, write endpoints require a matching
  ``X-API-Key`` header.
- ``SAFETYOPS_RATE_LIMIT_PER_MINUTE``: when > 0, each client IP is limited to
  that many protected requests per rolling 60s window (in-memory; suitable for
  the single-process free-tier deployments this project targets).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request

from safetyops.core.settings import settings

_WINDOW_SECONDS = 60.0
_hits: Dict[str, Deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def reset_rate_limiter() -> None:
    """Clear rate-limit state (used by tests)."""
    with _lock:
        _hits.clear()


def enforce_write_policy(request: Request) -> None:
    """FastAPI dependency for endpoints that mutate state or cost resources."""
    if settings.api_key:
        provided = request.headers.get("X-API-Key")
        if provided != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return

    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        window = _hits[client]
        while window and now - window[0] > _WINDOW_SECONDS:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        window.append(now)
