# myapp/payment_strategies/__init__.py
"""
Payment processing strategies using the Strategy pattern.

This module provides a pluggable interface for payment providers,
allowing easy addition of new payment methods without changing core business logic.

Supported providers:
- Stripe
- PayPal
- PayPal (legacy)
- Bank Transfer (manual)

Usage:
    from myapp.payment_strategies import PaymentProviderFactory

    strategy = PaymentProviderFactory.get_strategy('stripe')
    result = strategy.create_payment_intent(amount=100, currency='usd')
"""

from .base import PaymentError, PaymentProvider, PaymentResult, WebhookEvent
from .factory import PaymentManager, PaymentProviderFactory
from .providers.bank_transfer import BankTransferPaymentProvider
from .providers.paypal import PayPalPaymentProvider
from .providers.stripe import StripePaymentProvider

__all__ = [
    "BankTransferPaymentProvider",
    "PayPalPaymentProvider",
    "PaymentError",
    "PaymentManager",
    # Base classes
    "PaymentProvider",
    # Factory
    "PaymentProviderFactory",
    "PaymentResult",
    # Providers
    "StripePaymentProvider",
    "WebhookEvent",
]
