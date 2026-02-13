# myapputils/log_helpers.py
"""
Helper functions for common logging scenarios.

This module provides utility functions for logging common events
such as API requests, database operations, authentication events, etc.

Usage:
    from myapputils.log_helpers import log_api_request, log_db_query

    log_api_request(request, response, duration=0.123)
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse

from .logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# API REQUEST LOGGING
# =============================================================================


def log_api_request(
    request: HttpRequest,
    response: HttpResponse | None = None,
    duration: float | None = None,
    error: Exception | None = None,
    **extra_context: Any,
) -> None:
    """
    Log an API request with context.

    Args:
        request: The Django HTTP request
        response: Optional HTTP response
        duration: Request duration in seconds
        error: Optional exception if request failed
        **extra_context: Additional context to log

    Example:
        log_api_request(
            request,
            response,
            duration=0.123,
            query_count=5,
            cache_hits=3
        )
    """
    context = {
        "request_method": request.method,
        "request_path": request.path,
        "request_user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "request_ip": get_client_ip(request),
    }

    if response:
        context.update(
            {
                "response_status": response.status_code,
                "response_size": len(response.content)
                if hasattr(response, "content")
                else 0,
            }
        )

    if duration is not None:
        context["duration_seconds"] = round(duration, 4)

    if error:
        context["error_type"] = type(error).__name__
        context["error_message"] = str(error)

    context.update(extra_context)

    log_level = "error" if error else "info"
    getattr(logger, log_level)(
        "api_request",
        **context,
    )


def get_client_ip(request: HttpRequest) -> str:
    """Get the client IP address from request headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


# =============================================================================
# DATABASE LOGGING
# =============================================================================


def log_db_query(
    model: str,
    action: str,
    query_type: str = "select",
    row_count: int | None = None,
    duration: float | None = None,
    **extra_context: Any,
) -> None:
    """
    Log a database operation.

    Args:
        model: The model name (e.g., 'User', 'Subscription')
        action: The action performed (e.g., 'create', 'update', 'delete', 'list')
        query_type: Type of query (select, insert, update, delete)
        row_count: Number of rows affected
        duration: Query duration in seconds
        **extra_context: Additional context

    Example:
        log_db_query('User', 'create', query_type='insert', row_count=1, duration=0.045)
    """
    context = {
        "db_model": model,
        "db_action": action,
        "db_query_type": query_type,
    }

    if row_count is not None:
        context["db_row_count"] = row_count

    if duration is not None:
        context["duration_seconds"] = round(duration, 4)

    context.update(extra_context)

    logger.debug("db_query", **context)


# =============================================================================
# AUTHENTICATION LOGGING
# =============================================================================


def log_auth_event(
    event_type: str,
    user_id: int | None = None,
    email: str | None = None,
    success: bool = True,
    failure_reason: str | None = None,
    **extra_context: Any,
) -> None:
    """
    Log an authentication event.

    Args:
        event_type: Type of auth event (login, logout, register, password_reset, etc.)
        user_id: User ID if applicable
        email: User email if applicable
        success: Whether the operation succeeded
        failure_reason: Reason for failure if not successful
        **extra_context: Additional context

    Example:
        log_auth_event('login', user_id=123, email='user@example.com', success=True)
        log_auth_event('login', email='hacker@evil.com', success=False,
                      failure_reason='invalid_credentials')
    """
    context = {
        "auth_event": event_type,
        "auth_success": success,
    }

    if user_id:
        context["user_id"] = user_id

    if email:
        context["user_email"] = email

    if failure_reason:
        context["failure_reason"] = failure_reason

    context.update(extra_context)

    log_level = "warning" if not success else "info"
    getattr(logger, log_level)(
        "auth_event",
        **context,
    )


# =============================================================================
# BUSINESS EVENT LOGGING
# =============================================================================


def log_business_event(
    event_type: str,
    user_id: int | None = None,
    subscription_id: int | None = None,
    amount: float | None = None,
    currency: str | None = None,
    status: str | None = None,
    **extra_context: Any,
) -> None:
    """
    Log a business event (subscription, payment, etc.).

    Args:
        event_type: Type of business event (subscription_created, payment_processed, etc.)
        user_id: User ID
        subscription_id: Subscription ID if applicable
        amount: Monetary amount if applicable
        currency: Currency code
        status: Event status
        **extra_context: Additional context

    Example:
        log_business_event(
            'subscription_created',
            user_id=123,
            subscription_id=456,
            amount=29.99,
            currency='USD',
            status='active'
        )
    """
    context = {"business_event": event_type}

    if user_id:
        context["user_id"] = user_id

    if subscription_id:
        context["subscription_id"] = subscription_id

    if amount is not None:
        context["amount"] = amount

    if currency:
        context["currency"] = currency

    if status:
        context["status"] = status

    context.update(extra_context)

    logger.info("business_event", **context)


# =============================================================================
# DECORATORS
# =============================================================================


