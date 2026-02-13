# myapp/payment_strategies/providers/stripe.py
"""
Stripe payment provider implementation.

This module implements the PaymentProvider interface for Stripe,
supporting:
- Payment Intents API
- Subscriptions with trials
- Webhook signature verification
- Refunds
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import stripe
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


class StripePaymentProvider(PaymentProvider):
    """
    Stripe payment provider using the Payment Intents API.

    Configuration:
        - secret_key: Stripe secret key (sk_live_... or sk_test_...)
        - publishable_key: Stripe publishable key (pk_live_... or pk_test_...)
        - webhook_secret: Webhook signing secret for verification
        - api_version: Stripe API version to use
    """

    provider_name = "stripe"
    display_name = "Stripe"

    @staticmethod
    def _get_first_item_from_subscription(subscription_id: str) -> str:
        """Get the first item ID from a Stripe subscription."""
        subscription = stripe.Subscription.retrieve(subscription_id)
        return subscription["items"]["data"][0].id

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

        # Get configuration from Django settings if not provided
        if not self.config:
            self.config = {
                "secret_key": getattr(settings, "STRIPE_SECRET_KEY", ""),
                "publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
                "webhook_secret": getattr(settings, "STRIPE_WEBHOOK_SECRET", ""),
                "api_version": getattr(settings, "STRIPE_API_VERSION", "2023-10-16"),
                "enabled": getattr(settings, "STRIPE_ENABLED", False),
            }

        # Configure Stripe SDK
        secret_key = self.config.get("secret_key", "")
        if secret_key:
            stripe.api_key = secret_key
            stripe.api_version = self.config.get("api_version")

    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(self.config.get("secret_key") and self.config.get("enabled", False))

    def create_payment_intent(
        self,
        amount: Decimal | float,
        currency: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        customer_email: str | None = None,
        payment_method_types: list[str] | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Create a Stripe PaymentIntent.

        Args:
            amount: Payment amount in cents (e.g., $10.00 = 1000)
            currency: Currency code (lowercase, e.g., 'usd')
            description: Payment description
            metadata: Metadata to attach to the payment
            customer_email: Customer email for receipts
            payment_method_types: List of payment method types
            **kwargs: Additional Stripe parameters

        Returns:
            PaymentResult with payment intent details
        """
        if not self.is_configured():
            return PaymentResult(
                success=False,
                message="Stripe is not configured",
                error=PaymentError(
                    message="Stripe payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            # Convert amount to integer cents
            amount_cents = int(Decimal(str(amount)) * 100)

            # Prepare payment intent parameters
            intent_params = {
                "amount": amount_cents,
                "currency": currency.lower(),
                "metadata": metadata or {},
                "automatic_payment_methods": {
                    "enabled": True,
                },
            }

            if description:
                intent_params["description"] = description

            if customer_email:
                # Create or get Stripe customer
                customer = self._get_or_create_customer(customer_email)
                intent_params["customer"] = customer.id

            # Add any additional parameters
            intent_params.update(kwargs)

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(**intent_params)

            return PaymentResult(
                success=True,
                transaction_id=payment_intent.id,
                provider_transaction_id=payment_intent.id,
                amount=Decimal(str(amount)),
                currency=currency.upper(),
                status=self._map_stripe_status(payment_intent.status),
                message="Payment intent created",
                provider=self.provider_name,
                client_secret=payment_intent.client_secret,
                provider_data={
                    "created": payment_intent.created,
                    "livemode": payment_intent.livemode,
                },
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment intent creation failed: {e}")
            return PaymentResult(
                success=False,
                message="Failed to create payment intent",
                error=PaymentError(
                    message=str(e),
                    code=e.error.get("code", "STRIPE_ERROR")
                    if hasattr(e, "error")
                    else "STRIPE_ERROR",
                    provider=self.provider_name,
                    details=getattr(e, "error", {}),
                ),
            )

    def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Confirm a Stripe PaymentIntent.

        Args:
            payment_intent_id: PaymentIntent ID
            payment_method_id: PaymentMethod ID to attach
            **kwargs: Additional parameters

        Returns:
            PaymentResult with updated status
        """
        if not self.is_configured():
            return PaymentResult(
                success=False,
                message="Stripe is not configured",
                error=PaymentError(
                    message="Stripe payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if payment_method_id:
                # Attach payment method to intent
                payment_intent = stripe.PaymentIntent.modify(
                    payment_intent_id,
                    payment_method=payment_method_id,
                )

            # Confirm the payment intent
            if payment_intent.status in [
                "requires_payment_method",
                "requires_confirmation",
            ]:
                payment_intent = stripe.PaymentIntent.confirm(payment_intent_id)

            return PaymentResult(
                success=payment_intent.status in ["succeeded", "processing"],
                transaction_id=payment_intent.id,
                provider_transaction_id=payment_intent.id,
                amount=Decimal(str(payment_intent.amount / 100)),
                currency=payment_intent.currency.upper(),
                status=self._map_stripe_status(payment_intent.status),
                message=f"Payment {payment_intent.status}",
                provider=self.provider_name,
                provider_data={
                    "status": payment_intent.status,
                    "created": payment_intent.created,
                },
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment confirmation failed: {e}")
            return PaymentResult(
                success=False,
                message="Failed to confirm payment",
                error=PaymentError(
                    message=str(e),
                    code=e.error.get("code", "STRIPE_ERROR")
                    if hasattr(e, "error")
                    else "STRIPE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def get_payment_status(
        self,
        transaction_id: str,
        **kwargs: Any,
    ) -> PaymentResult:
        """Get the current status of a Stripe PaymentIntent."""
        if not self.is_configured():
            return PaymentResult(
                success=False,
                message="Stripe is not configured",
                error=PaymentError(
                    message="Stripe payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            payment_intent = stripe.PaymentIntent.retrieve(transaction_id)

            return PaymentResult(
                success=True,
                transaction_id=payment_intent.id,
                provider_transaction_id=payment_intent.id,
                amount=Decimal(str(payment_intent.amount / 100)),
                currency=payment_intent.currency.upper(),
                status=self._map_stripe_status(payment_intent.status),
                message=f"Payment status: {payment_intent.status}",
                provider=self.provider_name,
                provider_data={
                    "status": payment_intent.status,
                    "amount_received": payment_intent.amount_received,
                },
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe status check failed: {e}")
            return PaymentResult(
                success=False,
                message="Failed to get payment status",
                error=PaymentError(
                    message=str(e),
                    code=e.error.get("code", "STRIPE_ERROR")
                    if hasattr(e, "error")
                    else "STRIPE_ERROR",
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
        Create a Stripe subscription.

        Args:
            plan_id: Stripe Price ID (price_xxx)
            customer_email: Customer email
            metadata: Additional metadata
            trial_days: Trial period days
            **kwargs: Additional parameters (quantity, payment_method, etc.)

        Returns:
            SubscriptionResult with subscription details
        """
        if not self.is_configured():
            return SubscriptionResult(
                success=False,
                message="Stripe is not configured",
                error=PaymentError(
                    message="Stripe payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            # Get or create customer
            customer = None
            if customer_email:
                customer = self._get_or_create_customer(customer_email)

            # Prepare subscription parameters
            subscription_params = {
                "items": [{"price": plan_id}],
                "metadata": metadata or {},
            }

            if customer:
                subscription_params["customer"] = customer.id

            if trial_days > 0:
                subscription_params["trial_period_days"] = trial_days

            # Add any additional parameters
            subscription_params.update(kwargs)

            subscription = stripe.Subscription.create(**subscription_params)

            return SubscriptionResult(
                success=True,
                provider_subscription_id=subscription.id,
                status=subscription.status,
                message="Subscription created successfully",
                provider=self.provider_name,
                provider_data={
                    "current_period_end": subscription.current_period_end,
                    "cancel_at_period_end": subscription.cancel_at_period_end,
                },
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            return SubscriptionResult(
                success=False,
                message="Failed to create subscription",
                error=PaymentError(
                    message=str(e),
                    code=e.error.get("code", "STRIPE_ERROR")
                    if hasattr(e, "error")
                    else "STRIPE_ERROR",
                    provider=self.provider_name,
                ),
            )

    def cancel_subscription(
        self,
        provider_subscription_id: str,
        cancel_at_period_end: bool = True,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """Cancel a Stripe subscription."""
        if not self.is_configured():
            return SubscriptionResult(
                success=False,
                message="Stripe is not configured",
                error=PaymentError(
                    message="Stripe payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            if cancel_at_period_end:
                # Cancel at period end
                subscription = stripe.Subscription.modify(
                    provider_subscription_id,
                    cancel_at_period_end=True,
                )
                message = "Subscription will be canceled at period end"
            else:
                # Cancel immediately
                subscription = stripe.Subscription.delete(provider_subscription_id)
                message = "Subscription canceled immediately"

            return SubscriptionResult(
                success=True,
                provider_subscription_id=subscription.id,
                status=subscription.status,
                message=message,
                provider=self.provider_name,
                provider_data={
                    "canceled_at": subscription.canceled_at,
                },
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            return SubscriptionResult(
                success=False,
                message="Failed to cancel subscription",
                error=PaymentError(
                    message=str(e),
                    code=e.error.get("code", "STRIPE_ERROR")
                    if hasattr(e, "error")
                    else "STRIPE_ERROR",
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
        """Update a Stripe subscription."""
        if not self.is_configured():
            return SubscriptionResult(
                success=False,
                message="Stripe is not configured",
                error=PaymentError(
                    message="Stripe payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            update_params = {}

            if plan_id:
                update_params["items"] = [
                    {
                        "id": self._get_first_item_from_subscription(
                            provider_subscription_id
                        ),
                        "price": plan_id,
                    }
                ]

            if quantity is not None:
                update_params["items"] = update_params.get("items", [])
                if update_params["items"]:
                    update_params["items"][0]["quantity"] = quantity

            update_params.update(kwargs)

            subscription = stripe.Subscription.modify(
                provider_subscription_id, **update_params
            )

            return SubscriptionResult(
                success=True,
                provider_subscription_id=subscription.id,
                status=subscription.status,
                message="Subscription updated successfully",
                provider=self.provider_name,
                provider_data={
                    "current_period_end": subscription.current_period_end,
                },
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription update failed: {e}")
            return SubscriptionResult(
                success=False,
                message="Failed to update subscription",
                error=PaymentError(
                    message=str(e),
                    code=e.error.get("code", "STRIPE_ERROR")
                    if hasattr(e, "error")
                    else "STRIPE_ERROR",
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
        Refund a Stripe payment.

        Args:
            transaction_id: PaymentIntent ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Additional parameters

        Returns:
            RefundResult with refund details
        """
        if not self.is_configured():
            return RefundResult(
                success=False,
                message="Stripe is not configured",
                error=PaymentError(
                    message="Stripe payment service is not available",
                    code="PROVIDER_NOT_CONFIGURED",
                    provider=self.provider_name,
                ),
            )

        try:
            refund_params = {
                "payment_intent": transaction_id,
                "reason": reason or "requested_by_customer",
            }

            if amount is not None:
                refund_params["amount"] = int(Decimal(str(amount)) * 100)

            refund = stripe.Refund.create(**refund_params)

            return RefundResult(
                success=refund.status in ["succeeded", "pending"],
                refund_id=refund.id,
                provider_refund_id=refund.id,
                amount=Decimal(str(refund.amount / 100)),
                currency=refund.currency.upper(),
                status=refund.status,
                reason=refund.reason or reason,
                message="Refund created successfully"
                if refund.status != "failed"
                else "Refund failed",
                provider=self.provider_name,
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund failed: {e}")
            return RefundResult(
                success=False,
                message="Failed to create refund",
                error=PaymentError(
                    message=str(e),
                    code=e.error.get("code", "STRIPE_ERROR")
                    if hasattr(e, "error")
                    else "STRIPE_ERROR",
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
        Parse and verify a Stripe webhook event.

        Args:
            payload: Raw webhook payload
            headers: HTTP headers including Stripe-Signature
            **kwargs: Additional parameters

        Returns:
            WebhookEvent with parsed data

        Raises:
            PaymentError: If signature verification fails
        """
        if not self.is_configured():
            raise PaymentError(
                message="Stripe is not configured",
                code="PROVIDER_NOT_CONFIGURED",
                provider=self.provider_name,
            )

        sig_header = headers.get("stripe-signature", "") if headers else ""
        webhook_secret = self.config.get("webhook_secret", "")

        if not webhook_secret:
            raise PaymentError(
                message="Webhook secret not configured",
                code="WEBHOOK_SECRET_MISSING",
                provider=self.provider_name,
            )

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

            return WebhookEvent(
                event_id=event.id,
                event_type=event.type,
                provider=self.provider_name,
                payload={"data": event.data, "type": event.type},
                received_at=datetime.now(timezone.utc),
            )

        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Stripe webhook signature verification failed: {e}")
            raise PaymentError(
                message="Invalid webhook signature",
                code="WEBHOOK_SIGNATURE_INVALID",
                provider=self.provider_name,
                details={"original_error": str(e)},
            ) from e

    # ==========================================================================
    # PRIVATE HELPER METHODS
    # ==========================================================================

    def _get_or_create_customer(
        self, email: str, name: str | None = None
    ) -> stripe.Customer:
        """Get existing or create new Stripe customer."""
        # Search for existing customer by email
        customers = stripe.Customer.list(email=email, limit=1)

        if customers.data:
            return customers.data[0]

        # Create new customer
        customer_params = {"email": email}
        if name:
            customer_params["name"] = name

        return stripe.Customer.create(**customer_params)

    @staticmethod
    def _map_stripe_status(stripe_status: str) -> PaymentStatus:
        """Map Stripe status to PaymentStatus enum."""
        status_map = {
            "succeeded": PaymentStatus.COMPLETED,
            "processing": PaymentStatus.PROCESSING,
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.PENDING,
            "canceled": PaymentStatus.CANCELLED,
        }
        return status_map.get(stripe_status, PaymentStatus.PENDING)
