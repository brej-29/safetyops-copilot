import logging
import logging.config
from contextvars import ContextVar

from safetyops.core.settings import settings

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id and app_name into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        record.app_name = settings.app_name
        return True


def configure_logging() -> None:
    """Configure application-wide structured logging."""
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s [%(app_name)s] "
                "[%(name)s] [corr=%(correlation_id)s] %(message)s",
            },
        },
        "filters": {
            "correlation": {
                "()": CorrelationIdFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["correlation"],
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
    }
    logging.config.dictConfig(logging_config)


def set_correlation_id(value: str | None) -> None:
    """Set the current correlation_id for log context."""
    _correlation_id.set(value)


def get_correlation_id() -> str | None:
    """Get the current correlation_id, if any."""
    return _correlation_id.get()


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger instance with standard configuration."""
    return logging.getLogger(name or settings.app_name)