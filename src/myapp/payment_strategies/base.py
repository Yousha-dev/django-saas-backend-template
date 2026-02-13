# myapp/payment_strategies/base.py
"""
Base classes for the payment strategy pattern.

This module defines the abstract interface that all payment providers
must implement, following the Strategy design pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from myapp.models.choices import PaymentStatus


class PaymentError(Exception):
    """
    Exception raised for payment-related errors.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        provider: The payment provider that raised the error
        details: Additional error details from the provider
    """

    def __init__(
        self,
        message: str,
        code: str = "PAYMENT_ERROR",
        provider: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "provider": self.provider,
            "details": self.details,
        }


@dataclass
class WebhookEvent:
    """
    Represents a payment webhook event.

    Attributes:
        event_id: Unique identifier for the event
        event_type: Type of event (e.g., 'payment.succeeded')
        provider: Payment provider that sent the event
        payload: Raw event payload from provider
        processed: Whether the event has been processed
        received_at: When the event was received
    """

    event_id: str
    event_type: str
    provider: str
    payload: dict[str, Any]
    processed: bool = False
    received_at: datetime = field(default_factory=datetime.utcnow)

    def mark_processed(self) -> None:
        """Mark the event as processed."""
        self.processed = True


@dataclass
class PaymentResult:
    """
    Result of a payment operation.

    Attributes:
        success: Whether the operation was successful
        transaction_id: Unique transaction identifier from provider
        provider_transaction_id: Provider's transaction reference
        amount: Payment amount
        currency: Payment currency (e.g., 'USD')
        status: Current payment status
        message: Human-readable result message
        provider: Payment provider used
        provider_data: Raw response data from provider
        error: PaymentError if operation failed
        redirect_url: URL to redirect user for payment completion
        client_secret: Client secret for frontend payment confirmation
    """

    success: bool
    transaction_id: str | None = None
    provider_transaction_id: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    message: str = ""
    provider: str = ""
    provider_data: dict[str, Any] = field(default_factory=dict)
    error: PaymentError | None = None
    redirect_url: str | None = None
    client_secret: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for API responses."""
        result = {
            "success": self.success,
            "transaction_id": self.transaction_id,
            "amount": str(self.amount) if self.amount else None,
            "currency": self.currency,
            "status": self.status.value
            if isinstance(self.status, PaymentStatus)
            else self.status,
            "message": self.message,
            "provider": self.provider,
        }

        if self.redirect_url:
            result["redirect_url"] = self.redirect_url

        if self.client_secret:
            result["client_secret"] = self.client_secret

        if self.provider_data:
            result["provider_data"] = self.provider_data

        if self.error:
            result["error"] = self.error.to_dict()

        return result


@dataclass
class SubscriptionResult:
    """
    Result of a subscription operation.

    Attributes:
        success: Whether the operation was successful
        subscription_id: Internal subscription ID
        provider_subscription_id: Provider's subscription identifier
        status: Subscription status
        plan_id: Plan ID subscribed to
        message: Human-readable result message
        provider: Payment provider used
        provider_data: Raw response data from provider
        error: PaymentError if operation failed
    """

    success: bool
    subscription_id: int | None = None
    provider_subscription_id: str | None = None
    status: str = "pending"
    plan_id: int | None = None
    message: str = ""
    provider: str = ""
    provider_data: dict[str, Any] = field(default_factory=dict)
    error: PaymentError | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for API responses."""
        result = {
            "success": self.success,
            "subscription_id": self.subscription_id,
            "status": self.status,
            "plan_id": self.plan_id,
            "message": self.message,
            "provider": self.provider,
        }

        if self.provider_subscription_id:
            result["provider_subscription_id"] = self.provider_subscription_id

        if self.provider_data:
            result["provider_data"] = self.provider_data

        if self.error:
            result["error"] = self.error.to_dict()

        return result


@dataclass
class RefundResult:
    """
    Result of a refund operation.

    Attributes:
        success: Whether the refund was successful
        refund_id: Internal refund ID
        provider_refund_id: Provider's refund identifier
        amount: Refund amount
        currency: Refund currency
        status: Refund status
        reason: Refund reason
        message: Human-readable result message
        provider: Payment provider used
        error: PaymentError if operation failed
    """

    success: bool
    refund_id: str | None = None
    provider_refund_id: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    status: str = "pending"
    reason: str = ""
    message: str = ""
    provider: str = ""
    error: PaymentError | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for API responses."""
        result = {
            "success": self.success,
            "refund_id": self.refund_id,
            "amount": str(self.amount) if self.amount else None,
            "currency": self.currency,
            "status": self.status,
            "reason": self.reason,
            "message": self.message,
            "provider": self.provider,
        }

        if self.provider_refund_id:
            result["provider_refund_id"] = self.provider_refund_id

        if self.error:
            result["error"] = self.error.to_dict()

        return result


