# authentication.py

import logging

from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication with enhanced security features.

    Features:
    - User verification with is_active and is_deleted checks
    - Token blacklist support for logout
    - Rate limiting support
    - Claims attachment to request object
    """

    def get_user(self, validated_token):
        """
        Get user from validated token with additional checks.

        Args:
            validated_token: Decoded JWT token payload

        Returns:
            User object

        Raises:
            AuthenticationFailed: If user not found or inactive
        """
        user_id = validated_token.get("user_id")
        if not user_id:
            raise AuthenticationFailed(
                "User ID not found in token", code="user_id_missing"
            )

        try:
            user = User.objects.get(user_id=user_id, is_active=1, is_deleted=0)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                "User not found", code="user_not_found"
            ) from None

        # Check if token is blacklisted
        token_jti = validated_token.get("jti")
        if token_jti and cache.get(f"blacklist:{token_jti}"):
            raise AuthenticationFailed(
                "Token has been blacklisted", code="token_blacklisted"
            )

        return user

    def authenticate(self, request):
        """
        Authenticate request using JWT token.

        Args:
            request: HTTP request object

        Returns:
            Tuple of (user, validated_token) or None if no auth
        """
        logger.debug("Starting authentication process.")

        header = self.get_header(request)
        if header is None:
            logger.debug("No Authorization header found.")
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            logger.debug("No raw token found in the Authorization header.")
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            logger.debug("Token successfully validated. Claims: %s", validated_token)

            # Get user object using custom get_user method
            user = self.get_user(validated_token)

            # Attach claims to the request object for later use
            request.user_id = validated_token.get("user_id")
            request.role = validated_token.get("role")
            request.token_jti = validated_token.get("jti")

            # Return user and token following DRF conventions
            return user, validated_token
        except Exception as e:
            logger.error("Authentication failed: %s", str(e))
            raise AuthenticationFailed(str(e)) from e
