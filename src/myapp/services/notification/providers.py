# myapp/services/notification/providers.py
"""
Notification provider implementations.

Moved from myapp.apis.core.notifications.providers to the service layer
since providers are infrastructure, not API concerns.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    @abstractmethod
    def send(
        self, recipient: str, message: str, subject: str | None = None, **kwargs
    ) -> bool:
        """
        Send a notification.

        Args:
            recipient: The recipient identifier (email, phone number, token)
            message: The message body
            subject: The message subject (optional, for email)
            **kwargs: Additional provider-specific arguments

        Returns:
            True if sent successfully, False otherwise.
        """

    @abstractmethod
    def validate_config(self) -> bool:
        """Check if the provider is properly configured."""


class SendGridProvider(NotificationProvider):
    """Email provider using SendGrid."""

    def __init__(self, api_key: str, default_from_email: str):
        self.api_key = api_key
        self.default_from_email = default_from_email

    def validate_config(self) -> bool:
        return bool(self.api_key and self.default_from_email)

    def send(
        self, recipient: str, message: str, subject: str | None = None, **kwargs
    ) -> bool:
        if not self.validate_config():
            logger.warning("SendGrid not configured — email logged but not sent.")
            logger.info(
                f"[EMAIL LOG] To: {recipient}, Subject: {subject}, Body: {message[:200]}"
            )
            return False

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = SendGridAPIClient(api_key=self.api_key)
            from_email = Email(self.default_from_email)
            to_email = To(recipient)
            content = Content("text/plain", message)

            html_content = kwargs.get("html_content")
            if html_content:
                content = Content("text/html", html_content)

            mail = Mail(from_email, to_email, subject or "Notification", content)

            template_id = kwargs.get("template_id")
            if template_id:
                mail.template_id = template_id

            template_data = kwargs.get("template_data")
            if template_data:
                mail.dynamic_template_data = template_data

            response = sg.client.mail.send.post(request_body=mail.get())

            if response.status_code in (200, 201, 202):
                logger.info(
                    f"Email sent to {recipient} via SendGrid (status: {response.status_code})"
                )
                return True
            else:
                logger.error(f"SendGrid API returned status {response.status_code}")
                return False

        except ImportError:
            logger.warning("SendGrid SDK not installed — run: pip install sendgrid")
            logger.info(
                f"[EMAIL LOG] To: {recipient}, Subject: {subject}, Body: {message[:200]}"
            )
            return False
        except Exception as e:
            logger.error(f"SendGrid error sending email to {recipient}: {e}")
            return False


class TwilioProvider(NotificationProvider):
    """SMS provider using Twilio."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def validate_config(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def send(
        self, recipient: str, message: str, subject: str | None = None, **kwargs
    ) -> bool:
        if not self.validate_config():
            logger.warning("Twilio not configured — SMS logged but not sent.")
            logger.info(f"[SMS LOG] To: {recipient}, Body: {message[:200]}")
            return False

        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)

            sms_body = f"{subject}: {message}" if subject else message
            if len(sms_body) > 1600:
                sms_body = sms_body[:1597] + "..."

            tw_message = client.messages.create(
                body=sms_body, from_=self.from_number, to=recipient
            )

            logger.info(f"SMS sent to {recipient} via Twilio (SID: {tw_message.sid})")
            return True

        except ImportError:
            logger.warning("Twilio SDK not installed — run: pip install twilio")
            logger.info(f"[SMS LOG] To: {recipient}, Body: {message[:200]}")
            return False
        except Exception as e:
            logger.error(f"Twilio error sending SMS to {recipient}: {e}")
            return False


class FirebaseProvider(NotificationProvider):
    """Push notification provider using Firebase Cloud Messaging (FCM)."""

    _initialized = False

    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path

    def validate_config(self) -> bool:
        return bool(self.credentials_path)

    def _ensure_initialized(self):
        """Initialize Firebase Admin SDK if not already done."""
        if FirebaseProvider._initialized:
            return True

        try:
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credentials_path)
                firebase_admin.initialize_app(cred)

            FirebaseProvider._initialized = True
            return True

        except ImportError:
            logger.warning(
                "Firebase Admin SDK not installed — run: pip install firebase-admin"
            )
            return False
        except Exception as e:
            logger.error(f"Firebase initialization error: {e}")
            return False

    def send(
        self, recipient: str, message: str, subject: str | None = None, **kwargs
    ) -> bool:
        """Send a push notification. Recipient is the FCM device token."""
        if not self.validate_config():
            logger.warning(
                "Firebase not configured — push notification logged but not sent."
            )
            logger.info(
                f"[PUSH LOG] Token: {recipient[:20]}..., Title: {subject}, Body: {message[:200]}"
            )
            return False

        try:
            if not self._ensure_initialized():
                logger.info(
                    f"[PUSH LOG] Token: {recipient[:20]}..., Title: {subject}, Body: {message[:200]}"
                )
                return False

            from firebase_admin import messaging

            notification = messaging.Notification(
                title=subject or "Notification",
                body=message,
            )

            data = kwargs.get("data", {})

            fcm_message = messaging.Message(
                notification=notification,
                token=recipient,
                data={k: str(v) for k, v in data.items()} if data else None,
            )

            response = messaging.send(fcm_message)
            logger.info(f"Push notification sent via Firebase (response: {response})")
            return True

        except ImportError:
            logger.warning(
                "Firebase Admin SDK not installed — run: pip install firebase-admin"
            )
            logger.info(
                f"[PUSH LOG] Token: {recipient[:20]}..., Title: {subject}, Body: {message[:200]}"
            )
            return False
        except Exception as e:
            logger.error(f"Firebase error sending push to {recipient[:20]}...: {e}")
            return False


class NotificationProviderFactory:
    """Factory to get notification providers based on channel type."""

    @staticmethod
    def get_provider(
        provider_type: str, config: dict[str, Any]
    ) -> NotificationProvider:
        if provider_type == "email":
            return SendGridProvider(
                api_key=config.get("SENDGRID_API_KEY", ""),
                default_from_email=config.get("DEFAULT_FROM_EMAIL", ""),
            )
        elif provider_type == "sms":
            return TwilioProvider(
                account_sid=config.get("TWILIO_ACCOUNT_SID", ""),
                auth_token=config.get("TWILIO_AUTH_TOKEN", ""),
                from_number=config.get("TWILIO_FROM_NUMBER", ""),
            )
        elif provider_type == "push":
            return FirebaseProvider(
                credentials_path=config.get("FIREBASE_CREDENTIALS_PATH", "")
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
