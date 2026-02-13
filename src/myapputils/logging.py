# myapputils/logging.py
"""
Production-ready structured logging configuration using structlog.

This module provides:
- Structured JSON logging for production
- Colored console logging for development
- Context-aware logging with request/user tracking
- Celery task logging support
- Django middleware for request context

Usage:
    from myapputils.logging import get_logger

    logger = get_logger(__name__)
    logger.info("User logged in", user_id=123, email="user@example.com")
"""

import logging
import logging.config
import sys
import traceback
from datetime import datetime
from pathlib import Path

import structlog
from django.conf import settings
from structlog.types import Processor

# =============================================================================
# CONFIGURATION
# =============================================================================

# Log levels mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def is_development() -> bool:
    """Check if running in development mode."""
    return getattr(settings, "DEBUG", False)


def get_log_level() -> int:
    """Get the configured log level."""
    level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    return LOG_LEVELS.get(level_name, logging.INFO)


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    base_dir = Path(settings.BASE_DIR)
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


# =============================================================================
# PROCESSORS
# =============================================================================


def add_logger_name(logger: structlog.PrintLogger, name: str, event_dict: dict) -> dict:
    """Add the logger name to the event dict."""
    event_dict["logger"] = name
    return event_dict


def add_environment(logger: structlog.PrintLogger, name: str, event_dict: dict) -> dict:
    """Add environment information to the event dict."""
    event_dict["environment"] = getattr(settings, "ENVIRONMENT", "unknown")
    return event_dict


def add_app_name(logger: structlog.PrintLogger, name: str, event_dict: dict) -> dict:
    """Add application name to the event dict."""
    event_dict["app"] = "template"
    return event_dict


def rename_message_field(
    logger: structlog.PrintLogger, name: str, event_dict: dict
) -> dict:
    """Rename 'event' field to 'message' for compatibility."""
    event_dict["message"] = event_dict.pop("event")
    return event_dict


class UTCFormatter:
    """Format timestamps in UTC."""

    def __call__(
        self, logger: structlog.PrintLogger, name: str, event_dict: dict
    ) -> dict:
        """Add UTC timestamp to event dict."""
        event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return event_dict


def filter_exc_info(logger: structlog.PrintLogger, name: str, event_dict: dict) -> dict:
    """Filter exception info from regular logs (only show in error logs)."""
    if event_dict.get("level") not in ("error", "critical"):
        event_dict.pop("exc_info", None)
        event_dict.pop("exception", None)
    return event_dict


def order_keys(logger: structlog.PrintLogger, name: str, event_dict: dict) -> dict:
    """Order keys for better readability."""
    key_order = ["timestamp", "level", "logger", "message", "environment"]
    ordered = {k: event_dict.pop(k) for k in key_order if k in event_dict}
    ordered.update(event_dict)
    return ordered


# =============================================================================
# SHARED PROCESSORS
# =============================================================================

SHARED_PROCESSORS: list[Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    add_app_name,
    add_environment,
    UTCFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
]


# =============================================================================
# DEVELOPMENT PROCESSORS (Console with colors)
# =============================================================================

DEV_PROCESSORS: list[Processor] = [
    *SHARED_PROCESSORS,
    rename_message_field,
    structlog.dev.ConsoleRenderer(
        colors=True, exception_formatter=structlog.dev.plain_traceback
    ),
]


# =============================================================================
# PRODUCTION PROCESSORS (JSON output)
# =============================================================================

PROD_PROCESSORS: list[Processor] = [
    *SHARED_PROCESSORS,
    rename_message_field,
    filter_exc_info,
    order_keys,
    structlog.processors.JSONRenderer(),
]


# =============================================================================
# DJANGO STANDARD LIBRARY LOGGING CONFIGURATION
# =============================================================================


def get_standard_logging_config() -> dict:
    """
    Get Django's standard logging configuration for structlog integration.

    This configures Django's built-in logging to use structlog's
    StdlibProcessor for consistent structured output.
    """
    logs_dir = get_logs_dir()
    log_level = get_log_level()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {asctime} {module} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
            },
            "console_json": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
            },
            "file": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": logs_dir / "django.log",
                "maxBytes": 1024 * 1024 * 10,  # 10 MB
                "backupCount": 5,
                "formatter": "json" if not is_development() else "verbose",
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": logs_dir / "django_error.log",
                "maxBytes": 1024 * 1024 * 10,  # 10 MB
                "backupCount": 10,
                "formatter": "json",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "django.request": {
                "handlers": ["error_file"],
                "level": "ERROR",
                "propagate": False,
            },
            "django.server": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "celery": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "myapp": {
                "handlers": ["console", "file"],
                "level": "DEBUG" if is_development() else "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": log_level,
        },
    }


