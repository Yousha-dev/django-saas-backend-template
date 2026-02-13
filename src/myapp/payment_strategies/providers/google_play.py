# myapp/payment_strategies/providers/google_play.py
"""
Google Play Billing Provider.

Handles purchase token validation and subscription status checks for Android apps.

Uses Google Play Developer API for purchase validation.
"""

import json
import logging
from decimal import Decimal
from typing import Any

from myapp.payment_strategies.base import (
    PaymentError,
    PaymentProvider,
    PaymentResult,
    PaymentStatus,
    RefundResult,
    SubscriptionResult,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


class GooglePlayProvider(PaymentProvider):
    """
    Google Play Billing Provider.

    Implements PaymentProvider interface for Google Play's Billing system.
    Handles purchase token validation, subscription management, and real-time developer notifications.

    Uses Google Play Developer API V3 for subscription and purchase validation.

    Configuration:
        - package_name: App package name (e.g., com.example.app)
        - service_account_info: Service account JSON string or path
        - credentials_path: Path to service account JSON credentials file
        - timeout: Request timeout in seconds (default: 10)
    """

    provider_name = "google_play"
    display_name = "Google Play Billing"

    # Google Play Developer API V3 endpoints
    API_BASE_URL = (
        "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
    )

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize Google Play provider.

        Args:
            config: Configuration dict with optional keys:
                - package_name: App package name
                - service_account_info: Service account JSON string
                - credentials_path: Path to credentials file
                - timeout: Request timeout (default: 10)
        """
        super().__init__(config)

        self.package_name = self.config.get("package_name", "")
        self.service_account_info = self.config.get("service_account_info", "")
        self.credentials_path = self.config.get("credentials_path", "")
        self.timeout = self.config.get("timeout", 10)
        self.logger = logging.getLogger(__name__)

        # Setup will be initialized when credentials are loaded
        self._credentials = None
        self._http = None

    def _setup_client(self):
        """Setup Google API client with credentials."""
        try:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2 import service_account

            # Load credentials
            if self.service_account_info:
                # Direct JSON string
                credentials = service_account.Credentials.from_service_account_info(
                    self.service_account_info
                )
            elif self.credentials_path:
                # From file
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
            else:
                logger.error("No Google Play credentials configured")
                return False

            self._credentials = credentials

            # Create authorized session
            self._http = AuthorizedSession(credentials)

            return True

        except ImportError:
            self.logger.warning(
                "Google API client libraries not available. "
                "Install: google-api-python-client"
            )
            return False
        except Exception as e:
            self.logger.error(f"Error setting up Google API client: {e}")
            return False

    def is_configured(self) -> bool:
        """
        Check if provider is properly configured.

        Returns:
            True if package_name and credentials are configured.
        """
        return bool(
            self.package_name and (self.service_account_info or self.credentials_path)
        )

    def create_payment_intent(
        self,
        amount: Decimal | float,
        currency: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        customer_email: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Google Play doesn't support traditional payment intents.

        Purchases are handled client-side via Google Play Billing Library.

        Args:
            amount: Not used for Google Play
            currency: Not used for Google Play
            description: Not used for Google Play
            metadata: Not used for Google Play
            customer_email: Not used for Google Play

        Returns:
            PaymentResult indicating operation not supported
        """
        return PaymentResult(
            success=False,
            status=PaymentStatus.FAILED,
            message="Google Play Billing does not support payment intents. "
            "Purchases are handled client-side via Google Play Billing Library.",
            provider=self.provider_name,
            error=PaymentError(
                message="Payment intents are not supported by Google Play Billing. "
                "Use validate_purchase() instead.",
                code="NOT_SUPPORTED",
                provider=self.provider_name,
            ),
        )

    def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Google Play doesn't support traditional payment confirmation.

        Purchase token validation serves as confirmation.

        Args:
            payment_intent_id: Purchase token
            payment_method_id: Not used for Google Play
            **kwargs: Additional parameters

        Returns:
            PaymentResult indicating operation not supported
        """
        return PaymentResult(
            success=False,
            status=PaymentStatus.FAILED,
            message="Google Play Billing does not support payment confirmation. "
            "Use validate_purchase() with purchase token instead.",
            provider=self.provider_name,
            error=PaymentError(
                message="Payment confirmation is not supported by Google Play Billing. "
                "Use validate_purchase() instead.",
                code="NOT_SUPPORTED",
                provider=self.provider_name,
            ),
        )

    def get_payment_status(
        self,
        transaction_id: str,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Check status of a purchase using Google Play Developer API.

        Args:
            transaction_id: Purchase token
            **kwargs: Additional parameters including:
                - product_id: Product/SKU ID

        Returns:
            PaymentResult with current status and details
        """
        product_id = kwargs.get("product_id")

        if not product_id:
            return PaymentResult(
                success=False,
                status=PaymentStatus.FAILED,
                message="Product ID is required to check purchase status",
                provider=self.provider_name,
                error=PaymentError(
                    message="Product ID is required",
                    code="MISSING_PRODUCT_ID",
                    provider=self.provider_name,
                ),
            )

        validation_result = self.validate_purchase(
            purchase_token=transaction_id, product_id=product_id
        )

        if validation_result.get("status") == "valid":
            return PaymentResult(
                success=True,
                transaction_id=transaction_id,
                provider_transaction_id=transaction_id,
                status=PaymentStatus.COMPLETED,
                message="Payment status retrieved successfully",
                provider=self.provider_name,
                provider_data=validation_result,
            )

        return PaymentResult(
            success=False,
            transaction_id=transaction_id,
            status=PaymentStatus.FAILED,
            message=validation_result.get("message", "Purchase validation failed"),
            provider=self.provider_name,
            provider_data=validation_result,
        )

    def validate_purchase(
        self,
        purchase_token: str,
        product_id: str,
    ) -> dict[str, Any]:
        """
        Validate a purchase using Google Play Developer API V3.

        Args:
            purchase_token: Purchase token from Google Play
            product_id: Product/SKU ID

        Returns:
            Dict with validation result containing:
                - status: 'valid', 'cancelled', 'pending', etc.
                - order_id: Google Play order ID
                - purchase_time: Purchase timestamp
                - acknowledgement_state: Purchase acknowledgement state
                - provider_data: Full API response for reference
        """
        self.logger.info(f"Validating Google Play purchase token for {product_id}")

        if not self._setup_client():
            return {
                "status": "client_error",
                "message": "Google Play API client not available. "
                "Install google-api-python-client",
            }

        try:
            from googleapiclient.errors import HttpError

            # Call Purchases.subscriptionsv2.get() API
            url = f"{self.API_BASE_URL}/{self.package_name}/purchases/subscriptionsv2/tokens/{purchase_token}"

            response = self._http.get(
                uri=url,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Google Play API returned status {response.status_code}"
                )
                return {
                    "status": "api_error",
                    "message": f"Google Play API error: {response.status_code}",
                    "error_details": response.text if response.text else "",
                }

            result = response.json()

            # Check acknowledgement state
            # States: 0=PENDING, 1=ACKNOWLEDGED, 2=STATE_TRANSITION
            acknowledgement_state = result.get("acknowledgementState", 0)

            return {
                "status": "valid" if acknowledgement_state == 1 else "pending",
                "order_id": result.get("orderId", ""),
                "purchase_time": result.get("purchaseTimeMillis", 0) / 1000,
                "acknowledgement_state": acknowledgement_state,
                "provider_data": result,
            }

        except HttpError as e:
            self.logger.error(f"Google Play API HTTP error: {e}")
            return {
                "status": "http_error",
                "message": f"HTTP error: {e!s}",
                "error_details": str(e),
            }
        except Exception as e:
            self.logger.error(f"Error validating Google Play purchase: {e}")
            return {
                "status": "error",
                "message": f"Validation error: {e!s}",
                "error_details": str(e),
            }

    def get_subscription_status(
        self,
        product_id: str,
        purchase_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Check status of a subscription using Google Play Developer API.

        Args:
            product_id: Subscription product ID (SKU)
            purchase_token: Purchase token for validation

        Returns:
            Dict with subscription status information:
                - status: 'active', 'expired', 'pending', etc.
                - expiry_time: ISO format expiry time
                - provider_data: Full API response
        """
        self.logger.info(f"Checking Google Play subscription status for {product_id}")

        # Validate the purchase token first
        validation_result = self.validate_purchase(
            purchase_token=purchase_token, product_id=product_id
        )

        if validation_result.get("status") == "valid":
            provider_data = validation_result.get("provider_data", {})

            # Check subscription status from response
            # For subscriptions, check if the subscription is active
            expiry_time_millis = provider_data.get("expiryTimeMillis", 0)

            if expiry_time_millis:
                from datetime import datetime
                from datetime import timezone as dt_timezone

                expiry_time = datetime.fromtimestamp(
                    expiry_time_millis / 1000, tz=dt_timezone.utc
                )

                now = datetime.now(dt_timezone.utc)

                if expiry_time > now:
                    return {
                        "status": "active",
                        "expiry_time": expiry_time.isoformat(),
                        "provider_data": provider_data,
                    }
                else:
                    return {
                        "status": "expired",
                        "expiry_time": expiry_time.isoformat(),
                        "provider_data": provider_data,
                    }

            return {
                "status": validation_result.get("status", "unknown"),
                "provider_data": provider_data,
            }

        return {
            "status": "unknown",
            "message": "Purchase validation failed",
        }

    def create_subscription(
        self,
        plan_id: str,
        customer_email: str | None = None,
        metadata: dict[str, Any] | None = None,
        trial_days: int = 0,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Google Play subscriptions are created client-side.

        Returns pending result indicating client-side action required.

        Args:
            plan_id: Product/SKU ID
            customer_email: Not used by Google Play
            metadata: Additional metadata
            trial_days: Configured in Play Console
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult with client-side instructions
        """
        return SubscriptionResult(
            success=False,
            status="pending_client_action",
            plan_id=plan_id,
            message="Google Play subscriptions must be created client-side via Google Play Billing Library. "
            "Validate the purchase token after purchase.",
            provider=self.provider_name,
            provider_data={
                "product_id": plan_id,
                "action_required": "Initiate purchase through Android Google Play Billing Library",
                "validate_purchase_after": "Call validate_purchase() with purchase token",
                "trial_days": trial_days,
            },
        )

    def cancel_subscription(
        self,
        provider_subscription_id: str,
        cancel_at_period_end: bool = True,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Cancel a Google Play subscription.

        Google doesn't provide a server-side API for cancellation.
        Cancellation must be handled client-side via Google Play Billing Library.

        Args:
            provider_subscription_id: Purchase token
            cancel_at_period_end: If True, cancel at period end
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult indicating cancellation method
        """
        self.logger.info(
            f"Google Play subscription cancel requested for {provider_subscription_id}"
        )

        return SubscriptionResult(
            success=False,
            status="cancellation_not_supported",
            provider_subscription_id=provider_subscription_id,
            message="Google Play subscriptions cannot be cancelled server-side. "
            "User must cancel via device Settings > Google Play > Subscriptions.",
            provider=self.provider_name,
            provider_data={
                "purchase_token": provider_subscription_id,
                "action_required": "User must cancel via device Settings > Google Play > Subscriptions",
                "cancel_at_period_end": cancel_at_period_end,
            },
        )

    def update_subscription(
        self,
        provider_subscription_id: str,
        plan_id: str | None = None,
        quantity: int | None = None,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Update a Google Play subscription.

        Google doesn't provide a server-side API for subscription updates.
        Plan changes must be handled client-side via Google Play Billing Library.

        Args:
            provider_subscription_id: Purchase token
            plan_id: New product ID (not supported for update)
            quantity: Quantity (not used for Google Play)
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult indicating update method
        """
        return SubscriptionResult(
            success=False,
            status="update_not_supported",
            provider_subscription_id=provider_subscription_id,
            message="Google Play subscriptions cannot be updated server-side. "
            "Plan changes require user to purchase new subscription via Google Play Billing Library.",
            provider=self.provider_name,
            provider_data={
                "current_purchase_token": provider_subscription_id,
                "new_product_id": plan_id,
                "action_required": "User must purchase new subscription via device Google Play",
            },
        )

    def refund_payment(
        self,
        transaction_id: str,
        amount: Decimal | float | None = None,
        reason: str = "",
        **kwargs: Any,
    ) -> RefundResult:
        """
        Process a refund for Google Play purchase.

        Google Play refunds must be processed through Google Play Console.
        This method records the refund intent.

        Args:
            transaction_id: Original purchase token
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Additional parameters

        Returns:
            RefundResult with refund details
        """
        self.logger.info(f"Google Play refund requested for {transaction_id}: {reason}")

        return RefundResult(
            success=False,
            refund_id=f"refund_{transaction_id}",
            provider_refund_id=transaction_id,
            amount=Decimal(str(amount)) if amount else Decimal("0"),
            currency="USD",
            status="pending_manual_processing",
            reason=reason,
            message="Google Play refunds must be processed through Google Play Console.",
            provider=self.provider_name,
            provider_data={
                "purchase_token": transaction_id,
                "action_required": "Process refund via Google Play Console > Orders",
                "reason": reason,
            },
        )

    def parse_webhook(
        self,
        payload: bytes | str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> WebhookEvent:
        """
        Parse a Google Play Realtime Developer Notification V3 webhook.

        Args:
            payload: Raw webhook payload (JSON)
            headers: HTTP headers (for authentication verification)
            **kwargs: Additional parameters

        Returns:
            WebhookEvent with parsed data

        Raises:
            PaymentError: If payload is invalid
        """
        self.logger.info("Parsing Google Play webhook")

        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")

            data = json.loads(payload) if isinstance(payload, str | bytes) else {}

            # Extract version and event type
            version = data.get("version", "")
            event_type = version  # In V3, event type is the version number

            return WebhookEvent(
                event_id=data.get("id", ""),
                event_type=event_type,
                provider=self.provider_name,
                payload=data,
                received_at=data.get("eventTimeMillis", 0) / 1000,
                provider_data={
                    "version": version,
                    "package_name": data.get("packageName", ""),
                    "event_time": data.get("eventTimeMillis", 0) / 1000,
                },
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in Google webhook: {e}")
            raise PaymentError(
                message="Invalid JSON payload",
                code="INVALID_PAYLOAD",
                provider=self.provider_name,
                details={"original_error": str(e)},
            ) from e
        except Exception as e:
            self.logger.error(f"Error parsing Google webhook: {e}")
            raise PaymentError(
                message="Failed to parse webhook payload",
                code="PARSING_ERROR",
                provider=self.provider_name,
                details={"original_error": str(e)},
            ) from e
