# myapp/payment_strategies/factory.py
"""
Payment provider factory and manager.

This module provides the factory pattern for creating payment provider
instances and a manager class for unified payment operations.
"""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.utils import timezone

from .base import PaymentError, PaymentProvider, PaymentResult
from .providers.apple_iap import AppleIAPProvider
from .providers.bank_transfer import BankTransferPaymentProvider
from .providers.google_play import GooglePlayProvider
from .providers.paypal import PayPalPaymentProvider
from .providers.stripe import StripePaymentProvider

logger = logging.getLogger(__name__)


# Provider registry - maps provider names to their classes
PROVIDER_REGISTRY: dict[str, type[PaymentProvider]] = {
    "stripe": StripePaymentProvider,
    "paypal": PayPalPaymentProvider,
    "bank_transfer": BankTransferPaymentProvider,
    "apple_iap": AppleIAPProvider,
    "google_play": GooglePlayProvider,
}


class PaymentProviderFactory:
    """
    Factory for creating payment provider instances.

    The factory handles provider registration and instantiation
    with proper configuration.

    Usage:
        stripe = PaymentProviderFactory.create('stripe')
        paypal = PaymentProviderFactory.create('paypal')
    """

    @classmethod
    def create(
        cls, provider_name: str, config: dict[str, Any] | None = None
    ) -> PaymentProvider:
        """
        Create a payment provider instance.

        Args:
            provider_name: Name of the provider (stripe, paypal, bank_transfer)
            config: Optional configuration (uses Django settings if not provided)

        Returns:
            PaymentProvider instance

        Raises:
            PaymentError: If provider is not found or not configured
        """
        provider_class = PROVIDER_REGISTRY.get(provider_name.lower())

        if not provider_class:
            available = ", ".join(PROVIDER_REGISTRY.keys())
            raise PaymentError(
                message=f"Unknown payment provider: {provider_name}. "
                f"Available providers: {available}",
                code="PROVIDER_NOT_FOUND",
                provider="factory",
            )

        provider = provider_class(config)

        if not provider.is_configured():
            logger.warning(
                f"Payment provider {provider_name} is not properly configured"
            )

        return provider

    @classmethod
    def register_provider(
        cls, name: str, provider_class: type[PaymentProvider]
    ) -> None:
        """
        Register a new payment provider.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from PaymentProvider)
        """
        if not issubclass(provider_class, PaymentProvider):
            raise ValueError(f"{provider_class} must inherit from PaymentProvider")

        PROVIDER_REGISTRY[name.lower()] = provider_class

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(PROVIDER_REGISTRY.keys())

    @classmethod
    def get_configured_providers(cls) -> list[str]:
        """Get list of providers that are properly configured."""
        configured = []
        for name in PROVIDER_REGISTRY:
            try:
                provider = cls.create(name)
                if provider.is_configured():
                    configured.append(name)
            except Exception:  # noqa: S110
                pass
        return configured