def log_execution(
    log_args: bool = False,
    log_result: bool = False,
    log_exceptions: bool = True,
    logger_name: str | None = None,
) -> Callable:
    """
    Decorator to log function execution.

    Args:
        log_args: Whether to log function arguments
        log_result: Whether to log function return value
        log_exceptions: Whether to log exceptions
        logger_name: Custom logger name (defaults to module name)

    Example:
        @log_execution(log_args=True, log_result=True)
        def my_function(x, y):
            return x + y
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            fn_logger = get_logger(logger_name or func.__module__)
            func_name = f"{func.__module__}.{func.__name__}"

            start_time = time.time()

            context = {"function": func_name}

            if log_args:
                context["args"] = str(args)[:200]  # Limit length
                context["kwargs"] = str(kwargs)[:200]

            fn_logger.debug("function_started", **context)

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                context["duration_seconds"] = round(duration, 4)
                if log_result:
                    context["result"] = str(result)[:200]

                fn_logger.debug("function_completed", **context)
                return result

            except Exception as e:
                duration = time.time() - start_time
                context["duration_seconds"] = round(duration, 4)
                context["exception_type"] = type(e).__name__
                context["exception_message"] = str(e)

                if log_exceptions:
                    fn_logger.error("function_failed", **context, exc_info=True)
                else:
                    fn_logger.debug("function_failed", **context)

                raise

        return wrapper

    return decorator


def log_api_view(func: Callable) -> Callable:
    """
    Decorator for API view functions to log requests automatically.

    This decorator should be applied to Django REST Framework view methods
    to automatically log all requests with timing and context.

    Example:
        class MyAPIView(APIView):
            @log_api_view
            def get(self, request):
                # ... view logic
                pass
    """

    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        view_logger = get_logger(f"{func.__module__}.{self.__class__.__name__}")
        start_time = time.time()

        view_logger.info(
            "api_view_started",
            view_method=func.__name__.upper(),
            request_method=request.method,
            request_path=request.path,
            user_id=getattr(request, "user_id", None),
        )

        try:
            response = func(self, request, *args, **kwargs)
            duration = time.time() - start_time

            view_logger.info(
                "api_view_completed",
                view_method=func.__name__.upper(),
                status_code=response.status_code,
                duration_seconds=round(duration, 4),
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            view_logger.error(
                "api_view_failed",
                view_method=func.__name__.upper(),
                exception_type=type(e).__name__,
                exception_message=str(e),
                duration_seconds=round(duration, 4),
                exc_info=True,
            )
            raise

    return wrapper


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================


class LogContext:
    """Context manager for adding temporary logging context."""

    def __init__(self, **context: Any):
        """
        Initialize the log context.

        Args:
            **context: Key-value pairs to add to logging context
        """
        self.context = context
        self.token = None

    def __enter__(self):
        """Add context to structlog contextvars."""
        try:
            from structlog.contextvars import bind_contextvars

            self.token = bind_contextvars(**self.context)
        except ImportError:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove context from structlog contextvars."""
        try:
            from structlog.contextvars import unbind_contextvars

            unbind_contextvars(*self.context.keys())
        except ImportError:
            pass


# =============================================================================
# ERROR TRACKING
# =============================================================================


def log_exception(
    exception: Exception,
    context: dict[str, Any] | None = None,
    level: str = "error",
    logger_name: str | None = None,
) -> None:
    """
    Log an exception with full context.

    Args:
        exception: The exception to log
        context: Additional context information
        level: Log level (error or critical)
        logger_name: Custom logger name

    Example:
        try:
            risky_operation()
        except Exception as e:
            log_exception(e, context={'user_id': 123, 'operation': 'risky'})
    """
    exc_logger = get_logger(logger_name or __name__)

    log_context = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
    }

    if context:
        log_context.update(context)

    getattr(exc_logger, level)(
        "exception",
        **log_context,
        exc_info=True,
    )


def log_task(
    task_name: str,
    status: str,
    result: Any = None,
    error: Exception | None = None,
    duration: float | None = None,
    **extra_context: Any,
) -> None:
    """
    Log a Celery task execution.

    Args:
        task_name: Name of the task
        status: Task status (started, success, failure, retry)
        result: Task result if successful
        error: Exception if failed
        duration: Task duration in seconds
        **extra_context: Additional context

    Example:
        log_task('send_email', status='success', result='sent', duration=1.23,
                 recipient='user@example.com')
    """
    context = {
        "task_name": task_name,
        "task_status": status,
    }

    if result is not None:
        context["task_result"] = str(result)[:500]

    if error:
        context["exception_type"] = type(error).__name__
        context["exception_message"] = str(error)

    if duration is not None:
        context["duration_seconds"] = round(duration, 2)

    context.update(extra_context)

    log_level = "error" if status == "failure" else "info"
    getattr(logger, log_level)("celery_task", **context)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Context manager
    "LogContext",
    "get_client_ip",
    # API logging
    "log_api_request",
    "log_api_view",
    # Auth logging
    "log_auth_event",
    # Business logging
    "log_business_event",
    # Database logging
    "log_db_query",
    # Error tracking
    "log_exception",
    # Decorators
    "log_execution",
    # Task logging
    "log_task",
]
