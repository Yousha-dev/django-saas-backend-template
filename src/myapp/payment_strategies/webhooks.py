# myapp/payment_strategies/webhooks.py
"""
Webhook handlers for payment providers.

This module provides webhook event handling with automatic
subscription and payment updates in database.
"""

import logging
from typing import Any

from django.utils import timezone

from myapp.models.choices import PaymentStatus, SubscriptionStatus

from .base import WebhookEvent

logger = logging.getLogger(__name__)


class WebhookHandler:
    """
    Base webhook handler with common functionality.

    This class provides methods to handle webhook events
    and update database accordingly.
    """

    @staticmethod
    def handle_stripe_webhook(event: WebhookEvent, **kwargs: Any) -> dict[str, Any]:
        """
        Handle a Stripe webhook event.

        Args:
            event: Parsed webhook event
            **kwargs: Additional context

        Returns:
            Dict with handling result
        """
        event_type = event.event_type
        payload = event.payload.get("data", {}).get("object", {})

        handlers = {
            "payment_intent.succeeded": _handle_stripe_payment_succeeded,
            "payment_intent.payment_failed": _handle_stripe_payment_failed,
            "invoice.paid": _handle_stripe_invoice_paid,
            "invoice.payment_failed": _handle_stripe_invoice_payment_failed,
            "customer.subscription.created": _handle_stripe_subscription_created,
            "customer.subscription.updated": _handle_stripe_subscription_updated,
            "customer.subscription.deleted": _handle_stripe_subscription_deleted,
        }

        handler = handlers.get(event_type)
        if handler:
            return handler(payload, **kwargs)

        logger.info(f"Unhandled Stripe event type: {event_type}")
        return {"status": "ignored", "message": f"Unhandled event: {event_type}"}

    @staticmethod
    def handle_paypal_webhook(event: WebhookEvent, **kwargs: Any) -> dict[str, Any]:
        """
        Handle a PayPal webhook event.

        Args:
            event: Parsed webhook event
            **kwargs: Additional context

        Returns:
            Dict with handling result
        """
        event_type = event.event_type
        payload = event.payload

        # PayPal event types use dot notation
        handlers = {
            "PAYMENT.CAPTURE.COMPLETED": _handle_paypal_payment_completed,
            "PAYMENT.CAPTURE.DENIED": _handle_paypal_payment_denied,
            "BILLING.SUBSCRIPTION.CREATED": _handle_paypal_subscription_created,
            "BILLING.SUBSCRIPTION.ACTIVATED": _handle_paypal_subscription_activated,
            "BILLING.SUBSCRIPTION.CANCELLED": _handle_paypal_subscription_cancelled,
            "PAYMENT.SALE.COMPLETED": _handle_paypal_sale_completed,
        }

        handler = handlers.get(event_type)
        if handler:
            return handler(payload, **kwargs)

        logger.info(f"Unhandled PayPal event type: {event_type}")
        return {"status": "ignored", "message": f"Unhandled event: {event_type}"}


# =============================================================================
# STRIPE EVENT HANDLERS
# =============================================================================