class PaymentManager:
    """
    High-level manager for payment operations.

    This class provides a unified interface for payment operations,
    automatically selecting the appropriate provider based on configuration
    and preferences.

    Features:
    - Automatic provider selection based on user preference or system default
    - Fallback to alternative providers if primary fails
    - Consistent error handling across providers
    - Integration with existing subscription models
    """

    def __init__(self, preferred_provider: str | None = None):
        """
        Initialize the payment manager.

        Args:
            preferred_provider: Default provider to use (from settings if None)
        """
        if preferred_provider is None:
            preferred_provider = getattr(settings, "DEFAULT_PAYMENT_PROVIDER", "stripe")

        self.preferred_provider = preferred_provider
        self._providers: dict[str, PaymentProvider] = {}

    def _get_provider(self, provider_name: str | None = None) -> PaymentProvider:
        """Get or create a provider instance."""
        if provider_name is None:
            provider_name = self.preferred_provider

        if provider_name not in self._providers:
            self._providers[provider_name] = PaymentProviderFactory.create(
                provider_name
            )

        return self._providers[provider_name]

    # ==========================================================================
    # PAYMENT INTENT OPERATIONS
    # ==========================================================================

    def create_payment_intent(
        self,
        amount: Decimal | float,
        currency: str = "USD",
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        customer_email: str | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Create a payment intent using the specified or preferred provider.

        Args:
            amount: Payment amount
            currency: Currency code
            description: Payment description
            metadata: Additional metadata
            customer_email: Customer email
            provider: Provider to use (uses preferred if None)
            **kwargs: Provider-specific parameters

        Returns:
            PaymentResult with transaction details
        """
        payment_provider = self._get_provider(provider)
        return payment_provider.create_payment_intent(
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata,
            customer_email=customer_email,
            **kwargs,
        )

    def confirm_payment(
        self,
        transaction_id: str,
        payment_method_id: str | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Confirm a payment intent.

        Args:
            transaction_id: Transaction ID
            payment_method_id: Payment method to charge
            provider: Provider to use (auto-detected if None)
            **kwargs: Provider-specific parameters

        Returns:
            PaymentResult with updated status
        """
        # Auto-detect provider from transaction ID if not specified
        if provider is None:
            provider = self._detect_provider_from_transaction(transaction_id)

        payment_provider = self._get_provider(provider)
        return payment_provider.confirm_payment(
            payment_intent_id=transaction_id,
            payment_method_id=payment_method_id,
            **kwargs,
        )

    def get_payment_status(
        self,
        transaction_id: str,
        provider: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """Get the current status of a payment."""
        if provider is None:
            provider = self._detect_provider_from_transaction(transaction_id)

        payment_provider = self._get_provider(provider)
        return payment_provider.get_payment_status(transaction_id, **kwargs)

    def refund_payment(
        self,
        transaction_id: str,
        amount: Decimal | float | None = None,
        reason: str = "",
        provider: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Refund a payment.

        Args:
            transaction_id: Transaction to refund
            amount: Refund amount (None for full refund)
            reason: Refund reason
            provider: Provider to use (auto-detected if None)
            **kwargs: Provider-specific parameters

        Returns:
            RefundResult with refund details
        """
        if provider is None:
            provider = self._detect_provider_from_transaction(transaction_id)

        payment_provider = self._get_provider(provider)

        # Import RefundResult here to avoid circular imports
        refund_result = payment_provider.refund_payment(
            transaction_id=transaction_id,
            amount=amount,
            reason=reason,
            **kwargs,
        )

        return PaymentResult(
            success=refund_result.success,
            transaction_id=refund_result.refund_id,
            amount=refund_result.amount,
            currency=refund_result.currency,
            message=refund_result.message,
            provider=refund_result.provider,
            error=refund_result.error,
        )

    # ==========================================================================
    # SUBSCRIPTION OPERATIONS
    # ==========================================================================

    def create_subscription(
        self,
        plan_id: str,
        customer_email: str,
        trial_days: int = 0,
        metadata: dict[str, Any] | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ):
        """
        Create a subscription.

        Args:
            plan_id: Provider-specific plan ID
            customer_email: Customer email
            trial_days: Trial period days
            metadata: Additional metadata
            provider: Provider to use (uses preferred if None)
            **kwargs: Provider-specific parameters

        Returns:
            SubscriptionResult with subscription details
        """
        payment_provider = self._get_provider(provider)
        return payment_provider.create_subscription(
            plan_id=plan_id,
            customer_email=customer_email,
            metadata=metadata,
            trial_days=trial_days,
            **kwargs,
        )

    def cancel_subscription(
        self,
        provider_subscription_id: str,
        cancel_at_period_end: bool = True,
        provider: str | None = None,
        **kwargs: Any,
    ):
        """Cancel a subscription."""
        payment_provider = self._get_provider(provider)
        return payment_provider.cancel_subscription(
            provider_subscription_id=provider_subscription_id,
            cancel_at_period_end=cancel_at_period_end,
            **kwargs,
        )

    def update_subscription(
        self,
        provider_subscription_id: str,
        plan_id: str | None = None,
        quantity: int | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ):
        """Update a subscription."""
        payment_provider = self._get_provider(provider)
        return payment_provider.update_subscription(
            provider_subscription_id=provider_subscription_id,
            plan_id=plan_id,
            quantity=quantity,
            **kwargs,
        )

    # ==========================================================================
    # WEBHOOK OPERATIONS
    # ==========================================================================

    def parse_webhook(
        self,
        provider: str,
        payload: bytes | str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ):
        """
        Parse a webhook event from a specific provider.

        Args:
            provider: Provider that sent the webhook
            payload: Raw webhook payload
            headers: HTTP headers
            **kwargs: Additional parameters

        Returns:
            WebhookEvent with parsed data
        """
        payment_provider = self._get_provider(provider)
        return payment_provider.parse_webhook(payload, headers, **kwargs)

    def handle_webhook(
        self,
        provider: str,
        event,
        **kwargs: Any,
    ):
        """Handle a parsed webhook event."""
        payment_provider = self._get_provider(provider)
        return payment_provider.handle_webhook_event(event, **kwargs)

    # ==========================================================================
    # HIGH-LEVEL SUBSCRIPTION INTEGRATION
    # ==========================================================================

    def register_user_with_subscription(
        self,
        user,
        plan_id: int,
        payment_method: str = "stripe",
        billing_frequency: str = "Monthly",
        trial_days: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Register a new user with subscription (high-level operation).

        This method integrates with the existing subscription models
        and creates the necessary database records.

        Args:
            user: User instance
            plan_id: Internal plan ID
            payment_method: Payment method (stripe, paypal, bank_transfer)
            billing_frequency: Billing frequency
            trial_days: Trial period
            **kwargs: Additional parameters

        Returns:
            Dict with subscription details
        """
        from myapp.models import Payment, Subscription, SubscriptionPlan

        try:
            # Get the plan
            plan = SubscriptionPlan.objects.get(
                subscription_plan_id=plan_id, is_active=1, is_deleted=0
            )

            # Calculate dates
            start_date = timezone.now().date()
            frequency_days = {
                "Monthly": 30,
                "Yearly": 365,
                "Weekly": 7,
                "Quarterly": 90,
            }
            end_date = start_date + timedelta(
                days=frequency_days.get(billing_frequency, 30)
            )

            # Create subscription
            subscription = Subscription.objects.create(
                user=user,
                subscription_plan=plan,
                billing_frequency=billing_frequency,
                start_date=start_date,
                end_date=end_date,
                auto_renew=1,
                status="Active",
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=user.user_id,
            )

            # Determine amount based on billing frequency
            amount = (
                plan.yearly_price
                if billing_frequency == "Yearly"
                else plan.monthly_price
            )

            # For paid plans, create payment intent
            payment_result = None
            if amount and amount > 0:
                payment_result = self.create_payment_intent(
                    amount=float(amount),
                    currency="USD",
                    description=f"{plan.name} - {billing_frequency}",
                    customer_email=user.email,
                    metadata={
                        "subscription_id": subscription.subscription_id,
                        "user_id": user.user_id,
                        "plan_id": plan_id,
                    },
                    provider=payment_method,
                )

                # Create payment record
                Payment.objects.create(
                    subscription=subscription,
                    amount=amount,
                    payment_date=start_date,
                    payment_method=payment_method,
                    reference_number=payment_result.transaction_id or "",
                    status="Pending",
                    payment_response=payment_result.message,
                    is_active=1,
                    is_deleted=0,
                    created_at=timezone.now(),
                    created_by=user.user_id,
                )
            else:
                # Free plan - create completed payment record
                Payment.objects.create(
                    subscription=subscription,
                    amount=0,
                    payment_date=start_date,
                    payment_method=payment_method,
                    reference_number=f"free_{subscription.subscription_id}",
                    status="Completed",
                    payment_response="Free trial subscription",
                    is_active=1,
                    is_deleted=0,
                    created_at=timezone.now(),
                    created_by=user.user_id,
                )

            return {
                "success": True,
                "subscription_id": subscription.subscription_id,
                "status": subscription.status,
                "payment_result": payment_result.to_dict() if payment_result else None,
            }

        except Exception as e:
            logger.error(f"Failed to register user subscription: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================

    @staticmethod
    def _detect_provider_from_transaction(transaction_id: str) -> str:
        """
        Detect which provider was used from transaction ID format.

        Args:
            transaction_id: Transaction ID to analyze

        Returns:
            Provider name
        """
        if transaction_id.startswith("pi_") or transaction_id.startswith("ch_"):
            return "stripe"
        elif transaction_id.startswith("bt_") or transaction_id.startswith("bt_sub_"):
            return "bank_transfer"
        elif transaction_id.startswith("PAYPAL") or transaction_id.startswith("PAY-"):
            return "paypal"
        elif transaction_id.startswith("google.") or ".a.o" in transaction_id:
            # Google Play transaction IDs often contain '.a.o' pattern
            return "google_play"
        elif len(transaction_id) >= 20 and transaction_id.replace("-", "").isalnum():
            # Apple transaction IDs are typically long alphanumeric strings
            # Could be Apple IAP (need context to confirm)
            return "apple_iap"
        else:
            # Default to configured provider
            return getattr(settings, "DEFAULT_PAYMENT_PROVIDER", "stripe")

    @staticmethod
    def calculate_prorated_amount(
        original_amount: Decimal | float,
        _original_frequency: str,
        _new_frequency: str,
        days_remaining: int,
    ) -> Decimal:
        """
        Calculate prorated amount for plan changes.

        Args:
            original_amount: Original plan amount
            original_frequency: Original billing frequency
            new_frequency: New billing frequency
            days_remaining: Days remaining in current period

        Returns:
            Prorated amount
        """
        amount = Decimal(str(original_amount))

        # Simple proration: (amount / 30) * days_remaining
        if days_remaining > 0 and days_remaining < 30:
            daily_rate = amount / 30
            return daily_rate * days_remaining

        return amount


def get_payment_manager(preferred_provider: str | None = None) -> PaymentManager:
    """
    Convenience function to get a PaymentManager instance.

    Args:
        preferred_provider: Default provider to use

    Returns:
        PaymentManager instance
    """
    return PaymentManager(preferred_provider)
