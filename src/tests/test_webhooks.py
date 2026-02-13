"""
Unit tests for webhook handlers.

Tests cover WebhookHandler.handle_stripe_webhook and
WebhookHandler.handle_paypal_webhook for key event types.
"""

import pytest

from myapp.payment_strategies.base import WebhookEvent


@pytest.mark.unit
class TestStripeWebhookHandler:
    """Tests for Stripe webhook handling."""

    def _make_event(self, event_type, payload_data=None):
        return WebhookEvent(
            event_id="evt_test_123",
            event_type=event_type,
            provider="stripe",
            payload={"data": {"object": payload_data or {}}},
        )

    def test_payment_succeeded(self, test_payment):
        """Test payment_intent.succeeded updates payment status."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        event = self._make_event(
            "payment_intent.succeeded",
            {
                "id": test_payment.reference_number or "pi_test",
                "amount": 999,
                "currency": "usd",
            },
        )

        # Set reference_number so handler can find the payment
        test_payment.reference_number = "pi_test"
        test_payment.save()

        result = WebhookHandler.handle_stripe_webhook(event)
        assert result["status"] == "processed"

    def test_payment_failed(self, test_payment):
        """Test payment_intent.payment_failed records failure."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        test_payment.reference_number = "pi_fail_test"
        test_payment.save()

        event = self._make_event(
            "payment_intent.payment_failed",
            {
                "id": "pi_fail_test",
                "last_payment_error": {"message": "Card declined"},
            },
        )

        result = WebhookHandler.handle_stripe_webhook(event)
        assert result["status"] == "processed"

        test_payment.refresh_from_db()
        assert test_payment.status == "Failed"

    def test_invoice_paid_renews_subscription(self, test_subscription):
        """Test invoice.paid event renews subscription."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        test_subscription.provider_subscription_id = "sub_test_123"
        test_subscription.save()

        event = self._make_event(
            "invoice.paid",
            {
                "id": "inv_test_123",
                "subscription": "sub_test_123",
                "amount_paid": 999,
                "currency": "usd",
            },
        )

        result = WebhookHandler.handle_stripe_webhook(event)
        assert result["status"] == "processed"

    def test_subscription_deleted_cancels(self, test_subscription):
        """Test customer.subscription.deleted cancels subscription."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        test_subscription.provider_subscription_id = "sub_del_test"
        test_subscription.save()

        event = self._make_event(
            "customer.subscription.deleted",
            {"id": "sub_del_test"},
        )

        result = WebhookHandler.handle_stripe_webhook(event)
        assert result["status"] == "processed"

        test_subscription.refresh_from_db()
        assert test_subscription.status == "Cancelled"
        assert test_subscription.is_active == 0

    def test_unhandled_event_type(self):
        """Test unhandled event type returns ignored status."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        event = self._make_event("unknown.event.type", {})
        result = WebhookHandler.handle_stripe_webhook(event)
        assert result["status"] == "ignored"

    def test_subscription_updated(self, test_subscription):
        """Test customer.subscription.updated updates status."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        test_subscription.provider_subscription_id = "sub_upd_test"
        test_subscription.save()

        event = self._make_event(
            "customer.subscription.updated",
            {"id": "sub_upd_test", "status": "past_due"},
        )

        result = WebhookHandler.handle_stripe_webhook(event)
        assert result["status"] == "processed"

        test_subscription.refresh_from_db()
        assert test_subscription.status == "Suspended"

    def test_invoice_payment_failed(self, test_subscription):
        """Test invoice.payment_failed suspends subscription."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        test_subscription.provider_subscription_id = "sub_inv_fail"
        test_subscription.save()

        event = self._make_event(
            "invoice.payment_failed",
            {"subscription": "sub_inv_fail"},
        )

        result = WebhookHandler.handle_stripe_webhook(event)
        assert result["status"] == "processed"

        test_subscription.refresh_from_db()
        assert test_subscription.status == "Suspended"


@pytest.mark.unit
class TestPayPalWebhookHandler:
    """Tests for PayPal webhook handling."""

    def _make_event(self, event_type, payload=None):
        return WebhookEvent(
            event_id="evt_pp_123",
            event_type=event_type,
            provider="paypal",
            payload=payload or {},
        )

    def test_unhandled_paypal_event(self):
        """Test unhandled PayPal event returns ignored."""
        from myapp.payment_strategies.webhooks import WebhookHandler

        event = self._make_event("UNKNOWN.EVENT", {})
        result = WebhookHandler.handle_paypal_webhook(event)
        assert result["status"] == "ignored"
