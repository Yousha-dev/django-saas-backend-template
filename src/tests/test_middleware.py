"""
Unit tests for custom middleware.

Tests cover LanguageMiddleware, APIRateLimitMiddleware,
RequestLoggingMiddleware, and JWTAuthenticationMiddleware.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpResponse
from django.test import RequestFactory


@pytest.mark.unit
class TestLanguageMiddleware:
    """Tests for LanguageMiddleware."""

    def _get_middleware(self):
        from myapp.middleware import LanguageMiddleware

        return LanguageMiddleware(get_response=lambda r: HttpResponse("OK"))

    def test_default_language_fallback(self):
        """Test fallback to settings.LANGUAGE_CODE when no header or user pref."""
        from django.conf import settings

        middleware = self._get_middleware()
        request = RequestFactory().get("/api/test/")
        request.user = MagicMock(is_authenticated=False)
        request.META.pop("HTTP_ACCEPT_LANGUAGE", None)

        middleware(request)
        assert request.LANGUAGE_CODE == settings.LANGUAGE_CODE

    def test_accept_language_header(self):
        """Test Accept-Language header is respected."""
        middleware = self._get_middleware()
        request = RequestFactory().get("/api/test/")
        request.META["HTTP_ACCEPT_LANGUAGE"] = "es,en;q=0.9"
        request.user = MagicMock(is_authenticated=False)

        middleware(request)
        assert request.LANGUAGE_CODE == "es"

    def test_user_preferred_language_overrides_header(self):
        """Test authenticated user's preferred_language overrides Accept-Language."""
        middleware = self._get_middleware()
        request = RequestFactory().get("/api/test/")
        request.META["HTTP_ACCEPT_LANGUAGE"] = "es"

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.preferred_language = "en"
        request.user = mock_user

        middleware(request)
        assert request.LANGUAGE_CODE == "en"

    def test_unsupported_language_ignored(self):
        """Test unsupported language code falls back to default."""
        from django.conf import settings

        middleware = self._get_middleware()
        request = RequestFactory().get("/api/test/")
        request.META["HTTP_ACCEPT_LANGUAGE"] = "xx-UNK"
        request.user = MagicMock(is_authenticated=False)

        middleware(request)
        assert request.LANGUAGE_CODE == settings.LANGUAGE_CODE


@pytest.mark.unit
class TestAPIRateLimitMiddleware:
    """Tests for APIRateLimitMiddleware."""

    def _get_middleware(self):
        from myapp.middleware import APIRateLimitMiddleware

        return APIRateLimitMiddleware(get_response=lambda r: HttpResponse("OK"))

    def test_non_api_path_not_rate_limited(self):
        """Test non-API paths bypass rate limiting."""
        middleware = self._get_middleware()
        request = RequestFactory().get("/admin/")
        request.user = MagicMock(is_authenticated=True)

        response = middleware(request)
        assert response.status_code == 200

    def test_unauthenticated_user_not_rate_limited(self):
        """Test unauthenticated users bypass rate limiting."""
        middleware = self._get_middleware()
        request = RequestFactory().get("/api/core/test/")
        request.user = MagicMock(is_authenticated=False)

        response = middleware(request)
        assert response.status_code == 200

    @patch("myapp.middleware.SubscriptionService")
    def test_rate_limit_exceeded_returns_429(self, mock_service):
        """Test 429 is returned when rate limit is exceeded."""
        mock_service.check_api_limit.return_value = (
            False,
            {"error": "API rate limit exceeded"},
        )

        middleware = self._get_middleware()
        request = RequestFactory().get("/api/core/events/")
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.user_id = 1
        mock_user.email = "test@example.com"
        request.user = mock_user

        response = middleware(request)
        assert response.status_code == 429

    @patch("myapp.middleware.SubscriptionService")
    def test_allowed_when_under_limit(self, mock_service):
        """Test request proceeds when under rate limit."""
        mock_service.check_api_limit.return_value = (
            True,
            {"max_calls_per_hour": 100, "current_usage": 5},
        )

        middleware = self._get_middleware()
        request = RequestFactory().get("/api/core/events/")
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        request.user = mock_user

        response = middleware(request)
        assert response.status_code == 200


@pytest.mark.unit
class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    def _get_middleware(self):
        from myapp.middleware import RequestLoggingMiddleware

        return RequestLoggingMiddleware(get_response=lambda r: HttpResponse("OK"))

    def test_logs_request_and_returns_response(self):
        """Test middleware logs and returns response untouched."""
        middleware = self._get_middleware()
        request = RequestFactory().get("/api/test/")
        request.user = MagicMock(is_authenticated=False)

        response = middleware(request)
        assert response.status_code == 200

    def test_get_client_ip_from_forwarded_for(self):
        """Test client IP extraction from X-Forwarded-For header."""
        from myapp.middleware import RequestLoggingMiddleware

        request = RequestFactory().get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4, 5.6.7.8"
        ip = RequestLoggingMiddleware._get_client_ip(request)
        assert ip == "1.2.3.4"

    def test_get_client_ip_from_remote_addr(self):
        """Test client IP extraction from REMOTE_ADDR."""
        from myapp.middleware import RequestLoggingMiddleware

        request = RequestFactory().get("/")
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        ip = RequestLoggingMiddleware._get_client_ip(request)
        assert ip == "10.0.0.1"


@pytest.mark.unit
class TestJWTAuthenticationMiddleware:
    """Tests for JWTAuthenticationMiddleware."""

    def _get_middleware(self):
        from myapp.middleware import JWTAuthenticationMiddleware

        return JWTAuthenticationMiddleware(get_response=lambda r: HttpResponse("OK"))

    def test_no_auth_header_passes_through(self):
        """Test request without Authorization header passes through."""
        middleware = self._get_middleware()
        request = RequestFactory().get("/api/test/")

        response = middleware(request)
        assert response.status_code == 200

    @patch("myapp.middleware.CustomJWTAuthentication")
    def test_valid_token_attaches_user(self, mock_auth_class):
        """Test valid JWT token attaches user info to request."""
        mock_user = MagicMock()
        mock_user.user_id = 42
        mock_token = {"user_id": 42, "role": "user"}

        mock_auth = MagicMock()
        mock_auth.authenticate.return_value = (mock_user, mock_token)
        mock_auth_class.return_value = mock_auth

        middleware = self._get_middleware()
        request = RequestFactory().get(
            "/api/test/", HTTP_AUTHORIZATION="Bearer test123"
        )

        middleware(request)
        assert request.user == mock_user
        assert request.user_id == 42
        assert request.role == "user"

    @patch("myapp.middleware.CustomJWTAuthentication")
    def test_invalid_token_does_not_crash(self, mock_auth_class):
        """Test invalid JWT token is handled gracefully."""
        from rest_framework.exceptions import AuthenticationFailed

        mock_auth = MagicMock()
        mock_auth.authenticate.side_effect = AuthenticationFailed("Invalid token")
        mock_auth_class.return_value = mock_auth

        middleware = self._get_middleware()
        request = RequestFactory().get("/api/test/", HTTP_AUTHORIZATION="Bearer bad")

        response = middleware(request)
        assert response.status_code == 200  # Should not crash
