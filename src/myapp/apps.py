# myapp/apps.py
"""
Django app configuration for the main myapp application.

This module initializes the application and configures structured logging.
"""

import contextlib

from django.apps import AppConfig


class MyappConfig(AppConfig):
    """Configuration for the myapp Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "myapp"
    verbose_name = "Template Application"

    def ready(self) -> None:
        """
        Initialize application when Django starts.

        This method is called when Django starts and is the appropriate place
        to initialize services like structured logging.
        """
        self._configure_structured_logging()
        self._initialize_signals()

    def _configure_structured_logging(self) -> None:
        """Configure structured logging if enabled."""
        from django.conf import settings

        if getattr(settings, "USE_STRUCTURED_LOGGING", True):
            try:
                from myapputils.logging import configure_logging

                configure_logging()
            except ImportError:
                # Fall back to standard logging if structlog is not available
                import logging

                logging.basicConfig(
                    level=getattr(settings, "LOG_LEVEL", "INFO"),
                    format="%(levelname)s %(asctime)s %(name)s %(message)s",
                )

    def _initialize_signals(self) -> None:
        """Initialize Django signal handlers."""
        # Import signals module to register signal handlers
        with contextlib.suppress(ImportError):
            import myapp.signals  # noqa: F401