# =============================================================================
# STRUCTLOG CONFIGURATION
# =============================================================================


def configure_structlog() -> None:
    """
    Configure structlog for the application.

    This should be called during Django startup.
    """
    processors = DEV_PROCESSORS if is_development() else PROD_PROCESSORS

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging() -> None:
    """
    Configure both standard Django logging and structlog.

    This is the main entry point for logging configuration.
    Call this once during application startup.
    """
    # Configure standard Django logging
    logging.config.dictConfig(get_standard_logging_config())

    # Configure structlog
    configure_structlog()


# =============================================================================
# LOGGER FACTORY
# =============================================================================


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__ of the calling module)

    Returns:
        A configured structlog BoundLogger instance

    Example:
        from myapputils.logging import get_logger

        logger = get_logger(__name__)
        logger.info("User action", user_id=123, action="login")
    """
    return structlog.get_logger(name)


# =============================================================================
# DJANGO MIDDLEWARE FOR REQUEST CONTEXT
# =============================================================================


class StructlogMiddleware:
    """
    Django middleware that adds request context to structured logs.

    This middleware automatically enriches all log entries within a request
    with request_id, user_id, and other contextual information.

    Add to Django's MIDDLEWARE setting:
        MIDDLEWARE = [
            ...
            'myapputils.logging.StructlogMiddleware',
            ...
        ]
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Process request with structured logging context."""
        # Import here to avoid circular imports
        from structlog.contextvars import bind_contextvars, clear_contextvars

        # Clear any previous context
        clear_contextvars()

        # Generate or get request ID
        request_id = self._get_request_id(request)

        # Bind context variables for this request
        bind_contextvars(
            request_id=request_id,
            request_method=request.method,
            request_path=request.path,
        )

        # Add user info if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            bind_contextvars(
                user_id=getattr(request.user, "user_id", None),
                user_email=getattr(request.user, "email", None),
                user_role=getattr(request.user, "role", None),
            )

        # Add request ID to the request object for use in views
        request.request_id = request_id

        # Process the request
        response = self.get_response(request)

        # Log request completion
        logger = get_logger("django.request")
        logger.info(
            "request_completed",
            status_code=response.status_code,
            method=request.method,
            path=request.path,
        )

        return response

    def _get_request_id(self, request) -> str:
        """Get or generate a request ID."""
        # Check for existing request ID from header
        request_id = request.headers.get("X-Request-ID")

        if request_id:
            return request_id

        # Generate UUID for request
        import uuid

        return str(uuid.uuid4())


def process_exception(
    logger: structlog.stdlib.BoundLogger,
    exc_type: type[BaseException],
    exc_value: BaseException,
    traceback_obj,
) -> dict:
    """
    Processor for formatting exceptions in structured logs.

    Args:
        logger: The logger instance
        exc_type: Exception type
        exc_value: Exception instance
        traceback_obj: Traceback object

    Returns:
        Event dict with formatted exception info
    """
    logger.error(
        "exception_occurred",
        exception_type=exc_type.__name__,
        exception_message=str(exc_value),
        exception_traceback="".join(
            traceback.format_exception(exc_type, exc_value, traceback_obj)
        ),
    )
    return {}


# =============================================================================
# CELERY INTEGRATION
# =============================================================================


class CeleryLogger:
    """
    Helper class for logging in Celery tasks with task context.

    Usage:
        from myapputils.logging import CeleryLogger

        @celery_app.task
        def my_task(arg1):
            logger = CeleryLogger.get_logger(__name__)
            logger.info("Task started", arg1=arg1)
    """

    @staticmethod
    def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
        """Get a logger with Celery task context."""
        from celery import current_task
        from structlog.contextvars import bind_contextvars

        logger = get_logger(name)

        # Bind task context if available
        if current_task:
            bind_contextvars(
                task_name=current_task.name,
                task_id=current_task.request.id,
                task_retries=current_task.request.retries,
            )

        return logger


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Celery
    "CeleryLogger",
    # Middleware
    "StructlogMiddleware",
    # Configuration
    "configure_logging",
    "configure_structlog",
    "get_log_level",
    # Loggers
    "get_logger",
    "get_logs_dir",
    "get_standard_logging_config",
    # Utilities
    "is_development",
]
