"""
pytest configuration and shared fixtures for Template Backend tests.
"""

import os
import sys
from pathlib import Path

import django
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("DJANGO_ENV", "test")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuration.settings")

# Setup Django
django.setup()


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Enable database access for all tests."""
    pass


@pytest.fixture
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup database before tests run."""
    pass


@pytest.fixture
def api_client():
    """API client for testing endpoints."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def auth_client(api_client, test_user):
    """Authenticated API client with the test_user."""
    from rest_framework_simplejwt.tokens import RefreshToken

    user = test_user

    refresh = RefreshToken.for_user(user)
    # Add custom claims
    refresh["user_id"] = user.user_id
    refresh["role"] = user.role

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    return {"client": api_client, "user": user, "token": str(refresh.access_token)}


@pytest.fixture
def test_user(django_db_setup):
    """Create a test user."""
    from myapp.models import User

    return User.objects.create_user(
        email="testuser@example.com",
        password="testpass123",
        full_name="Test User",
    )


@pytest.fixture
def admin_user(django_db_setup):
    """Create an admin user."""
    from myapp.models import User

    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        full_name="Admin User",
    )


@pytest.fixture
def subscription_plan(django_db_setup):
    """Create a test subscription plan."""
    from myapp.models import SubscriptionPlan

    return SubscriptionPlan.objects.create(
        name="Test Plan",
        description="A test subscription plan",
        monthly_price=9.99,
        yearly_price=99.99,
        max_operations=10,
        max_api_calls_per_hour=100,
        feature_details="Basic test features",
        is_active=1,
        is_deleted=0,
    )


@pytest.fixture
def free_plan(django_db_setup):
    """Create a free subscription plan."""
    from myapp.models import SubscriptionPlan

    return SubscriptionPlan.objects.create(
        name="Free",
        description="Free tier",
        monthly_price=0,
        yearly_price=0,
        max_operations=1,
        max_api_calls_per_hour=10,
        feature_details="Free features",
        is_active=1,
        is_deleted=0,
    )


@pytest.fixture
def test_subscription(django_db_setup, test_user, subscription_plan):
    """Create a test subscription."""
    from django.utils import timezone

    from myapp.models import Subscription

    return Subscription.objects.create(
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


@pytest.fixture
def test_event(django_db_setup, test_user):
    """Create a test event."""
    from datetime import date, time

    from myapp.models import Event

    return Event.objects.create(
        user=test_user,
        title="Test Event",
        type="Action",
        category="Work",
        description="A test event",
        start_time=time(10, 0),
        end_time=time(11, 0),
        start_date=date(2025, 1, 15),
        repeated=0,
        email_to="test@example.com",
        is_active=1,
        is_deleted=0,
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    """Authenticated API client with admin privileges."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    refresh["user_id"] = admin_user.user_id
    refresh["role"] = admin_user.role

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return {
        "client": api_client,
        "user": admin_user,
        "token": str(refresh.access_token),
    }


@pytest.fixture
def test_reminder(django_db_setup, test_user):
    """Create a test reminder."""
    from django.utils import timezone

    from myapp.models import Reminder

    return Reminder.objects.create(
        user=test_user,
        note="Don't forget your meeting!",
        timestamp=timezone.now() + timezone.timedelta(hours=1),
        is_active=1,
        is_deleted=0,
    )


@pytest.fixture
def test_payment(django_db_setup, test_user, test_subscription):
    """Create a test payment."""
    from django.utils import timezone

    from myapp.models import Payment

    return Payment.objects.create(
        user=test_user,
        subscription=test_subscription,
        amount=9.99,
        status="Completed",
        payment_method="Credit Card",
        payment_date=timezone.now(),
        is_active=1,
        is_deleted=0,
    )


@pytest.fixture
def test_post(django_db_setup, test_user):
    """Create a test post."""
    from myapp.models import Post

    return Post.objects.create(
        author=test_user,
        title="Test Post",
        content_text="This is a test post content.",
        content_type="general",
        is_active=1,
        is_deleted=0,
        created_by=test_user.user_id,
    )


@pytest.fixture
def test_comment(django_db_setup, test_user, test_post):
    """Create a test comment on a post."""
    from myapp.models import Comment

    return Comment.objects.create(
        author=test_user,
        post=test_post,
        content_text="This is a test comment.",
        is_active=1,
        is_deleted=0,
        created_by=test_user.user_id,
    )


@pytest.fixture
def test_coupon(django_db_setup):
    """Create a test coupon."""
    from django.utils import timezone

    from myapp.models import Coupon

    return Coupon.objects.create(
        code="TESTCOUPON20",
        description="20% off test coupon",
        discount_type="percentage",
        discount_value=20.00,
        valid_from=timezone.now() - timezone.timedelta(days=1),
        valid_until=timezone.now() + timezone.timedelta(days=30),
        max_uses=100,
        current_uses=0,
        max_uses_per_user=1,
        first_purchase_only=False,
        is_active=1,
        is_deleted=0,
    )


@pytest.fixture
def test_referral_code(django_db_setup, test_user):
    """Create a test referral code."""
    from myapp.models import ReferralCode

    return ReferralCode.objects.create(
        user=test_user,
        code="TESTREF1",
        max_uses=0,
        current_uses=0,
        reward_type="credit",
        reward_amount=10.00,
        is_active=1,
        is_deleted=0,
        created_by=test_user.user_id,
    )


@pytest.fixture
def mock_celery(monkeypatch):
    """Mock Celery tasks."""
    mock_apply = pytest.MagicMock()
    mock_apply.return_value.id = "test-task-id"

    monkeypatch.setattr(
        "myapp.tasks.tasks.send_notification_task.apply_async", mock_apply
    )

    return mock_apply


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis cache."""
    mock_cache = pytest.MagicMock()
    monkeypatch.setattr("django.core.cache", "cache", mock_cache)
    return mock_cache


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
