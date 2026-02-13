# myapp/services/notification/notification_service.py
"""
Unified notification service.

Orchestrates sending notifications across multiple channels (email, SMS, push)
and creates in-app Notification records in the database.
"""

import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from .providers import NotificationProviderFactory

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service to orchestrate notification sending across multiple channels.

    Also creates in-app Notification records for the user's notification inbox.
    """

    def __init__(self):
        self.config = {
            "SENDGRID_API_KEY": getattr(settings, "SENDGRID_API_KEY", ""),
            "DEFAULT_FROM_EMAIL": getattr(settings, "DEFAULT_FROM_EMAIL", ""),
            "TWILIO_ACCOUNT_SID": getattr(settings, "TWILIO_ACCOUNT_SID", ""),
            "TWILIO_AUTH_TOKEN": getattr(settings, "TWILIO_AUTH_TOKEN", ""),
            "TWILIO_FROM_NUMBER": getattr(settings, "TWILIO_FROM_NUMBER", ""),
            "FIREBASE_CREDENTIALS_PATH": getattr(
                settings, "FIREBASE_CREDENTIALS_PATH", ""
            ),
        }

    def send_notification(
        self,
        user,
        title: str,
        message: str,
        channels: list[str] | None = None,
        data: dict[str, Any] | None = None,
        create_in_app: bool = True,
    ) -> dict[str, Any]:
        """
        Send notification to a user via specified (or preferred) channels.

        Args:
            user: User object with email, phone, fcm_token fields
            title: Notification title
            message: Notification body
            channels: List of channels ('email', 'sms', 'push').
                      If None, defaults to email if available.
            data: Extra data for push notifications/templates
            create_in_app: Whether to create an in-app Notification record

        Returns:
            Dict mapping channel names to success booleans
        """
        if not channels:
            channels = []
            if user.email:
                channels.append("email")
            if getattr(user, "phone", None):
                channels.append("sms")
            if getattr(user, "fcm_token", None):
                channels.append("push")
            # At minimum, try email
            if not channels and user.email:
                channels = ["email"]

        results: dict[str, Any] = {}

        for channel in channels:
            try:
                provider = NotificationProviderFactory.get_provider(
                    channel, self.config
                )
                recipient = self._get_recipient(user, channel)

                if recipient:
                    success = provider.send(
                        recipient, message, subject=title, data=data
                    )
                    results[channel] = success
                else:
                    logger.warning(
                        f"No recipient info for user {user.pk} on channel {channel}"
                    )
                    results[channel] = False

            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                results[channel] = False

        # Create in-app notification record
        if create_in_app:
            try:
                self._create_in_app_notification(user, title, message)
                results["in_app"] = True
            except Exception as e:
                logger.error(f"Failed to create in-app notification: {e}")
                results["in_app"] = False

        return results

    @staticmethod
    def _get_recipient(user, channel: str) -> str | None:
        """Get the recipient identifier for the given channel."""
        if channel == "email":
            return user.email
        elif channel == "sms":
            return getattr(user, "phone", None)
        elif channel == "push":
            return getattr(user, "fcm_token", None)
        return None

    @staticmethod
    def _create_in_app_notification(user, title: str, message: str) -> None:
        """Create an in-app Notification record in the database."""
        from myapp.models import Notification

        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            is_read=0,
            is_active=1,
            is_deleted=0,
            created_at=timezone.now(),
            created_by=user.user_id if hasattr(user, "user_id") else 0,
        )
