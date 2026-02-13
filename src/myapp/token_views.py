# token_views.py
"""
JWT token refresh views.

Separated from authentication.py to avoid circular imports with Django settings.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import User

logger = logging.getLogger(__name__)


class EnhancedTokenRefreshView(TokenRefreshView):
    """
    Enhanced token refresh view with blacklist support.

    Features:
    - Automatic refresh token rotation
    - Old refresh token blacklisting
    - Logout functionality
    """

    def post(self, request, *args, **kwargs):
        """
        Refresh access token using refresh token.

        This implementation supports:
        - Token rotation for enhanced security
        - Logout by blacklisting refresh token

        Request body:
            refresh: Refresh token
            logout: Optional boolean to logout (blacklist token)

        Returns:
            - New access token if refresh is valid
            - Logout confirmation if logout=True
        """
        refresh_token = request.data.get("refresh")
        logout = request.data.get("logout", False)

        if not refresh_token:
            raise ValidationError(
                {"detail": "Refresh token is required"}, code="refresh_token_required"
            )

        try:
            # Validate refresh token
            refresh = RefreshToken(refresh_token)
            user_id = refresh["user_id"]
            jti = refresh.get("jti")

            # Check if token is already blacklisted
            if jti and cache.get(f"blacklist:{jti}"):
                raise ValidationError(
                    {"detail": "Refresh token has been revoked"}, code="token_revoked"
                )

            # Handle logout
            if logout:
                if jti:
                    # Blacklist the refresh token
                    refresh_lifetime = settings.SIMPLE_JWT.get(
                        "REFRESH_TOKEN_LIFETIME", timedelta(days=7)
                    )
                    cache.set(
                        f"blacklist:{jti}",
                        "1",
                        timeout=int(refresh_lifetime.total_seconds()),
                    )
                return Response(
                    {"detail": "Successfully logged out"}, status=status.HTTP_200_OK
                )

            # Get user
            try:
                user = User.objects.get(user_id=user_id, is_active=1, is_deleted=0)
            except User.DoesNotExist:
                raise AuthenticationFailed(
                    "User not found", code="user_not_found"
                ) from None

            # Create new access token
            access_token = AccessToken.for_user(user)

            # Token rotation: blacklist old refresh token and create new one
            new_refresh_token = str(refresh)
            if jti:
                refresh_lifetime = settings.SIMPLE_JWT.get(
                    "REFRESH_TOKEN_LIFETIME", timedelta(days=7)
                )
                cache.set(
                    f"blacklist:{jti}",
                    "1",
                    timeout=int(refresh_lifetime.total_seconds()),
                )

            return Response(
                {
                    "access": str(access_token),
                    "refresh": new_refresh_token,
                    "user_id": user_id,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error("Token refresh failed: %s", str(e))
            raise AuthenticationFailed(
                "Invalid refresh token", code="invalid_refresh_token"
            ) from e


def blacklist_token(token_jti: str, lifetime: int | None = None) -> bool:
    """
    Add a token to the blacklist.

    Args:
        token_jti: JWT ID to blacklist
        lifetime: Optional custom lifetime (uses settings default if None)

    Returns:
        True if token was blacklisted successfully
    """
    if lifetime is None:
        lifetime = settings.SIMPLE_JWT.get(
            "REFRESH_TOKEN_LIFETIME", timedelta(days=7)
        ).total_seconds()

    cache.set(f"blacklist:{token_jti}", "1", timeout=int(lifetime))
    return True


def is_token_blacklisted(token_jti: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        token_jti: JWT ID to check

    Returns:
        True if token is blacklisted
    """
    return bool(cache.get(f"blacklist:{token_jti}"))
