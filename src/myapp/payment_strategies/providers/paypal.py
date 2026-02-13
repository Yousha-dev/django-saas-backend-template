# myapp/payment_strategies/providers/paypal.py
"""
PayPal payment provider implementation.

This module implements the PaymentProvider interface for PayPal,
supporting:
- PayPal Orders API for one-time payments
- PayPal Subscriptions API for recurring payments
- Webhook signature verification
- Refunds
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings

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


class PayPalPaymentProvider(PaymentProvider):
    """
    PayPal payment provider using the Orders API and Subscriptions API.

    Configuration:
        - client_id: PayPal REST API client ID
        - client_secret: PayPal REST API client secret
        - webhook_id: PayPal webhook ID for signature verification
        - mode: 'sandbox' or 'live'
        - base_url: API base URL (auto-configured based on mode)
    """

    provider_name = "paypal"
    display_name = "PayPal"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

        # Get configuration from Django settings if not provided
        if not self.config:
            self.config = {
                "client_id": getattr(settings, "PAYPAL_CLIENT_ID", ""),
                "client_secret": getattr(settings, "PAYPAL_CLIENT_SECRET", ""),
                "webhook_id": getattr(settings, "PAYPAL_WEBHOOK_ID", ""),
                "mode": getattr(settings, "PAYPAL_MODE", "sandbox"),
            }

        # Configure base URL based on mode
        mode = self.config.get("mode", "sandbox")
        if mode == "live":
            self.base_url = "https://api-m.paypal.com"
        else:
            self.base_url = "https://api-m.sandbox.paypal.com"

        self._access_token = None
        self._token_expires = None

    def is_configured(self) -> bool:
        """Check if PayPal is properly configured."""
        return bool(self.config.get("client_id") and self.config.get("client_secret"))

    def _get_access_token(self) -> str:
        """Get or refresh PayPal API access token."""
        # Return cached token if still valid
        if (
            self._access_token
            and self._token_expires
            and datetime.now(timezone.utc) < self._token_expires
        ):
            return self._access_token

        # Get new token
        auth = (self.config["client_id"], self.config["client_secret"])
        response = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            auth=auth,
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(f"PayPal auth failed: {response.text}")
            raise PaymentError(
                message="Failed to authenticate with PayPal",
                code="PAYPAL_AUTH_FAILED",
                provider=self.provider_name,
            )

        data = response.json()
        self._access_token = data["access_token"]
        # Set expiration with buffer
        expires_in = data.get("expires_in", 3600)
        self._token_expires = datetime.now(timezone.utc).replace(
            second=0, microsecond=0
        ) + timezone.timedelta(seconds=expires_in - 60)

        return self._access_token

    def create_payment_intent(
        self,
        amount: Decimal | float,
        currency: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        customer_email: str | None = None,
        return_url: str | None = None,
        cancel_url: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Create a PayPal Order (equivalent to payment intent).

        Args:
            amount: Payment amount
            currency: Currency code
            description: Order description
            metadata: Additional metadata
            customer_email: Customer email
            return_url: URL for successful payment
            cancel_url: URL for cancelled payment
            **kwargs: Additional parameters

        Returns:
            PaymentResult with order details and approval URL
        """
        if not self.is_configured():
            return PaymentResult(
                success=False,
                message="PayPal is not configured",
                error=PaymentError(
                    message="PayPal payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            token = self._get_access_token()

            # Default URLs if not provided
            if not return_url:
                return_url = self.config.get("default_return_url", "")
            if not cancel_url:
                cancel_url = self.config.get("default_cancel_url", "")

            order_data = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": currency.upper(),
                            "value": str(amount),
                        },
                        "description": description or "Payment",
                    }
                ],
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                },
            }

            # Add custom metadata
            if metadata:
                # PayPal allows custom_id (up to 64 chars)
                custom_value = json.dumps(metadata)
                order_data["purchase_units"][0]["custom_id"] = custom_value[:64]

            response = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json=order_data,
                timeout=30,
            )

            if response.status_code != 201:
                logger.error(f"PayPal order creation failed: {response.text}")
                return PaymentResult(
                    success=False,
                    message="Failed to create PayPal order",
                    error=PaymentError(
                        message=response.text,
                        code="PAYPAL_ORDER_FAILED",
                        provider=self.provider_name,
                    ),
                )

            order = response.json()

            # Extract approval link
            approval_url = None
            for link in order.get("links", []):
                if link.get("rel") == "approve":
                    approval_url = link.get("href")
                    break

            return PaymentResult(
                success=True,
                transaction_id=order["id"],
                provider_transaction_id=order["id"],
                amount=Decimal(amount),
                currency=currency.upper(),
                status=PaymentStatus.PENDING,
                message="PayPal order created",
                provider=self.provider_name,
                redirect_url=approval_url,
                provider_data={
                    "status": order["status"],
                    "create_time": order.get("create_time"),
                },
            )

        except requests.RequestException as e:
            logger.error(f"PayPal API request failed: {e}")
            return PaymentResult(
                success=False,
                message="PayPal service unavailable",
                error=PaymentError(
                    message=str(e),
                    code="PAYPAL_SERVICE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str | None = None,
        payer_id: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Capture a PayPal payment (after user approval).

        Args:
            payment_intent_id: PayPal Order ID
            payment_method_id: Not used for PayPal
            payer_id: PayPal Payer-ID from approval
            **kwargs: Additional parameters

        Returns:
            PaymentResult with capture status
        """
        if not self.is_configured():
            return PaymentResult(
                success=False,
                message="PayPal is not configured",
                error=PaymentError(
                    message="PayPal payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            token = self._get_access_token()

            # Capture payment for the order
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders/{payment_intent_id}/capture",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=30,
            )

            if response.status_code not in (200, 201):
                logger.error(f"PayPal capture failed: {response.text}")
                return PaymentResult(
                    success=False,
                    message="Failed to capture PayPal payment",
                    error=PaymentError(
                        message=response.text,
                        code="PAYPAL_CAPTURE_FAILED",
                        provider=self.provider_name,
                    ),
                )

            data = response.json()
            purchase_unit = data.get("purchase_units", [{}])[0]
            payment_capture = purchase_unit.get("payments", {}).get("captures", [{}])[0]

            return PaymentResult(
                success=data["status"] == "COMPLETED",
                transaction_id=data["id"],
                provider_transaction_id=payment_capture.get("id"),
                amount=Decimal(payment_capture.get("amount", {}).get("value", "0")),
                currency=payment_capture.get("amount", {}).get("currency", "USD"),
                status=PaymentStatus.COMPLETED
                if data["status"] == "COMPLETED"
                else PaymentStatus.PROCESSING,
                message=f"Payment {data['status']}",
                provider=self.provider_name,
                provider_data={
                    "status": data["status"],
                    "create_time": data.get("create_time"),
                },
            )

        except requests.RequestException as e:
            logger.error(f"PayPal capture request failed: {e}")
            return PaymentResult(
                success=False,
                message="PayPal service unavailable",
                error=PaymentError(
                    message=str(e),
                    code="PAYPAL_SERVICE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def get_payment_status(
        self,
        transaction_id: str,
        **kwargs: Any,
    ) -> PaymentResult:
        """Get the current status of a PayPal Order."""
        if not self.is_configured():
            return PaymentResult(
                success=False,
                message="PayPal is not configured",
                error=PaymentError(
                    message="PayPal payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            token = self._get_access_token()

            response = requests.get(
                f"{self.base_url}/v2/checkout/orders/{transaction_id}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=30,
            )

            if response.status_code != 200:
                return PaymentResult(
                    success=False,
                    message="Failed to get order status",
                    error=PaymentError(
                        message=response.text,
                        code="PAYPAL_STATUS_FAILED",
                        provider=self.provider_name,
                    ),
                )

            order = response.json()
            status_map = {
                "CREATED": PaymentStatus.PENDING,
                "APPROVED": PaymentStatus.PROCESSING,
                "COMPLETED": PaymentStatus.COMPLETED,
                "SAVED": PaymentStatus.PENDING,
                "VOIDED": PaymentStatus.CANCELLED,
            }

            purchase_unit = order.get("purchase_units", [{}])[0]
            amount_info = purchase_unit.get("amount", {})

            return PaymentResult(
                success=True,
                transaction_id=order["id"],
                provider_transaction_id=order["id"],
                amount=Decimal(amount_info.get("value", "0")),
                currency=amount_info.get("currency", "USD"),
                status=status_map.get(order["status"], PaymentStatus.PENDING),
                message=f"Order status: {order['status']}",
                provider=self.provider_name,
                provider_data={
                    "status": order["status"],
                    "create_time": order.get("create_time"),
                },
            )

        except requests.RequestException as e:
            logger.error(f"PayPal status check failed: {e}")
            return PaymentResult(
                success=False,
                message="PayPal service unavailable",
                error=PaymentError(
                    message=str(e),
                    code="PAYPAL_SERVICE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def create_subscription(
        self,
        plan_id: str,
        customer_email: str | None = None,
        metadata: dict[str, Any] | None = None,
        trial_days: int = 0,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Create a PayPal subscription.

        Note: PayPal requires a pre-configured Plan ID and Product ID.
        The plan_id parameter should be the PayPal Plan ID.

        Args:
            plan_id: PayPal Plan ID
            customer_email: Customer email
            metadata: Additional metadata
            trial_days: Trial period (must be configured in plan)
            **kwargs: Additional parameters (shipping_address, etc.)

        Returns:
            SubscriptionResult with subscription details
        """
        if not self.is_configured():
            return SubscriptionResult(
                success=False,
                message="PayPal is not configured",
                error=PaymentError(
                    message="PayPal payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            token = self._get_access_token()

            # Create subscription
            subscription_data = {
                "plan_id": plan_id,
                "application_context": kwargs.get(
                    "application_context",
                    {
                        "brand_name": "Template",
                        "user_action": "SUBSCRIBE_NOW",
                        "payment_method": {
                            "payer_selected": "PAYPAL",
                            "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED",
                        },
                        "return_url": kwargs.get("return_url", ""),
                        "cancel_url": kwargs.get("cancel_url", ""),
                    },
                ),
            }

            # Add custom metadata
            if metadata:
                # PayPal allows custom_id
                custom_value = json.dumps(metadata)
                subscription_data["custom_id"] = custom_value[:64]

            response = requests.post(
                f"{self.base_url}/v1/billing/subscriptions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json=subscription_data,
                timeout=30,
            )

            if response.status_code not in (201, 200):
                logger.error(f"PayPal subscription creation failed: {response.text}")
                return SubscriptionResult(
                    success=False,
                    message="Failed to create PayPal subscription",
                    error=PaymentError(
                        message=response.text,
                        code="PAYPAL_SUBSCRIPTION_FAILED",
                        provider=self.provider_name,
                    ),
                )

            subscription = response.json()

            # Extract approval link
            approval_url = None
            for link in subscription.get("links", []):
                if link.get("rel") == "approve":
                    approval_url = link.get("href")
                    break

            return SubscriptionResult(
                success=True,
                provider_subscription_id=subscription["id"],
                status=subscription["status"],
                message="PayPal subscription created",
                provider=self.provider_name,
                provider_data={
                    "status": subscription["status"],
                    "create_time": subscription.get("create_time"),
                    "approval_url": approval_url,
                },
            )

        except requests.RequestException as e:
            logger.error(f"PayPal subscription request failed: {e}")
            return SubscriptionResult(
                success=False,
                message="PayPal service unavailable",
                error=PaymentError(
                    message=str(e),
                    code="PAYPAL_SERVICE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def cancel_subscription(
        self,
        provider_subscription_id: str,
        cancel_at_period_end: bool = True,
        reason: str = "User requested cancellation",
        **kwargs: Any,
    ) -> SubscriptionResult:
        """Cancel a PayPal subscription."""
        if not self.is_configured():
            return SubscriptionResult(
                success=False,
                message="PayPal is not configured",
                error=PaymentError(
                    message="PayPal payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            token = self._get_access_token()

            # For PayPal, we need to cancel (not deactivate)
            response = requests.post(
                f"{self.base_url}/v1/billing/subscriptions/{provider_subscription_id}/cancel",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={"reason": reason},
                timeout=30,
            )

            if response.status_code != 204:
                logger.error(
                    f"PayPal subscription cancellation failed: {response.text}"
                )
                return SubscriptionResult(
                    success=False,
                    message="Failed to cancel PayPal subscription",
                    error=PaymentError(
                        message=response.text,
                        code="PAYPAL_CANCEL_FAILED",
                        provider=self.provider_name,
                    ),
                )

            return SubscriptionResult(
                success=True,
                provider_subscription_id=provider_subscription_id,
                status="CANCELLED",
                message="PayPal subscription cancelled",
                provider=self.provider_name,
            )

        except requests.RequestException as e:
            logger.error(f"PayPal cancellation request failed: {e}")
            return SubscriptionResult(
                success=False,
                message="PayPal service unavailable",
                error=PaymentError(
                    message=str(e),
                    code="PAYPAL_SERVICE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def update_subscription(
        self,
        provider_subscription_id: str,
        plan_id: str | None = None,
        quantity: int | None = None,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Update a PayPal subscription.

        Note: PayPal doesn't allow direct plan changes. You would need to
        create a new subscription and cancel the old one.
        """
        if not self.is_configured():
            return SubscriptionResult(
                success=False,
                message="PayPal is not configured",
                error=PaymentError(
                    message="PayPal payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        # PayPal doesn't support direct plan updates
        # Return with guidance
        return SubscriptionResult(
            success=False,
            message="PayPal doesn't support direct plan changes. "
            "Create a new subscription and cancel the old one.",
            error=PaymentError(
                message="Plan changes require subscription replacement",
                code="PAYPAL_PLAN_CHANGE_NOT_SUPPORTED",
                provider=self.provider_name,
            ),
        )

    def refund_payment(
        self,
        transaction_id: str,
        amount: Decimal | float | None = None,
        reason: str = "",
        **kwargs: Any,
    ) -> RefundResult:
        """
        Refund a PayPal payment.

        Args:
            transaction_id: PayPal Capture ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Additional parameters

        Returns:
            RefundResult with refund details
        """
        if not self.is_configured():
            return RefundResult(
                success=False,
                message="PayPal is not configured",
                error=PaymentError(
                    message="PayPal payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            token = self._get_access_token()

            refund_data = {
                "amount": {
                    "value": str(amount),
                    "currency_code": "USD",  # Should be derived from original payment
                }
                if amount
                else None,
                "note": reason or "Refund",
            }

            # Remove None values
            refund_data = {k: v for k, v in refund_data.items() if v is not None}

            response = requests.post(
                f"{self.base_url}/v2/payments/captures/{transaction_id}/refund",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json=refund_data,
                timeout=30,
            )

            if response.status_code not in (200, 201):
                logger.error(f"PayPal refund failed: {response.text}")
                return RefundResult(
                    success=False,
                    message="Failed to create PayPal refund",
                    error=PaymentError(
                        message=response.text,
                        code="PAYPAL_REFUND_FAILED",
                        provider=self.provider_name,
                    ),
                )

            refund = response.json()

            return RefundResult(
                success=refund["status"] in ["COMPLETED", "PENDING"],
                refund_id=refund["id"],
                provider_refund_id=refund["id"],
                amount=Decimal(refund.get("amount", {}).get("value", "0")),
                currency=refund.get("amount", {}).get("currency", "USD"),
                status=refund["status"],
                reason=reason,
                message="Refund created successfully",
                provider=self.provider_name,
            )

        except requests.RequestException as e:
            logger.error(f"PayPal refund request failed: {e}")
            return RefundResult(
                success=False,
                message="PayPal service unavailable",
                error=PaymentError(
                    message=str(e),
                    code="PAYPAL_SERVICE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def parse_webhook(
        self,
        payload: bytes | str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> WebhookEvent:
        """
        Parse and verify a PayPal webhook event.

        PayPal webhooks use HMAC signature verification.

        Args:
            payload: Raw webhook payload (string or bytes)
            headers: HTTP headers including PayPal-Auth-Algo, PayPal-Transmission-ID, etc.
            **kwargs: Additional parameters

        Returns:
            WebhookEvent with parsed data

        Raises:
            PaymentError: If signature verification fails
        """
        webhook_id = self.config.get("webhook_id")
        if not webhook_id:
            # Skip verification if webhook ID not configured (development)
            try:
                data = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                data = {}

            return WebhookEvent(
                event_id=data.get("id", ""),
                event_type=data.get("event_type", ""),
                provider=self.provider_name,
                payload=data,
                received_at=datetime.now(timezone.utc),
            )

        if not headers:
            raise PaymentError(
                message="Missing headers for webhook verification",
                code="WEBHOOK_HEADERS_MISSING",
                provider=self.provider_name,
            )

        # Extract PayPal verification headers
        auth_algo = headers.get("paypal-auth-algo", "")
        cert_id = headers.get("paypal-cert-id", "")
        transmission_id = headers.get("paypal-transmission-id", "")
        transmission_sig = headers.get("paypal-transmission-sig", "")
        transmission_time = headers.get("paypal-transmission-time", "")

        if not all(
            [auth_algo, cert_id, transmission_id, transmission_sig, transmission_time]
        ):
            raise PaymentError(
                message="Missing required PayPal webhook headers",
                code="WEBHOOK_HEADERS_INCOMPLETE",
                provider=self.provider_name,
            )

        # Prepare verification payload
        verification_payload = {
            "auth_algo": auth_algo,
            "cert_id": cert_id,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": webhook_id,
            "webhook_event": payload
            if isinstance(payload, str)
            else payload.decode("utf-8"),
        }

        # Verify with PayPal
        try:
            token = self._get_access_token()

            verify_response = requests.post(
                f"{self.base_url}/v1/notifications/verify-webhook-signature",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json=verification_payload,
                timeout=30,
            )

            if verify_response.status_code != 200:
                logger.error(
                    f"PayPal webhook verification failed: {verify_response.text}"
                )
                raise PaymentError(
                    message="Webhook signature verification failed",
                    code="WEBHOOK_SIGNATURE_INVALID",
                    provider=self.provider_name,
                )

            verification_result = verify_response.json()
            if verification_result.get("verification_status") != "SUCCESS":
                raise PaymentError(
                    message="Webhook signature verification failed",
                    code="WEBHOOK_SIGNATURE_INVALID",
                    provider=self.provider_name,
                )

            # Parse the actual event payload
            try:
                event_data = (
                    json.loads(payload)
                    if isinstance(payload, str)
                    else json.loads(payload.decode("utf-8"))
                )
            except json.JSONDecodeError:
                event_data = {}

            return WebhookEvent(
                event_id=transmission_id,
                event_type=event_data.get("event_type", ""),
                provider=self.provider_name,
                payload=event_data,
                received_at=datetime.now(timezone.utc),
            )

        except requests.RequestException as e:
            logger.error(f"PayPal webhook verification request failed: {e}")
            raise PaymentError(
                message="Failed to verify webhook with PayPal",
                code="WEBHOOK_VERIFICATION_ERROR",
                provider=self.provider_name,
                details={"original_error": str(e)},
            ) from e