def _handle_stripe_payment_succeeded(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle Stripe payment_intent.succeeded event."""
    from myapp.models import Payment

    payment_intent_id = payload.get("id")
    amount = payload.get("amount", 0) / 100  # Convert from cents
    currency = payload.get("currency", "usd").upper()

    # Update payment record
    try:
        payment = Payment.objects.filter(
            reference_number=payment_intent_id, is_deleted=0
        ).first()

        if payment:
            payment.status = PaymentStatus.COMPLETED.value
            payment.payment_date = timezone.now().date()
            payment.payment_response = (
                f"Payment succeeded via Stripe. Amount: {amount} {currency}"
            )
            payment.updated_at = timezone.now()
            payment.save()

            # Update subscription if applicable
            if payment.subscription:
                subscription = payment.subscription
                subscription.status = SubscriptionStatus.ACTIVE.value
                subscription.is_active = 1
                subscription.updated_at = timezone.now()
                subscription.save()

            logger.info(f"Payment {payment_intent_id} marked as completed")

            return {
                "status": "processed",
                "message": "Payment succeeded",
                "payment_id": payment.payment_id,
            }
    except Exception as e:
        logger.error(f"Error updating payment after success: {e}")

    return {"status": "processed", "message": "Payment succeeded"}


def _handle_stripe_payment_failed(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle Stripe payment_intent.payment_failed event."""
    from myapp.models import Payment

    payment_intent_id = payload.get("id")
    error = payload.get("last_payment_error", {})

    # Update payment record
    try:
        payment = Payment.objects.filter(
            reference_number=payment_intent_id, is_deleted=0
        ).first()

        if payment:
            payment.status = PaymentStatus.FAILED.value
            payment.payment_response = (
                f"Payment failed: {error.get('message', 'Unknown error')}"
            )
            payment.updated_at = timezone.now()
            payment.save()

            logger.warning(
                f"Payment {payment_intent_id} failed: {error.get('message')}"
            )

            return {
                "status": "processed",
                "message": "Payment failed recorded",
                "payment_id": payment.payment_id,
            }
    except Exception as e:
        logger.error(f"Error updating payment after failure: {e}")

    return {"status": "processed", "message": "Payment failure recorded"}


def _handle_stripe_invoice_paid(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle Stripe invoice.paid event (subscription renewal)."""
    from myapp.models import Payment, Subscription

    subscription_id = payload.get("subscription")
    invoice_id = payload.get("id")
    amount_paid = payload.get("amount_paid", 0) / 100
    payload.get("currency", "usd").upper()

    # Find subscription by provider subscription ID
    try:
        subscription = Subscription.objects.filter(
            provider_subscription_id=subscription_id, is_deleted=0
        ).first()

        if subscription:
            # Create payment record for renewal
            Payment.objects.create(
                subscription=subscription,
                amount=amount_paid,
                payment_date=timezone.now().date(),
                payment_method="stripe",
                reference_number=invoice_id,
                status=PaymentStatus.COMPLETED.value,
                payment_response="Subscription renewal payment via Stripe",
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=subscription.user_id or 0,
            )

            # Update subscription status
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.is_active = 1
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.info(
                f"Subscription {subscription.subscription_id} renewed via Stripe invoice"
            )

            return {
                "status": "processed",
                "message": "Subscription renewed",
                "subscription_id": subscription.subscription_id,
            }
    except Exception as e:
        logger.error(f"Error processing Stripe invoice paid: {e}")

    return {"status": "processed", "message": "Invoice paid recorded"}


def _handle_stripe_invoice_payment_failed(
    payload: dict, **kwargs: Any
) -> dict[str, Any]:
    """Handle Stripe invoice.payment_failed event."""
    from myapp.models import Subscription

    subscription_id = payload.get("subscription")

    try:
        subscription = Subscription.objects.filter(
            provider_subscription_id=subscription_id, is_deleted=0
        ).first()

        if subscription:
            # Mark subscription as past due
            subscription.status = "Suspended"
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.warning(
                f"Subscription {subscription.subscription_id} payment failed"
            )

            return {
                "status": "processed",
                "message": "Subscription payment failed",
                "subscription_id": subscription.subscription_id,
            }
    except Exception as e:
        logger.error(f"Error processing invoice payment failed: {e}")

    return {"status": "processed", "message": "Invoice payment failure recorded"}


def _handle_stripe_subscription_created(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle Stripe customer.subscription.created event."""

    subscription_id = payload.get("id")
    payload.get("status")
    payload.get("current_period_end")

    # Try to find and update existing subscription
    try:
        # This is typically for webhooks from Stripe dashboard
        # For our app, subscriptions are created internally first
        logger.info(f"Stripe subscription created: {subscription_id}")

        return {
            "status": "processed",
            "message": "Stripe subscription created",
            "stripe_subscription_id": subscription_id,
        }
    except Exception as e:
        logger.error(f"Error processing subscription created: {e}")

    return {"status": "processed", "message": "Subscription created recorded"}


def _handle_stripe_subscription_updated(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle Stripe customer.subscription.updated event."""
    from myapp.models import Subscription

    subscription_id = payload.get("id")
    status = payload.get("status")

    try:
        subscription = Subscription.objects.filter(
            provider_subscription_id=subscription_id, is_deleted=0
        ).first()

        if subscription:
            # Update subscription status
            status_map = {
                "active": SubscriptionStatus.ACTIVE.value,
                "past_due": "Suspended",
                "canceled": SubscriptionStatus.CANCELLED.value,
                "unpaid": SubscriptionStatus.EXPIRED.value,
                "trialing": SubscriptionStatus.ACTIVE.value,
            }

            subscription.status = status_map.get(
                status, SubscriptionStatus.ACTIVE.value
            )
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.info(
                f"Subscription {subscription.subscription_id} updated to {subscription.status}"
            )

            return {
                "status": "processed",
                "message": "Subscription updated",
                "subscription_id": subscription.subscription_id,
            }
    except Exception as e:
        logger.error(f"Error processing subscription updated: {e}")

    return {"status": "processed", "message": "Subscription update recorded"}


def _handle_stripe_subscription_deleted(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle Stripe customer.subscription.deleted event."""
    from myapp.models import Subscription

    subscription_id = payload.get("id")

    try:
        subscription = Subscription.objects.filter(
            provider_subscription_id=subscription_id, is_deleted=0
        ).first()

        if subscription:
            subscription.status = "Cancelled"
            subscription.is_active = 0
            subscription.auto_renew = 0
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.info(
                f"Subscription {subscription.subscription_id} cancelled via Stripe"
            )

            return {
                "status": "processed",
                "message": "Subscription cancelled",
                "subscription_id": subscription.subscription_id,
            }
    except Exception as e:
        logger.error(f"Error processing subscription deleted: {e}")

    return {"status": "processed", "message": "Subscription cancellation recorded"}


# =============================================================================
# PAYPAL EVENT HANDLERS
# =============================================================================


def _handle_paypal_payment_completed(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle PayPal payment capture completed event."""
    from myapp.models import Payment

    capture_id = payload.get("resource", {}).get("id", "")
    amount_info = payload.get("resource", {}).get("amount", {})
    amount = float(amount_info.get("value", "0"))
    currency = amount_info.get("currency_code", "USD")

    # Update payment record
    try:
        payment = Payment.objects.filter(
            reference_number=capture_id, is_deleted=0
        ).first()

        if payment:
            payment.status = "Completed"
            payment.payment_date = timezone.now().date()
            payment.payment_response = (
                f"Payment succeeded via PayPal. Amount: {amount} {currency}"
            )
            payment.updated_at = timezone.now()
            payment.save()

            # Update subscription if applicable
            if payment.subscription:
                subscription = payment.subscription
                subscription.status = "Active"
                subscription.is_active = 1
                subscription.updated_at = timezone.now()
                subscription.save()

            logger.info(f"PayPal payment {capture_id} marked as completed")

            return {
                "status": "processed",
                "message": "Payment succeeded",
                "payment_id": payment.payment_id,
            }
    except Exception as e:
        logger.error(f"Error updating PayPal payment: {e}")

    return {"status": "processed", "message": "PayPal payment recorded"}


def _handle_paypal_payment_denied(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle PayPal payment capture denied event."""
    from myapp.models import Payment

    capture_id = payload.get("resource", {}).get("id", "")

    try:
        payment = Payment.objects.filter(
            reference_number=capture_id, is_deleted=0
        ).first()

        if payment:
            payment.status = PaymentStatus.FAILED.value
            payment.payment_response = "Payment denied via PayPal"
            payment.updated_at = timezone.now()
            payment.save()

            logger.warning(f"PayPal payment {capture_id} denied")

            return {
                "status": "processed",
                "message": "Payment denied",
                "payment_id": payment.payment_id,
            }
    except Exception as e:
        logger.error(f"Error processing PayPal payment denied: {e}")

    return {"status": "processed", "message": "PayPal payment denial recorded"}


def _handle_paypal_subscription_created(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle PayPal billing subscription created event."""
    subscription_id = payload.get("resource", {}).get("id", "")

    logger.info(f"PayPal subscription created: {subscription_id}")

    return {
        "status": "processed",
        "message": "PayPal subscription created",
        "paypal_subscription_id": subscription_id,
    }


def _handle_paypal_subscription_activated(
    payload: dict, **kwargs: Any
) -> dict[str, Any]:
    """Handle PayPal billing subscription activated event."""
    from myapp.models import Subscription

    subscription_id = payload.get("resource", {}).get("id", "")

    try:
        subscription = Subscription.objects.filter(
            provider_subscription_id=subscription_id, is_deleted=0
        ).first()

        if subscription:
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.is_active = 1
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.info(f"PayPal subscription {subscription.subscription_id} activated")

            return {
                "status": "processed",
                "message": "Subscription activated",
                "subscription_id": subscription.subscription_id,
            }
    except Exception as e:
        logger.error(f"Error processing PayPal subscription activated: {e}")

    return {"status": "processed", "message": "PayPal subscription activated"}


def _handle_paypal_subscription_cancelled(
    payload: dict, **kwargs: Any
) -> dict[str, Any]:
    """Handle PayPal billing subscription cancelled event."""
    from myapp.models import Subscription

    subscription_id = payload.get("resource", {}).get("id", "")

    try:
        subscription = Subscription.objects.filter(
            provider_subscription_id=subscription_id, is_deleted=0
        ).first()

        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED.value
            subscription.is_active = 0
            subscription.auto_renew = 0
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.info(f"PayPal subscription {subscription.subscription_id} cancelled")

            return {
                "status": "processed",
                "message": "Subscription cancelled",
                "subscription_id": subscription.subscription_id,
            }
    except Exception as e:
        logger.error(f"Error processing PayPal subscription cancelled: {e}")

    return {
        "status": "processed",
        "message": "PayPal subscription cancellation recorded",
    }


def _handle_paypal_sale_completed(payload: dict, **kwargs: Any) -> dict[str, Any]:
    """Handle PayPal payment sale completed event (legacy)."""
    # Similar to payment capture completed
    return _handle_paypal_payment_completed(payload, **kwargs)
