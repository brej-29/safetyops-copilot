class SafetyOpsError(Exception):
    """Base exception for SafetyOps Copilot."""


class StreamingError(SafetyOpsError):
    """Raised when there is a streaming/event bus related failure."""


class InferenceError(SafetyOpsError):
    """Raised when an ML inference operation fails."""


class DatabaseError(SafetyOpsError):
    """Raised when a database interaction fails in a controlled way."""