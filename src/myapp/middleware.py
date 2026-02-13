# middleware.py
"""
Custom middleware for Django REST Framework authentication and rate limiting.

This module provides:
- JWT-based authentication middleware
- User ID and role attachment to requests
- API rate limiting based on subscription
- Structured logging integration
"""

import logging
import time
from typing import Any

from django.http import HttpRequest, JsonResponse
from rest_framework.exceptions import AuthenticationFailed

from myapp.authentication import CustomJWTAuthentication
from myapp.services.subscription_service import SubscriptionService

# Try to use structured logging, fall back to standard logging
try:
    from myapputils.logging import get_logger

    logger = get_logger(__name__)
    USE_STRUCTURED_LOGGING = True
except ImportError:
    logger = logging.getLogger(__name__)
    USE_STRUCTURED_LOGGING = False


class JWTAuthenticationMiddleware:
    """
    Authenticates users via JWT and attaches user_id, user, and role to request.

    This is a single, consistent authentication middleware that replaces
    the three previously redundant middleware classes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        if "Authorization" in request.headers:
            auth = CustomJWTAuthentication()
            try:
                user, token = auth.authenticate(request)
                if user and token:
                    # Attach user object and claims to request
                    request.user = user
                    request.user_id = token.get("user_id")
                    request.role = token.get("role")
            except AuthenticationFailed as e:
                if USE_STRUCTURED_LOGGING:
                    logger.debug("authentication_failed", reason=str(e))
                else:
                    logger.debug(f"Authentication failed: {e}")

        response = self.get_response(request)
        return response


class APIRateLimitMiddleware:
    """
    Rate limiting middleware for API endpoints.

    Checks if authenticated users have available API quota based on
    their subscription plan. Returns 429 (Too Many Requests) if
    rate limit is exceeded.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        # Apply rate limiting to API endpoints for authenticated users
        if (
            request.path.startswith("/api/core/")
            and hasattr(request, "user")
            and request.user
            and getattr(request.user, "is_authenticated", False)
        ):
            try:
                can_use_api, details = SubscriptionService.check_api_limit(request.user)
                if not can_use_api:
                    message = (
                        details.get("error", "API rate limit exceeded")
                        if isinstance(details, dict)
                        else str(details)
                    )
                    if USE_STRUCTURED_LOGGING:
                        logger.warning(
                            "rate_limit_exceeded",
                            user_id=getattr(request.user, "user_id", None),
                            user_email=getattr(request.user, "email", None),
                            path=request.path,
                        )
                    return JsonResponse(
                        {
                            "error": "API rate limit exceeded",
                            "message": message,
                        },
                        status=429,
                    )

            except Exception as e:
                if USE_STRUCTURED_LOGGING:
                    logger.error(
                        "rate_limit_check_failed",
                        user_email=getattr(request.user, "email", None),
                        error=str(e),
                    )
                else:
                    logger.error(
                        f"Error checking API rate limit for {getattr(request.user, 'email', 'unknown')}: {e}"
                    )

        response = self.get_response(request)
        return response


class RequestLoggingMiddleware:
    """
    Middleware that logs all HTTP requests and responses with timing.

    This middleware automatically logs:
    - Request method and path
    - Response status code
    - Request duration
    - User context (if authenticated)
    - Client IP address

    Logs are structured JSON in production, formatted text in development.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        start_time = time.time()

        # Generate request ID if not already set by StructlogMiddleware
        request_id = getattr(request, "request_id", None)

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration = time.time() - start_time

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Get user info if available
        user_id = getattr(request, "user_id", None)
        user_email = getattr(request, "user", None)
        if user_email and hasattr(user_email, "email"):
            user_email = user_email.email

        # Log request
        if USE_STRUCTURED_LOGGING:
            logger.info(
                "http_request",
                request_id=request_id,
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_seconds=round(duration, 4),
                user_id=user_id,
                client_ip=client_ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:200],
            )
        else:
            logger.info(
                f"{request.method} {request.path} - "
                f"{response.status_code} - {duration:.4f}s - {client_ip}"
            )

        return response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Get client IP address from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class LanguageMiddleware:
    """
    Middleware to activate the user's preferred language.

    Checks (in order):
    1. Accept-Language header
    2. User.preferred_language (if authenticated)
    3. Falls back to settings.LANGUAGE_CODE
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        from django.conf import settings
        from django.utils import translation

        language = None

        # Check Accept-Language header first
        accept_lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        if accept_lang:
            # Extract primary language code
            primary = accept_lang.split(",")[0].split(";")[0].strip()
            lang_code = primary.split("-")[0].lower()
            supported = [code for code, _ in settings.LANGUAGES]
            if lang_code in supported:
                language = lang_code

        # Override with user preference if authenticated
        user = getattr(request, "user", None)
        if user and hasattr(user, "is_authenticated") and user.is_authenticated:
            user_lang = getattr(user, "preferred_language", None)
            if user_lang:
                supported = [code for code, _ in settings.LANGUAGES]
                if user_lang in supported:
                    language = user_lang

        # Activate language
        language = language or settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language

        response = self.get_response(request)

        translation.deactivate()
        return response
