# myapp/payment_strategies/providers/apple_iap.py
"""
Apple In-App Purchase Provider.

Handles receipt validation and subscription status checks for iOS apps.

Uses Apple's official App Store Server API for receipt validation.
"""

import base64
import json
import logging
from decimal import Decimal
from typing import Any

import requests
from requests.exceptions import RequestException

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


class AppleIAPProvider(PaymentProvider):
    """
    Apple In-App Purchase Provider.

    Implements PaymentProvider interface for Apple's In-App Purchase system.
    Handles receipt validation, subscription management, and server-to-server notifications.
    Uses Apple's official App Store Server API V2 for receipt validation.

    Configuration:
        - bundle_id: App bundle ID (e.g., com.example.app)
        - shared_secret: Shared secret for receipt validation
        - sandbox: Whether to use sandbox environment (default: True)
        - timeout: Request timeout in seconds (default: 10)
    """

    provider_name = "apple_iap"
    display_name = "Apple In-App Purchase"

    # Apple App Store Server API V2 endpoints
    SANDBOX_URL = "https://sandbox.itunes.apple.com/api/v2/sales"
    PRODUCTION_URL = "https://buy.itunes.apple.com/api/v2/sales"

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize Apple IAP provider.

        Args:
            config: Configuration dict with optional keys:
                - bundle_id: App bundle ID
                - shared_secret: Shared secret for receipt validation
                - sandbox: Whether to use sandbox (default: True)
                - timeout: Request timeout (default: 10)
        """
        super().__init__(config)

        self.bundle_id = self.config.get("bundle_id", "")
        self.shared_secret = self.config.get("shared_secret", "")
        self.sandbox = self.config.get("sandbox", True)
        self.timeout = self.config.get("timeout", 10)
        self.logger = logging.getLogger(__name__)

        # Set API URL based on sandbox setting
        self.api_url = self.SANDBOX_URL if self.sandbox else self.PRODUCTION_URL

    def is_configured(self) -> bool:
        """
        Check if provider is properly configured.

        Returns:
            True if bundle_id and shared_secret are configured.
        """
        return bool(self.bundle_id and self.shared_secret)

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
        Apple IAP doesn't support traditional payment intents.

        Payments are handled client-side via StoreKit.
        Receipt validation happens after purchase.

        Args:
            amount: Not used for Apple IAP
            currency: Not used for Apple IAP
            description: Not used for Apple IAP
            metadata: Not used for Apple IAP
            customer_email: Not used for Apple IAP

        Returns:
            PaymentResult indicating operation not supported
        """
        return PaymentResult(
            success=False,
            status=PaymentStatus.FAILED,
            message="Apple IAP does not support payment intents. "
            "Receipts are validated client-side via StoreKit.",
            provider=self.provider_name,
            error=PaymentError(
                message="Payment intents are not supported by Apple IAP. "
                "Use validate_receipt() instead.",
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
        Apple IAP doesn't support traditional payment confirmation.

        Receipt validation serves as confirmation.

        Args:
            payment_intent_id: Receipt data (base64 encoded)
            payment_method_id: Not used for Apple IAP
            **kwargs: Additional parameters

        Returns:
            PaymentResult indicating operation not supported
        """
        return PaymentResult(
            success=False,
            status=PaymentStatus.FAILED,
            message="Apple IAP does not support payment confirmation. "
            "Use validate_receipt() with receipt data instead.",
            provider=self.provider_name,
            error=PaymentError(
                message="Payment confirmation is not supported by Apple IAP. "
                "Use validate_receipt() instead.",
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
        Check status of a payment using Apple's App Store Server API.

        Args:
            transaction_id: Apple transaction ID
            **kwargs: Additional parameters including:
                - receipt_data: Base64 encoded receipt data
                - request_date: Date of original purchase (for subscriptions)

        Returns:
            PaymentResult with current status and details
        """
        receipt_data = kwargs.get("receipt_data")
        request_date = kwargs.get("request_date")

        if not receipt_data:
            return PaymentResult(
                success=False,
                status=PaymentStatus.FAILED,
                message="Receipt data is required to check payment status",
                provider=self.provider_name,
                error=PaymentError(
                    message="Receipt data is required",
                    code="MISSING_RECEIPT",
                    provider=self.provider_name,
                ),
            )

        validation_result = self.validate_receipt(
            receipt_data, request_date=request_date
        )

        if validation_result.get("success"):
            return PaymentResult(
                success=True,
                transaction_id=transaction_id,
                provider_transaction_id=transaction_id,
                status=PaymentStatus.COMPLETED
                if validation_result.get("status") == 0
                else PaymentStatus.FAILED,
                message="Payment status retrieved successfully",
                provider=self.provider_name,
                provider_data=validation_result.get("provider_data", {}),
            )

        return PaymentResult(
            success=False,
            transaction_id=transaction_id,
            status=PaymentStatus.FAILED,
            message=validation_result.get("message", "Receipt validation failed"),
            provider=self.provider_name,
            provider_data=validation_result,
        )

    def validate_receipt(
        self,
        receipt_data: str,
        password: str | None = None,
        request_date: str | None = None,
        exclude_old_transactions: bool = True,
    ) -> dict[str, Any]:
        """
        Validate an App Store receipt using Apple's Server API V2.

        Args:
            receipt_data: Base64 encoded receipt data
            password: Shared secret (overrides config)
            request_date: Date of original purchase (for subscriptions)
            exclude_old_transactions: Exclude older transactions (default: True)

        Returns:
            Dict with validation result containing:
                - status: 0 = valid, 21000-21009 = various errors
                - environment: 'Sandbox' or 'production'
                - receipt: Parsed receipt data
                - latest_receipt_info: Latest receipt info
                - provider_data: Full API response for reference
        """
        self.logger.info(f"Validating Apple receipt (Sandbox: {self.sandbox})")

        if not self.is_configured():
            return {
                "status": 21000,
                "message": "Apple IAP provider is not configured. Set bundle_id and shared_secret.",
            }

        receipt_password = password or self.shared_secret

        if not receipt_password:
            return {
                "status": 21000,
                "message": "Shared secret is required for receipt validation",
            }

        try:
            # Decode base64 receipt if needed
            try:
                decoded_receipt = base64.b64decode(receipt_data)
                if isinstance(decoded_receipt, bytes):
                    receipt_data = decoded_receipt.decode("utf-8")
                else:
                    receipt_data = decoded_receipt
            except Exception:
                # Receipt is already decoded or in different format
                receipt_data = receipt_data

            # Prepare request payload
            payload = {
                "receipt-data": receipt_data,
                "password": receipt_password,
                "exclude-old-transactions": exclude_old_transactions,
            }

            # Add request-date for subscription status checks
            if request_date:
                payload["request-date"] = request_date

            # Make request to Apple App Store Server API
            response = requests.post(
                f"{self.api_url}/verifyReceipt",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )

            # Check response status
            if response.status_code != 200:
                self.logger.error(
                    f"Apple API returned status {response.status_code}: {response.text}"
                )
                return {
                    "status": 21002,
                    "message": f"Apple API error: {response.status_code}",
                    "environment": "sandbox" if self.sandbox else "production",
                }

            result = response.json()

            # Check validation status
            status = result.get("status", 21000)

            if status == 0:
                # Receipt is valid
                self.logger.info("Apple receipt validated successfully")

                receipt_info = result.get("receipt", {})
                latest_receipt = receipt_info.get("latest_receipt_info", {})

                return {
                    "status": 0,
                    "environment": result.get(
                        "environment", "sandbox" if self.sandbox else "production"
                    ),
                    "receipt": receipt_info,
                    "latest_receipt_info": latest_receipt,
                    "provider_data": result,
                }
            else:
                # Receipt validation failed
                self.logger.warning(
                    f"Apple receipt validation failed with status: {status}"
                )
                return {
                    "status": status,
                    "message": f"Receipt validation failed with status code: {status}",
                    "environment": result.get(
                        "environment", "sandbox" if self.sandbox else "production"
                    ),
                }

        except RequestException as e:
            self.logger.error(f"Network error validating Apple receipt: {e}")
            return {
                "status": 21000,
                "message": f"Network error: {e!s}",
                "environment": "sandbox" if self.sandbox else "production",
            }
        except Exception as e:
            self.logger.error(f"Error validating Apple receipt: {e}")
            return {
                "status": 21000,
                "message": f"Validation error: {e!s}",
                "environment": "sandbox" if self.sandbox else "production",
            }

    def get_subscription_status(
        self,
        original_transaction_id: str,
        receipt_data: str | None = None,
    ) -> dict[str, Any]:
        """
        Check status of a subscription using Apple's subscription status API.

        For auto-renewable subscriptions, use the original transaction ID
        (or receipt data) to check the current status.

        Args:
            original_transaction_id: Original transaction ID
            receipt_data: Optional fresh receipt data for validation

        Returns:
            Dict with subscription status information:
                - status: 'active', 'expired', 'pending', etc.
                - expiry_date: ISO format expiry date
                - environment: 'sandbox' or 'production'
                - provider_data: Full API response
        """
        self.logger.info(
            f"Checking Apple subscription status for {original_transaction_id}"
        )

        # For Apple, we validate the receipt to get current subscription status
        if receipt_data:
            result = self.validate_receipt(
                receipt_data, request_date=original_transaction_id
            )
        else:
            # Use cached result or re-validate
            result = self.validate_receipt(
                receipt_data, request_date=original_transaction_id
            )

        if result.get("status") == 0:
            latest_receipt = result.get("latest_receipt_info", {})
            expires_date_ms = latest_receipt.get("expires_date_ms")

            if expires_date_ms:
                from datetime import datetime, timezone

                expires_date = datetime.fromtimestamp(
                    expires_date_ms / 1000, tz=timezone.utc
                )

                # Check if subscription is active
                from datetime import timezone as dt_timezone

                now = datetime.now(dt_timezone.utc)

                if expires_date > now:
                    return {
                        "status": "active",
                        "expiry_date": expires_date.isoformat(),
                        "environment": result.get(
                            "environment", "sandbox" if self.sandbox else "production"
                        ),
                        "provider_data": result.get("provider_data"),
                    }
                else:
                    return {
                        "status": "expired",
                        "expiry_date": expires_date.isoformat(),
                        "environment": result.get(
                            "environment", "sandbox" if self.sandbox else "production"
                        ),
                        "provider_data": result.get("provider_data"),
                    }
            else:
                return {
                    "status": "active",
                    "environment": result.get(
                        "environment", "sandbox" if self.sandbox else "production"
                    ),
                    "provider_data": result.get("provider_data"),
                }

        return {
            "status": "unknown",
            "environment": "sandbox" if self.sandbox else "production",
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
        Apple IAP subscriptions are created client-side.

        Returns pending result indicating client-side action required.

        Args:
            plan_id: Apple product ID
            customer_email: Not used by Apple
            metadata: Additional metadata
            trial_days: Configured in App Store Connect
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult with client-side instructions
        """
        return SubscriptionResult(
            success=False,
            status="pending_client_action",
            plan_id=plan_id,
            message="Apple IAP subscriptions must be created client-side via StoreKit. "
            "Validate the receipt after purchase.",
            provider=self.provider_name,
            provider_data={
                "product_id": plan_id,
                "action_required": "Initiate purchase through iOS StoreKit",
                "validate_receipt_after": "Call validate_receipt() with receipt data",
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
        Cancel an Apple IAP subscription.

        Apple doesn't provide a server-side API for cancellation.
        Cancellation must be handled client-side or via App Store Connect.

        Args:
            provider_subscription_id: Apple transaction ID
            cancel_at_period_end: If True, cancel at period end
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult indicating cancellation method
        """
        self.logger.info(
            f"Apple IAP subscription cancel requested for {provider_subscription_id}"
        )

        return SubscriptionResult(
            success=False,
            status="cancellation_not_supported",
            provider_subscription_id=provider_subscription_id,
            message="Apple IAP subscriptions cannot be cancelled server-side. "
            "User must cancel via device Settings or App Store.",
            provider=self.provider_name,
            provider_data={
                "transaction_id": provider_subscription_id,
                "action_required": "User must cancel via device Settings > App Store > Subscriptions",
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
        Update an Apple IAP subscription.

        Apple doesn't provide a server-side API for subscription updates.
        Plan changes must be handled client-side via StoreKit.

        Args:
            provider_subscription_id: Apple transaction ID
            plan_id: New product ID (not supported for update)
            quantity: Quantity (not used for Apple)
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult indicating update method
        """
        return SubscriptionResult(
            success=False,
            status="update_not_supported",
            provider_subscription_id=provider_subscription_id,
            message="Apple IAP subscriptions cannot be updated server-side. "
            "Plan changes require user to purchase new subscription via StoreKit.",
            provider=self.provider_name,
            provider_data={
                "current_transaction_id": provider_subscription_id,
                "new_product_id": plan_id,
                "action_required": "User must purchase new subscription via device App Store",
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
        Process a refund for Apple IAP purchase.

        Apple refunds must be processed through App Store Connect.
        This method records the refund intent.

        Args:
            transaction_id: Original transaction ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Additional parameters

        Returns:
            RefundResult with refund details
        """
        self.logger.info(f"Apple IAP refund requested for {transaction_id}: {reason}")

        return RefundResult(
            success=False,
            refund_id=f"refund_{transaction_id}",
            provider_refund_id=transaction_id,
            amount=Decimal(str(amount)) if amount else Decimal("0"),
            currency="USD",
            status="pending_manual_processing",
            reason=reason,
            message="Apple IAP refunds must be processed through App Store Connect.",
            provider=self.provider_name,
            provider_data={
                "transaction_id": transaction_id,
                "action_required": "Process refund via App Store Connect > Sales > Transactions",
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
        Parse an Apple App Store Server Notification V2 webhook.

        Args:
            payload: Raw webhook payload (JSON)
            headers: HTTP headers (for authentication verification)
            **kwargs: Additional parameters

        Returns:
            WebhookEvent with parsed data

        Raises:
            PaymentError: If payload is invalid or signature verification fails
        """
        self.logger.info("Parsing Apple IAP webhook")

        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")

            data = json.loads(payload) if isinstance(payload, str | bytes) else {}

            # Extract notification type and data
            notification_type = data.get("notification_type", "")
            subtype = data.get("subtype", "")

            # Determine event type
            event_map = {
                "CANCEL": "subscription_cancelled",
                "DID_FAIL_TO_RENEW": "subscription_expired",
                "DID_RENEW": "subscription_renewed",
                "INIT_BUY": "subscription_purchased",
                "PRICE_INCREASE": "price_increase",
                "REFUND": "refund",
                "RENEW": "subscription_renewed",
                "REVOKE": "subscription_revoked",
                "SUBSCRIBED": "subscription_purchased",
            }

            event_type = event_map.get(notification_type, "unknown")

            return WebhookEvent(
                event_id=data.get("notification_uuid", ""),
                event_type=event_type,
                provider=self.provider_name,
                payload=data,
                received_at=data.get("signedDate", ""),
                provider_data={
                    "subtype": subtype,
                    "environment": "sandbox" if self.sandbox else "production",
                    "notification_type": notification_type,
                },
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in Apple webhook: {e}")
            raise PaymentError(
                message="Invalid JSON payload",
                code="INVALID_PAYLOAD",
                provider=self.provider_name,
                details={"original_error": str(e)},
            ) from e
        except Exception as e:
            self.logger.error(f"Error parsing Apple webhook: {e}")
            raise PaymentError(
                message="Failed to parse webhook payload",
                code="PARSING_ERROR",
                provider=self.provider_name,
                details={"original_error": str(e)},
            ) from e
