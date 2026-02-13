"""
Unit tests for Django models.

Tests cover the current model structure after the AbstractBaseUser refactor
and generic SaaS template changes.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from myapp.models import (
    ActivityLog,
    AuditLog,
    Comment,
    Coupon,
    CouponUsage,
    Event,
    FeatureFlags,
    ModerationAppeal,
    ModerationQueue,
    Notification,
    Payment,
    Post,
    ReferralCode,
    ReferralTransaction,
    Reminder,
    Role,
    Subscription,
    SubscriptionPlan,
    User,
)
from myapp.models.choices import DiscountType, ModerationStatus, ReferralRewardType

# =============================================================================
# USER MODEL TESTS
# =============================================================================


@pytest.mark.unit
class TestUser:
    """Tests for User model (AbstractBaseUser)."""

    def test_create_user(self, django_db_setup):
        """Test creating a standard user via UserManager."""
        user = User.objects.create_user(
            email="user@example.com",
            password="testpass123",
            full_name="Test User",
        )
        assert user.email == "user@example.com"
        assert user.full_name == "Test User"
        assert user.role == Role.USER
        assert not user.is_staff
        assert not user.is_superuser
        assert user.check_password("testpass123")
        assert user.is_active == 1
        assert user.is_deleted == 0

    def test_create_superuser(self, django_db_setup):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            full_name="Admin User",
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == Role.ADMIN

    def test_create_user_no_email_raises(self, django_db_setup):
        """Test that creating user without email raises ValueError."""
        with pytest.raises(ValueError, match="Email"):
            User.objects.create_user(email="", password="pass123", full_name="No Email")

    def test_user_str(self, django_db_setup):
        """Test User string representation."""
        user = User(email="test@example.com", full_name="Test User")
        assert str(user) == "Test User (test@example.com)"

    def test_user_is_admin(self, django_db_setup):
        """Test is_admin helper."""
        admin = User(email="a@b.com", full_name="Admin", role=Role.ADMIN)
        user = User(email="u@b.com", full_name="User", role=Role.USER)
        assert admin.is_admin() is True
        assert user.is_admin() is False

    def test_user_is_moderator(self, django_db_setup):
        """Test is_moderator helper."""
        mod = User(email="m@b.com", full_name="Mod", role=Role.MODERATOR)
        assert mod.is_moderator() is True

    def test_user_password_hash_alias(self, django_db_setup):
        """Test backward-compatible password_hash property."""
        user = User.objects.create_user(
            email="alias@example.com",
            password="testpass",
            full_name="Alias Test",
        )
        # password_hash should be an alias for password
        assert user.password_hash == user.password
        assert user.password_hash.startswith("pbkdf2_sha256$")

    def test_user_has_custom_smtp(self, django_db_setup):
        """Test custom SMTP detection."""
        user = User(
            email="test@example.com",
            full_name="Test",
            use_user_smtp=1,
            smtp_host="smtp.example.com",
        )
        assert user.has_custom_smtp() is True

        user_no_smtp = User(email="test2@example.com", full_name="Test2")
        assert user_no_smtp.has_custom_smtp() is False

    def test_user_has_perm_superuser(self, django_db_setup):
        """Test has_perm for superuser returns True."""
        su = User(email="su@b.com", full_name="SU", is_superuser=True)
        assert su.has_perm("any.permission") is True

    def test_user_has_module_perms_admin(self, django_db_setup):
        """Test has_module_perms for admin role."""
        admin = User(email="a@b.com", full_name="Admin", role=Role.ADMIN)
        assert admin.has_module_perms("myapp") is True


# =============================================================================
# SUBSCRIPTION PLAN TESTS
# =============================================================================


@pytest.mark.unit
class TestSubscriptionPlan:
    """Tests for SubscriptionPlan model."""

    def test_create_plan(self, django_db_setup):
        """Test creating a subscription plan."""
        plan = SubscriptionPlan.objects.create(
            name="Pro Plan",
            description="Professional plan",
            monthly_price=Decimal("29.99"),
            yearly_price=Decimal("299.99"),
            max_operations=10,
            max_api_calls_per_hour=100,
            feature_details="Advanced features",
            is_active=1,
            is_deleted=0,
        )
        assert plan.name == "Pro Plan"
        assert plan.monthly_price == Decimal("29.99")
        assert plan.is_active == 1

    def test_plan_str(self, django_db_setup):
        """Test SubscriptionPlan string representation."""
        plan = SubscriptionPlan(name="Test Plan", monthly_price=Decimal("9.99"))
        assert "Test Plan" in str(plan)
        assert "9.99" in str(plan)


# =============================================================================
# SUBSCRIPTION TESTS
# =============================================================================


@pytest.mark.unit
class TestSubscription:
    """Tests for Subscription model."""

    def test_create_subscription(self, test_user, subscription_plan):
        """Test creating a subscription."""
        sub = Subscription.objects.create(
            user=test_user,
            subscription_plan=subscription_plan,
            billing_frequency="Monthly",
            start_date=timezone.now(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            status="Active",
            auto_renew=True,
            is_active=1,
            is_deleted=0,
        )
        assert sub.user == test_user
        assert sub.subscription_plan == subscription_plan
        assert sub.status == "Active"


# =============================================================================
# PAYMENT TESTS
# =============================================================================


@pytest.mark.unit
class TestPayment:
    """Tests for Payment model."""

    def test_create_payment(self, test_user, test_subscription):
        """Test creating a payment record."""
        payment = Payment.objects.create(
            subscription=test_subscription,
            user=test_user,
            amount=Decimal("9.99"),
            payment_date=timezone.now().date(),
            payment_method="CreditCard",
            status="Completed",
            is_active=1,
            is_deleted=0,
        )
        assert payment.amount == Decimal("9.99")
        assert payment.status == "Completed"


# =============================================================================
# EVENT & REMINDER TESTS
# =============================================================================


@pytest.mark.unit
class TestEvent:
    """Tests for Event model."""

    def test_create_event(self, test_user):
        """Test creating an event."""
        from datetime import date, time

        event = Event.objects.create(
            user=test_user,
            title="Team Meeting",
            type="Action",
            category="Work",
            description="Weekly sync",
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=date(2025, 1, 15),
            repeated=0,
            email_to="user@example.com",
            is_active=1,
            is_deleted=0,
        )
        assert event.title == "Team Meeting"
        assert event.user == test_user
        assert event.is_recurring() is False

    def test_recurring_event(self, test_user):
        """Test recurring event detection."""
        from datetime import date, time

        event = Event.objects.create(
            user=test_user,
            title="Daily Standup",
            type="Action",
            category="Work",
            start_time=time(9, 0),
            end_time=time(9, 15),
            start_date=date(2025, 1, 1),
            repeated=1,
            frequency="Daily",
            email_to="team@example.com",
            is_active=1,
            is_deleted=0,
        )
        assert event.is_recurring() is True


@pytest.mark.unit
class TestReminder:
    """Tests for Reminder model."""

    def test_create_reminder(self, test_user):
        """Test creating a reminder."""
        reminder = Reminder.objects.create(
            user=test_user,
            note="Remember to review PRs",
            timestamp=timezone.now(),
            is_active=1,
            is_deleted=0,
        )
        assert reminder.note == "Remember to review PRs"
        assert reminder.user == test_user


# =============================================================================
# NOTIFICATION TESTS
# =============================================================================


@pytest.mark.unit
class TestNotification:
    """Tests for Notification model."""

    def test_create_notification(self, test_user):
        """Test creating a notification."""
        notification = Notification.objects.create(
            user=test_user,
            title="New Message",
            message="You have a new message",
            type="Info",
            is_active=1,
            is_deleted=0,
        )
        assert notification.user == test_user
        assert notification.title == "New Message"


# =============================================================================
# LOGGING TESTS
# =============================================================================


@pytest.mark.unit
class TestActivityLog:
    """Tests for ActivityLog model."""

    def test_create_activity_log(self, test_user):
        """Test creating an activity log entry."""
        log = ActivityLog.objects.create(
            user=test_user,
            activity_type="user_login",
            activity_details="Logged in from 127.0.0.1",
            activity_date=timezone.now(),
            is_active=1,
            is_deleted=0,
        )
        assert log.user == test_user
        assert log.activity_type == "user_login"


@pytest.mark.unit
class TestAuditLog:
    """Tests for AuditLog model."""

    def test_create_audit_log(self, test_user):
        """Test creating an audit log entry."""
        log = AuditLog.objects.create(
            user=test_user,
            action="CREATE",
            table_affected="Subscriptions",
            is_active=1,
            is_deleted=0,
        )
        assert log.user == test_user
        assert log.action == "CREATE"


# =============================================================================
# DISCOUNT & COUPON TESTS
# =============================================================================


@pytest.mark.unit
class TestCoupon:
    """Tests for Coupon model."""

    def test_create_coupon(self, django_db_setup):
        """Test creating a coupon."""
        from datetime import timedelta

        coupon = Coupon.objects.create(
            code="SAVE20",
            description="20% off",
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=Decimal("20.00"),
            max_uses=100,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=30),
            is_active=1,
            is_deleted=0,
        )
        assert coupon.code == "SAVE20"
        assert coupon.discount_value == Decimal("20.00")

    def test_coupon_usage(self, test_user, django_db_setup):
        """Test creating a coupon usage record."""
        from datetime import timedelta

        coupon = Coupon.objects.create(
            code="TEST10",
            discount_type=DiscountType.FIXED.value,
            discount_value=Decimal("10.00"),
            max_uses=50,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=30),
            is_active=1,
            is_deleted=0,
        )
        usage = CouponUsage.objects.create(
            coupon=coupon,
            user=test_user,
            discount_applied=Decimal("10.00"),
            original_amount=Decimal("29.99"),
            final_amount=Decimal("19.99"),
            is_active=1,
            is_deleted=0,
        )
        assert usage.discount_applied == Decimal("10.00")


# =============================================================================
# REFERRAL TESTS
# =============================================================================


@pytest.mark.unit
class TestReferral:
    """Tests for ReferralCode and ReferralTransaction models."""

    def test_create_referral_code(self, test_user):
        """Test creating a referral code."""
        ref_code = ReferralCode.objects.create(
            user=test_user,
            code="MYREF123",
            max_uses=10,
            reward_type=ReferralRewardType.CREDIT.value,
            reward_amount=Decimal("5.00"),
            is_active=1,
            is_deleted=0,
        )
        assert ref_code.code == "MYREF123"
        assert ref_code.user == test_user

    def test_referral_transaction(self, test_user, django_db_setup):
        """Test creating a referral transaction."""
        ref_code = ReferralCode.objects.create(
            user=test_user,
            code="REF456",
            max_uses=5,
            reward_type=ReferralRewardType.DISCOUNT.value,
            reward_amount=Decimal("10.00"),
            is_active=1,
            is_deleted=0,
        )
        referred = User.objects.create_user(
            email="referred@example.com",
            password="pass123",
            full_name="Referred User",
        )
        tx = ReferralTransaction.objects.create(
            referral_code=ref_code,
            referred_user=referred,
            is_active=1,
            is_deleted=0,
        )
        assert tx.referral_code == ref_code
        assert tx.referred_user == referred


# =============================================================================
# CONTENT & MODERATION TESTS
# =============================================================================


@pytest.mark.unit
class TestContent:
    """Tests for Post and Comment models."""

    def test_create_post(self, test_user):
        """Test creating a post."""
        post = Post.objects.create(
            author=test_user,
            title="My First Post",
            content_text="Hello World!",
            content_type="article",
            is_active=1,
            is_deleted=0,
        )
        assert post.title == "My First Post"
        assert post.author == test_user

    def test_create_comment(self, test_user):
        """Test creating a comment on a post."""
        post = Post.objects.create(
            author=test_user,
            title="Test Post",
            content_text="Post body",
            is_active=1,
            is_deleted=0,
        )
        comment = Comment.objects.create(
            author=test_user,
            post=post,
            content_text="Great post!",
            is_active=1,
            is_deleted=0,
        )
        assert comment.post == post
        assert comment.author == test_user


@pytest.mark.unit
class TestModeration:
    """Tests for ModerationQueue and ModerationAppeal models."""

    def test_create_moderation_queue_item(self, test_user):
        """Test creating a moderation queue item."""
        item = ModerationQueue.objects.create(
            content_type="Post",
            content_id=1,
            reporter_id=test_user,
            reason="Inappropriate content",
            status=ModerationStatus.PENDING.value,
            is_active=1,
            is_deleted=0,
        )
        assert item.reporter_id == test_user
        assert item.status == ModerationStatus.PENDING.value

    def test_create_moderation_appeal(self, test_user):
        """Test creating a moderation appeal."""
        item = ModerationQueue.objects.create(
            content_type="Post",
            content_id=1,
            reporter_id=test_user,
            reason="Spam",
            status=ModerationStatus.REJECTED.value,
            is_active=1,
            is_deleted=0,
        )
        appeal = ModerationAppeal.objects.create(
            original_queue=item,
            user=test_user,
            reason="This was not spam",
            is_active=1,
            is_deleted=0,
        )
        assert appeal.original_queue == item
        assert appeal.user == test_user


# =============================================================================
# BASE MODEL TESTS
# =============================================================================


@pytest.mark.unit
class TestBaseModel:
    """Tests for BaseModel soft delete and activation."""

    def test_soft_delete(self, test_user):
        """Test soft_delete method."""
        notification = Notification.objects.create(
            user=test_user,
            title="To Delete",
            message="Will be soft deleted",
            type="Info",
            is_active=1,
            is_deleted=0,
        )
        notification.soft_delete()
        notification.refresh_from_db()
        assert notification.is_deleted == 1
        assert notification.is_active == 0

    def test_restore(self, test_user):
        """Test restoring a soft-deleted record."""
        notification = Notification.objects.create(
            user=test_user,
            title="To Restore",
            message="Will be restored",
            type="Info",
            is_active=0,
            is_deleted=1,
        )
        notification.restore()
        notification.refresh_from_db()
        assert notification.is_deleted == 0


# =============================================================================
# FEATURE FLAGS TESTS
# =============================================================================


@pytest.mark.unit
class TestFeatureFlags:
    """Tests for FeatureFlags model."""

    def test_create_feature_flags(self, subscription_plan):
        """Test creating feature flags for a plan."""
        flags = FeatureFlags.objects.create(
            subscription_plan=subscription_plan,
            features={
                "api_access": {"enabled": True, "calls_per_hour": 100},
                "ai_analytics": {"enabled": False},
            },
        )
        assert flags.subscription_plan == subscription_plan
        assert flags.features["api_access"]["enabled"] is True

    def test_get_feature(self, subscription_plan):
        """Test get_feature with dot notation."""
        flags = FeatureFlags.objects.create(
            subscription_plan=subscription_plan,
            features={
                "api_access": {"enabled": True, "calls_per_hour": 100},
                "ai_analytics": {"enabled": False},
            },
        )
        assert flags.get_feature("api_access.enabled") is True
        assert flags.get_feature("api_access.calls_per_hour") == 100
        assert flags.get_feature("ai_analytics.enabled") is False
        assert flags.get_feature("nonexistent", default="N/A") == "N/A"

    def test_is_enabled(self, subscription_plan):
        """Test is_enabled method."""
        flags = FeatureFlags.objects.create(
            subscription_plan=subscription_plan,
            features={
                "api_access": {"enabled": True},
                "beta_feature": False,
            },
        )
        assert flags.is_enabled("api_access.enabled") is True
        assert flags.is_enabled("beta_feature") is False

    def test_enable_disable(self, subscription_plan):
        """Test enable and disable methods."""
        flags = FeatureFlags.objects.create(
            subscription_plan=subscription_plan,
            features={"new_feature": False},
        )
        flags.enable("new_feature")
        assert flags.get_feature("new_feature") is True

        flags.disable("new_feature")
        assert flags.get_feature("new_feature") is False
