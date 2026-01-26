from prometheus_client import Counter, Histogram

from safetyops.core.settings import settings

NAMESPACE = settings.metrics_namespace

EVENTS_PUBLISHED = Counter(
    f"{NAMESPACE}_events_published_total",
    "Number of events published to the event stream",
    ["event_type"],
)

WORKER_PROCESSED = Counter(
    f"{NAMESPACE}_worker_processed_total",
    "Number of events processed by the worker",
    ["event_type", "result"],
)

WORKER_PROCESSING_TIME = Histogram(
    f"{NAMESPACE}_worker_processing_seconds",
    "Time spent processing events in the worker",
    ["event_type"],
)