"""
Unit tests for service layer.

Tests cover DiscountService, ReferralService, and SubscriptionService.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


@pytest.mark.unit
class TestDiscountService:
    """Tests for DiscountService."""

    def test_validate_coupon_valid(self, test_coupon, test_user):
        """Test validating a valid coupon."""
        from myapp.services.discount_service import DiscountService

        result = DiscountService.validate_coupon(
            code=test_coupon.code, user_id=test_user.user_id
        )
        assert result["valid"] is True
        assert result["discount_type"] == "percentage"
        assert result["amount"] == 20.0

    def test_validate_coupon_invalid_code(self, test_user):
        """Test validating a non-existent coupon."""
        from myapp.services.discount_service import DiscountService

        result = DiscountService.validate_coupon(
            code="NONEXISTENT", user_id=test_user.user_id
        )
        assert result["valid"] is False

    def test_validate_coupon_expired(self, test_user):
        """Test validating an expired coupon."""
        from myapp.models import Coupon
        from myapp.services.discount_service import DiscountService

        coupon = Coupon.objects.create(
            code="EXPIRED",
            description="Expired coupon",
            discount_type="percentage",
            discount_value=10.00,
            valid_from=timezone.now() - timedelta(days=30),
            valid_until=timezone.now() - timedelta(days=1),
            max_uses=100,
            current_uses=0,
            max_uses_per_user=1,
            is_active=1,
            is_deleted=0,
        )

        result = DiscountService.validate_coupon(
            code=coupon.code, user_id=test_user.user_id
        )
        assert result["valid"] is False
        assert "expired" in result["message"].lower()

    def test_apply_coupon_percentage(self, test_coupon, test_user):
        """Test applying a percentage coupon."""
        from myapp.services.discount_service import DiscountService

        result = DiscountService.apply_coupon(
            code=test_coupon.code,
            user_id=test_user.user_id,
            original_amount=Decimal("100.00"),
        )
        assert result["success"] is True
        assert result["final_amount"] == 80.0
        assert result["discount_applied"] == 20.0

    def test_apply_coupon_fixed(self, test_user):
        """Test applying a fixed-amount coupon."""
        from myapp.models import Coupon
        from myapp.services.discount_service import DiscountService

        coupon = Coupon.objects.create(
            code="FIXED15",
            description="$15 off",
            discount_type="fixed",
            discount_value=15.00,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30),
            max_uses=100,
            current_uses=0,
            max_uses_per_user=1,
            is_active=1,
            is_deleted=0,
        )

        result = DiscountService.apply_coupon(
            code=coupon.code,
            user_id=test_user.user_id,
            original_amount=Decimal("50.00"),
        )
        assert result["success"] is True
        assert result["final_amount"] == 35.0

    def test_calculate_discounted_price_percentage(self):
        """Test percentage discount calculation."""
        from myapp.services.discount_service import DiscountService

        result = DiscountService.calculate_discounted_price(
            Decimal("100"), {"valid": True, "discount_type": "percentage", "amount": 25}
        )
        assert result == Decimal("75")

    def test_calculate_discounted_price_fixed(self):
        """Test fixed discount calculation."""
        from myapp.services.discount_service import DiscountService

        result = DiscountService.calculate_discounted_price(
            Decimal("100"), {"valid": True, "discount_type": "fixed", "amount": 30}
        )
        assert result == Decimal("70")

    def test_calculate_discounted_price_invalid(self):
        """Test discount with invalid data returns original price."""
        from myapp.services.discount_service import DiscountService

        result = DiscountService.calculate_discounted_price(
            Decimal("100"), {"valid": False}
        )
        assert result == Decimal("100")


@pytest.mark.unit
class TestReferralService:
    """Tests for ReferralService."""

    def test_generate_referral_code(self, test_user):
        """Test generating a referral code."""
        from myapp.services.referral_service import ReferralService

        result = ReferralService.generate_referral_code(user_id=test_user.user_id)
        assert result["success"] is True
        assert "code" in result
        assert len(result["code"]) == 8

    def test_generate_referral_code_idempotent(self, test_user, test_referral_code):
        """Test generating code when one already exists returns existing."""
        from myapp.services.referral_service import ReferralService

        result = ReferralService.generate_referral_code(user_id=test_user.user_id)
        assert result["success"] is True
        assert result["code"] == test_referral_code.code

    def test_apply_referral_self_referral(self, test_user, test_referral_code):
        """Test self-referral is rejected."""
        from myapp.services.referral_service import ReferralService

        result = ReferralService.apply_referral(
            referrer_code=test_referral_code.code, new_user_id=test_user.user_id
        )
        assert result["success"] is False
        assert "own" in result["message"].lower()

    def test_apply_referral_invalid_code(self, test_user):
        """Test applying invalid referral code."""
        from myapp.services.referral_service import ReferralService

        result = ReferralService.apply_referral(
            referrer_code="NONEXISTENT", new_user_id=test_user.user_id
        )
        assert result["success"] is False

    def test_apply_referral_success(self, test_referral_code):
        """Test applying a valid referral code for a new user."""
        from myapp.models import User
        from myapp.services.referral_service import ReferralService

        new_user = User.objects.create_user(
            email="referred@example.com",
            password="pass123",
            full_name="Referred User",
        )

        result = ReferralService.apply_referral(
            referrer_code=test_referral_code.code, new_user_id=new_user.user_id
        )
        assert result["success"] is True
        assert "transaction_id" in result

    def test_get_referral_stats_with_code(self, test_user, test_referral_code):
        """Test getting referral stats for a user with a code."""
        from myapp.services.referral_service import ReferralService

        stats = ReferralService.get_referral_stats(user_id=test_user.user_id)
        assert stats["has_code"] is True
        assert stats["code"] == test_referral_code.code
        assert stats["total_referrals"] == 0

    def test_get_referral_stats_no_code(self):
        """Test getting referral stats for a user without a code."""
        from myapp.models import User
        from myapp.services.referral_service import ReferralService

        user = User.objects.create_user(
            email="noreferral@example.com",
            password="pass123",
            full_name="No Referral User",
        )

        stats = ReferralService.get_referral_stats(user_id=user.user_id)
        assert stats["has_code"] is False
        assert stats["total_referrals"] == 0


@pytest.mark.unit
class TestAnalyticsService:
    """Tests for AnalyticsService."""

    def test_aggregate_monthly_data(self):
        """Test monthly data aggregation."""
        from myapp.services.analytics_service import AnalyticsService

        now = timezone.now()
        result = AnalyticsService.aggregate_monthly_data(now.year, now.month)
        assert result is True

    def test_get_dashboard_stats(self):
        """Test dashboard stats retrieval."""
        from myapp.services.analytics_service import AnalyticsService

        stats = AnalyticsService.get_dashboard_stats()
        assert "mrr" in stats
        assert "active_subscribers" in stats
        assert "total_users" in stats
        assert "new_users_this_month" in stats


@pytest.mark.unit
class TestNotificationService:
    """Tests for NotificationService."""

    def test_notification_service_init(self):
        """Test NotificationService initialization."""
        from myapp.services.notification_service import NotificationService

        service = NotificationService()
        assert service.config is not None
        assert "SENDGRID_API_KEY" in service.config


@pytest.mark.unit
class TestPaymentService:
    """Tests for PaymentService."""

    def _make_payment_result(self, success=True, **kwargs):
        """Helper to build a mock PaymentResult."""
        from unittest.mock import MagicMock

        result = MagicMock()
        result.success = success
        result.transaction_id = kwargs.get("transaction_id", "tx_123")
        result.provider_transaction_id = kwargs.get("provider_tx_id", "pi_stripe_123")
        result.amount = kwargs.get("amount", Decimal("9.99"))
        result.currency = kwargs.get("currency", "USD")
        result.status = kwargs.get("status", "completed")
        result.message = kwargs.get("message", "OK")
        result.provider = kwargs.get("provider", "stripe")
        result.provider_data = {}
        result.error = kwargs.get("error")
        return result

    def test_basic_payment(self, test_user, monkeypatch):
        """Test creating a basic payment without coupon or referral."""
        from unittest.mock import MagicMock

        from myapp.services.payment.payment_service import PaymentService

        mock_manager = MagicMock()
        mock_manager.create_payment.return_value = self._make_payment_result()
        monkeypatch.setattr(
            "myapp.services.payment.payment_service.get_payment_manager",
            lambda: mock_manager,
        )

        result = PaymentService.create_payment(
            user_id=test_user.user_id,
            amount=Decimal("9.99"),
            currency="USD",
            provider="stripe",
        )
        assert result["success"] is True
        assert result["transaction_id"] == "tx_123"
        assert result["final_amount"] == 9.99
        assert result["discount_applied"] == 0.0
        mock_manager.create_payment.assert_called_once()

    def test_payment_with_coupon(self, test_user, test_coupon, monkeypatch):
        """Test payment with a valid coupon applied."""
        from unittest.mock import MagicMock

        from myapp.services.payment.payment_service import PaymentService

        mock_manager = MagicMock()
        mock_manager.create_payment.return_value = self._make_payment_result()
        monkeypatch.setattr(
            "myapp.services.payment.payment_service.get_payment_manager",
            lambda: mock_manager,
        )

        result = PaymentService.create_payment(
            user_id=test_user.user_id,
            amount=Decimal("100.00"),
            coupon_code=test_coupon.code,
        )
        assert result["success"] is True
        assert result["discount_applied"] == 20.0
        assert result["final_amount"] == 80.0

    def test_payment_with_invalid_coupon(self, test_user, monkeypatch):
        """Test payment with invalid coupon code is rejected."""
        from myapp.services.payment.payment_service import PaymentService

        result = PaymentService.create_payment(
            user_id=test_user.user_id,
            amount=Decimal("50.00"),
            coupon_code="FAKECOUPON",
        )
        assert result["success"] is False
        assert "message" in result

    def test_payment_provider_failure(self, test_user, monkeypatch):
        """Test handling when payment provider fails."""
        from unittest.mock import MagicMock

        from myapp.services.payment.payment_service import PaymentService

        mock_manager = MagicMock()
        mock_manager.create_payment.return_value = self._make_payment_result(
            success=False, message="Card declined"
        )
        monkeypatch.setattr(
            "myapp.services.payment.payment_service.get_payment_manager",
            lambda: mock_manager,
        )

        result = PaymentService.create_payment(
            user_id=test_user.user_id,
            amount=Decimal("9.99"),
        )
        assert result["success"] is False

    def test_payment_with_referral(self, test_user, test_referral_code, monkeypatch):
        """Test payment with a referral code."""
        from unittest.mock import MagicMock

        from myapp.models import User
        from myapp.services.payment.payment_service import PaymentService

        # Create a different user to avoid self-referral
        new_user = User.objects.create_user(
            email="newpayer@example.com",
            password="pass123",
            full_name="New Payer",
        )

        mock_manager = MagicMock()
        mock_manager.create_payment.return_value = self._make_payment_result()
        monkeypatch.setattr(
            "myapp.services.payment.payment_service.get_payment_manager",
            lambda: mock_manager,
        )

        result = PaymentService.create_payment(
            user_id=new_user.user_id,
            amount=Decimal("50.00"),
            referral_code=test_referral_code.code,
        )
        assert result["success"] is True
        assert result.get("referral_applied") is True


@pytest.mark.unit
class TestRefundService:
    """Tests for RefundService."""

    def test_refund_completed_payment(self, test_payment, monkeypatch):
        """Test refunding a completed payment."""
        from unittest.mock import MagicMock

        from myapp.services.payment.refund import RefundService

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.transaction_id = "refund_123"

        mock_manager = MagicMock()
        mock_manager.refund_payment.return_value = mock_result
        monkeypatch.setattr(
            "myapp.services.payment.refund.get_payment_manager",
            lambda: mock_manager,
        )

        result = RefundService.process_refund(
            payment_id=test_payment.payment_id,
            reason="Customer request",
        )
        assert result["success"] is True
        assert result["refund_id"] == "refund_123"

    def test_refund_non_completed_payment(self, test_payment):
        """Test refunding a payment that is not completed."""
        from myapp.services.payment.refund import RefundService

        test_payment.status = "Pending"
        test_payment.save()

        result = RefundService.process_refund(payment_id=test_payment.payment_id)
        assert result["success"] is False
        assert "not in completed status" in result["message"]

    def test_refund_nonexistent_payment(self):
        """Test refunding a payment that does not exist."""
        from myapp.services.payment.refund import RefundService

        result = RefundService.process_refund(payment_id=999999)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_partial_refund(self, test_payment, monkeypatch):
        """Test partial refund updates status correctly."""
        from unittest.mock import MagicMock

        from myapp.services.payment.refund import RefundService

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.transaction_id = "partial_refund_123"

        mock_manager = MagicMock()
        mock_manager.refund_payment.return_value = mock_result
        monkeypatch.setattr(
            "myapp.services.payment.refund.get_payment_manager",
            lambda: mock_manager,
        )

        result = RefundService.process_refund(
            payment_id=test_payment.payment_id,
            amount=Decimal("5.00"),
            reason="Partial refund",
        )
        assert result["success"] is True

        # Verify status was set to partially refunded
        test_payment.refresh_from_db()
        assert (
            "partial" in test_payment.status.lower()
            or "Partially" in test_payment.status
        )

    def test_refund_provider_failure(self, test_payment, monkeypatch):
        """Test handling when refund provider fails."""
        from unittest.mock import MagicMock

        from myapp.services.payment.refund import RefundService

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Insufficient funds for refund"

        mock_manager = MagicMock()
        mock_manager.refund_payment.return_value = mock_result
        monkeypatch.setattr(
            "myapp.services.payment.refund.get_payment_manager",
            lambda: mock_manager,
        )

        result = RefundService.process_refund(
            payment_id=test_payment.payment_id,
            reason="Test failure",
        )
        assert result["success"] is False
        assert "Insufficient" in result["message"]


@pytest.mark.unit
class TestSubscriptionService:
    """Tests for SubscriptionService."""

    def test_get_user_subscription(self, test_user, test_subscription):
        """Test getting an active subscription for a user."""
        from myapp.services.subscription_service import SubscriptionService

        sub = SubscriptionService.get_user_subscription(test_user)
        assert sub is not None
        assert sub.subscription_id == test_subscription.subscription_id
        assert sub.status == "Active"

    def test_get_user_subscription_creates_default(self, test_user, subscription_plan):
        """Test that a default subscription is created if none exists."""
        from myapp.services.subscription_service import SubscriptionService

        sub = SubscriptionService.get_user_subscription(test_user)
        assert sub is not None
        assert sub.status == "Active"
        assert sub.user == test_user

    def test_is_subscription_valid(self, test_user, test_subscription):
        """Test subscription validity check."""
        from myapp.services.subscription_service import SubscriptionService

        is_valid, msg = SubscriptionService.is_subscription_valid(test_user)
        assert is_valid is True
        assert "valid" in msg.lower()

    def test_get_subscription_features(self, test_user, test_subscription):
        """Test getting subscription features dict."""
        from myapp.services.subscription_service import SubscriptionService

        features = SubscriptionService.get_subscription_features(test_user)
        assert "plan_name" in features
        assert "features" in features
        assert "is_valid" in features
        assert features["plan_name"] == "Test Plan"

    def test_get_subscription_features_with_flags(
        self, test_user, test_subscription, subscription_plan
    ):
        """Test getting features when FeatureFlags are configured."""
        from myapp.models.features import FeatureFlags
        from myapp.services.subscription_service import SubscriptionService

        FeatureFlags.objects.create(
            subscription_plan=subscription_plan,
            features={
                "api_access": {"enabled": True, "calls_per_hour": 100},
                "ai_analytics": {"enabled": True},
            },
        )

        features = SubscriptionService.get_subscription_features(test_user)
        assert features["features"].get("api_access", {}).get("enabled") is True

    def test_can_use_feature(self, test_user, test_subscription, subscription_plan):
        """Test feature access check."""
        from myapp.models.features import FeatureDefinition, FeatureFlags
        from myapp.services.subscription_service import SubscriptionService

        FeatureFlags.objects.create(
            subscription_plan=subscription_plan,
            features={
                "api_access": {"enabled": True, "calls_per_hour": 50},
            },
        )

        can_use, _msg = SubscriptionService.can_use_feature(
            test_user, FeatureDefinition.API_ENABLED
        )
        assert can_use is True

    def test_can_use_feature_disabled(
        self, test_user, test_subscription, subscription_plan
    ):
        """Test feature access is denied when disabled."""
        from myapp.models.features import FeatureDefinition, FeatureFlags
        from myapp.services.subscription_service import SubscriptionService

        FeatureFlags.objects.create(
            subscription_plan=subscription_plan,
            features={
                "api_access": {"enabled": False},
            },
        )

        can_use, _msg = SubscriptionService.can_use_feature(
            test_user, FeatureDefinition.API_ENABLED
        )
        assert can_use is False

    def test_cancel_subscription(self, test_user, test_subscription):
        """Test cancelling a subscription."""
        from myapp.services.subscription_service import SubscriptionService

        success, msg = SubscriptionService.cancel_subscription(test_user)
        assert success is True
        assert "cancelled" in msg.lower()

        test_subscription.refresh_from_db()
        assert test_subscription.status == "Cancelled"
        assert test_subscription.auto_renew == 0

    def test_extend_subscription(self, test_user, test_subscription):
        """Test extending a subscription."""
        from myapp.services.subscription_service import SubscriptionService

        original_end = test_subscription.end_date
        success, _msg = SubscriptionService.extend_subscription(test_user, 15)
        assert success is True

        test_subscription.refresh_from_db()
        assert test_subscription.end_date == original_end + timedelta(days=15)

    def test_change_subscription_plan(self, test_user, test_subscription, free_plan):
        """Test changing to a different subscription plan."""
        from myapp.services.subscription_service import SubscriptionService

        success, msg = SubscriptionService.change_user_subscription_plan(
            test_user, free_plan.subscription_plan_id
        )
        assert success is True
        assert free_plan.name in msg

    def test_change_same_plan_rejected(
        self, test_user, test_subscription, subscription_plan
    ):
        """Test changing to the same plan is rejected."""
        from myapp.services.subscription_service import SubscriptionService

        success, msg = SubscriptionService.change_user_subscription_plan(
            test_user, subscription_plan.subscription_plan_id
        )
        assert success is False
        assert "already" in msg.lower()

    def test_get_available_plans(self, subscription_plan, free_plan):
        """Test listing available plans."""
        from myapp.services.subscription_service import SubscriptionService

        plans = SubscriptionService.get_available_plans()
        assert len(plans) >= 2
        plan_names = [p["name"] for p in plans]
        assert "Test Plan" in plan_names
        assert "Free" in plan_names

    def test_is_plan_upgrade(self, test_user, test_subscription, free_plan):
        """Test upgrade/downgrade detection."""
        from myapp.services.subscription_service import SubscriptionService

        success, info = SubscriptionService.is_plan_upgrade(
            test_user, free_plan.subscription_plan_id
        )
        assert success is True
        assert info["change_type"] == "downgrade"

    def test_get_subscription_stats(self, test_user, test_subscription):
        """Test comprehensive stats."""
        from myapp.services.subscription_service import SubscriptionService

        stats = SubscriptionService.get_subscription_stats(test_user)
        assert "subscription" in stats
        assert "features_available" in stats

    def test_renew_subscription(self, test_user, test_subscription):
        """Test subscription renewal."""
        from myapp.services.subscription_service import SubscriptionService

        result = SubscriptionService.renew_subscription(
            test_subscription.subscription_id
        )
        assert result["success"] is True
        assert "new_end_date" in result

    def test_renew_subscription_auto_renew_disabled(self, test_user, test_subscription):
        """Test renewal fails when auto_renew is disabled."""
        from myapp.services.subscription_service import SubscriptionService

        test_subscription.auto_renew = False
        test_subscription.save()

        result = SubscriptionService.renew_subscription(
            test_subscription.subscription_id
        )
        assert result["success"] is False
        assert "auto-renew" in result["message"].lower()
