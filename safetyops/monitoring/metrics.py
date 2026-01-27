from prometheus_client import Counter, Histogram

from safetyops.core.settings import settings

NAMESPACE = settings.metrics_namespace

# Ingestion metrics (API)
EVENTS_INGESTED = Counter(
    f"{NAMESPACE}_events_ingested_total",
    "Number of events ingested by the API",
    ["event_type"],
)

# Worker processing metrics
EVENTS_PROCESSED = Counter(
    f"{NAMESPACE}_events_processed_total",
    "Number of events processed by the worker",
    ["event_type", "status"],
)

WORKER_PROCESSING_TIME = Histogram(
    f"{NAMESPACE}_worker_processing_seconds",
    "Time spent processing events in the worker",
    ["event_type"],
)

# Model inference metrics
model_inference_seconds = Histogram(
    f"{NAMESPACE}_model_inference_seconds",
    "Time spent in model inference calls",
    ["model"],
)

# DLQ metrics
DLQ_MESSAGES = Counter(
    f"{NAMESPACE}_dlq_messages_total",
    "Number of messages sent to the DLQ stream",
)