class PaymentProvider(ABC):
    """
    Abstract base class for payment provider strategies.

    All payment providers must implement this interface to ensure
    consistent behavior across different payment methods.

    Implementations should be stateless to allow for concurrent use.
    """

    #: Provider identifier (e.g., 'stripe', 'paypal')
    provider_name: str = ""

    #: Display name for the provider
    display_name: str = ""

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the payment provider.

        Args:
            config: Provider-specific configuration (API keys, etc.)
        """
        self.config = config or {}

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured.

        Returns:
            True if the provider has valid credentials and configuration
        """
        pass

    @abstractmethod
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
        Create a payment intent for a one-time payment.

        Args:
            amount: Payment amount
            currency: Currency code (e.g., 'USD')
            description: Payment description
            metadata: Additional metadata to attach
            customer_email: Customer email for receipts
            **kwargs: Provider-specific parameters

        Returns:
            PaymentResult with transaction details
        """
        pass

    @abstractmethod
    def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Confirm and process a payment intent.

        Args:
            payment_intent_id: Payment intent identifier
            payment_method_id: Payment method to charge
            **kwargs: Provider-specific parameters

        Returns:
            PaymentResult with updated transaction details
        """
        pass

    @abstractmethod
    def get_payment_status(
        self,
        transaction_id: str,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Get the current status of a payment.

        Args:
            transaction_id: Transaction identifier
            **kwargs: Provider-specific parameters

        Returns:
            PaymentResult with current status
        """
        pass

    @abstractmethod
    def create_subscription(
        self,
        plan_id: str,
        customer_email: str | None = None,
        metadata: dict[str, Any] | None = None,
        trial_days: int = 0,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Create a recurring subscription.

        Args:
            plan_id: Provider-specific plan identifier
            customer_email: Customer email
            metadata: Additional metadata
            trial_days: Trial period days
            **kwargs: Provider-specific parameters

        Returns:
            SubscriptionResult with subscription details
        """
        pass

    @abstractmethod
    def cancel_subscription(
        self,
        provider_subscription_id: str,
        cancel_at_period_end: bool = True,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Cancel a subscription.

        Args:
            provider_subscription_id: Provider subscription identifier
            cancel_at_period_end: If True, cancel at period end
            **kwargs: Provider-specific parameters

        Returns:
            SubscriptionResult with cancellation details
        """
        pass

    @abstractmethod
    def update_subscription(
        self,
        provider_subscription_id: str,
        plan_id: str | None = None,
        quantity: int | None = None,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Update a subscription (plan, quantity, etc.).

        Args:
            provider_subscription_id: Provider subscription identifier
            plan_id: New plan identifier
            quantity: New quantity
            **kwargs: Provider-specific parameters

        Returns:
            SubscriptionResult with updated details
        """
        pass

    @abstractmethod
    def refund_payment(
        self,
        transaction_id: str,
        amount: Decimal | float | None = None,
        reason: str = "",
        **kwargs: Any,
    ) -> RefundResult:
        """
        Refund a payment (full or partial).

        Args:
            transaction_id: Transaction to refund
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Provider-specific parameters

        Returns:
            RefundResult with refund details
        """
        pass

    @abstractmethod
    def parse_webhook(
        self,
        payload: bytes | str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> WebhookEvent:
        """
        Parse and validate a webhook event from the provider.

        Args:
            payload: Raw webhook payload
            headers: HTTP headers from webhook request
            **kwargs: Provider-specific parameters

        Returns:
            WebhookEvent with parsed data

        Raises:
            PaymentError: If webhook is invalid or signature verification fails
        """
        pass

    def handle_webhook_event(
        self,
        event: WebhookEvent,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Handle a parsed webhook event.

        This method provides a default implementation that can be overridden
        by specific providers to handle common event types.

        Args:
            event: Parsed webhook event
            **kwargs: Additional context

        Returns:
            Dict with handling result
        """
        event_type = event.event_type.lower()

        handlers = {
            "payment.succeeded": self._handle_payment_succeeded,
            "payment.failed": self._handle_payment_failed,
            "subscription.created": self._handle_subscription_created,
            "subscription.updated": self._handle_subscription_updated,
            "subscription.cancelled": self._handle_subscription_cancelled,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            return handler(event)

        return {"status": "ignored", "message": f"Unhandled event type: {event_type}"}

    def _handle_payment_succeeded(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle payment succeeded event."""
        return {"status": "processed", "message": "Payment succeeded"}

    def _handle_payment_failed(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle payment failed event."""
        return {"status": "processed", "message": "Payment failed"}

    def _handle_subscription_created(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle subscription created event."""
        return {"status": "processed", "message": "Subscription created"}

    def _handle_subscription_updated(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle subscription updated event."""
        return {"status": "processed", "message": "Subscription updated"}

    def _handle_subscription_cancelled(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle subscription cancelled event."""
        return {"status": "processed", "message": "Subscription cancelled"}

    def _handle_invoice_paid(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle invoice paid event."""
        return {"status": "processed", "message": "Invoice paid"}

    def _handle_invoice_payment_failed(self, event: WebhookEvent) -> dict[str, Any]:
        """Handle invoice payment failed event."""
        return {"status": "processed", "message": "Invoice payment failed"}
