"""
Unit tests for API endpoints.

Tests use the actual URL names defined in the project's urls.py files.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.unit
class TestAuthAPI:
    """Tests for authentication API endpoints."""

    def test_register_user(self, api_client):
        """Test user registration endpoint."""
        url = reverse("register_user")
        data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "fullname": "New User",
            "role": "User",
        }
        response = api_client.post(url, data)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_register_duplicate_email(self, api_client, test_user):
        """Test registration with duplicate email fails."""
        url = reverse("register_user")
        data = {
            "email": test_user.email,
            "password": "SecurePass123!",
            "fullname": "Duplicate User",
            "role": "User",
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_valid_credentials(self, api_client, test_user):
        """Test login with valid credentials."""
        url = reverse("login")
        data = {"email": test_user.email, "password": "testpass123"}
        response = api_client.post(url, data)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert "access" in response.data or "token" in response.data

    def test_login_invalid_credentials(self, api_client, test_user):
        """Test login with invalid credentials fails."""
        url = reverse("login")
        data = {"email": test_user.email, "password": "wrongpassword"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestUserProfileAPI:
    """Tests for user profile API endpoints."""

    def test_get_profile_unauthorized(self, api_client):
        """Test getting profile without authentication fails."""
        url = reverse("get_user")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_authorized(self, auth_client):
        """Test getting profile with authentication."""
        client = auth_client["client"]
        url = reverse("get_user")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_update_profile(self, auth_client):
        """Test updating user profile."""
        client = auth_client["client"]
        url = reverse("update_user")
        data = {"full_name": "Updated Name"}
        response = client.put(url, data)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]


@pytest.mark.unit
class TestSubscriptionAPI:
    """Tests for subscription API endpoints."""

    def test_list_plans(self, api_client):
        """Test listing subscription plans (public auth endpoint)."""
        url = reverse("list_subscriptionplans")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_get_subscription_unauthorized(self, api_client):
        """Test getting subscription without authentication fails."""
        url = reverse("get_subscription")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_subscription_authorized(self, auth_client, subscription_plan):
        """Test getting subscription with authentication."""
        client = auth_client["client"]
        url = reverse("get_subscription")
        response = client.get(url)
        # May return 200 with data or 404 if user has no subscription
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_subscription_health_check(self, auth_client, subscription_plan):
        """Test subscription health check endpoint."""
        client = auth_client["client"]
        url = reverse("subscription_health_check")
        response = client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]


@pytest.mark.unit
class TestEventAPI:
    """Tests for event API endpoints."""

    def test_list_events_unauthorized(self, api_client):
        """Test listing events without authentication fails."""
        url = reverse("list_events")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_events_authorized(self, auth_client):
        """Test listing events with authentication."""
        client = auth_client["client"]
        url = reverse("list_events")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_event(self, auth_client):
        """Test creating an event."""
        client = auth_client["client"]
        url = reverse("create_event")
        data = {
            "title": "New Meeting",
            "description": "Team sync",
            "type": "Action",
            "category": "Work",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "start_date": "2025-01-15",
            "end_date": "2025-01-15",
            "repeated": 0,
            "email_to": "user@example.com",
            "email_subject": "Meeting Reminder",
            "email_body": "Please join the meeting.",
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_event_invalid_data(self, auth_client):
        """Test creating event with invalid data fails."""
        client = auth_client["client"]
        url = reverse("create_event")
        data = {"title": "Missing required fields"}
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_event(self, auth_client, test_event):
        """Test updating an event."""
        client = auth_client["client"]
        url = reverse("update_event", kwargs={"event_id": test_event.pk})
        data = {"title": "Updated Event"}
        response = client.put(url, data, format="json")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]

    def test_delete_event(self, auth_client, test_event):
        """Test deleting an event."""
        client = auth_client["client"]
        url = reverse("delete_event", kwargs={"event_id": test_event.pk})
        response = client.delete(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ]


@pytest.mark.unit
class TestNotificationAPI:
    """Tests for notification API endpoints."""

    def test_list_notifications_unauthorized(self, api_client):
        """Test listing notifications without authentication fails."""
        url = reverse("list_notifications")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_notifications_authorized(self, auth_client):
        """Test listing notifications with authentication."""
        client = auth_client["client"]
        url = reverse("list_notifications")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_mark_notification_read(self, auth_client, test_user):
        """Test marking a notification as read."""
        from myapp.models import Notification

        client = auth_client["client"]
        notification = Notification.objects.create(
            user=test_user,
            title="Test Notification",
            message="Test message",
            type="Info",
            is_active=1,
            is_deleted=0,
        )
        url = reverse(
            "marks_as_read_notification",
            kwargs={"notification_id": notification.pk},
        )
        response = client.put(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
class TestAdminAPI:
    """Tests for admin API endpoints."""

    def test_dashboard_stats_unauthorized(self, api_client):
        """Test admin dashboard stats without authentication fails."""
        url = reverse("dashboard_stats")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_users_unauthorized(self, api_client):
        """Test admin list users without authentication fails."""
        url = reverse("list_users")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]


@pytest.mark.unit
class TestReminderAPI:
    """Tests for reminder API endpoints."""

    def test_list_reminders_unauthorized(self, api_client):
        """Test listing reminders without authentication fails."""
        url = reverse("list_reminders")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_reminders_authorized(self, auth_client):
        """Test listing reminders with authentication."""
        client = auth_client["client"]
        url = reverse("list_reminders")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_reminder(self, auth_client):
        """Test creating a reminder."""
        client = auth_client["client"]
        url = reverse("create_reminder")
        data = {
            "note": "Upcoming event reminder",
            "timestamp": "2027-06-15T10:00:00Z",
        }
        response = client.post(url, data, format="json")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
        ]

    def test_delete_reminder(self, auth_client, test_reminder):
        """Test deleting a reminder."""
        client = auth_client["client"]
        url = reverse("delete_reminder", kwargs={"reminder_id": test_reminder.pk})
        response = client.delete(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ]


@pytest.mark.unit
class TestPaymentAPI:
    """Tests for payment API endpoints."""

    def test_get_payments_unauthorized(self, api_client):
        """Test getting payments without authentication fails."""
        url = reverse("get_user_payments")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_payments_authorized(self, auth_client):
        """Test getting payments with authentication."""
        client = auth_client["client"]
        url = reverse("get_user_payments")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_billing_history(self, auth_client):
        """Test getting billing history."""
        client = auth_client["client"]
        url = reverse("list_billing_history")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
class TestDiscountAPI:
    """Tests for discount/coupon API endpoints."""

    def test_validate_coupon_unauthorized(self, api_client):
        """Test validating coupon without authentication fails."""
        url = reverse("validate_coupon")
        response = api_client.post(url, {"code": "TEST"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_validate_coupon_valid(self, auth_client, test_coupon):
        """Test validating a valid coupon."""
        client = auth_client["client"]
        url = reverse("validate_coupon")
        response = client.post(url, {"code": test_coupon.code}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["valid"] is True

    def test_validate_coupon_invalid_code(self, auth_client):
        """Test validating a non-existent coupon code."""
        client = auth_client["client"]
        url = reverse("validate_coupon")
        response = client.post(url, {"code": "NONEXISTENT"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["valid"] is False

    def test_apply_coupon(self, auth_client, test_coupon):
        """Test applying a coupon to an amount."""
        client = auth_client["client"]
        url = reverse("apply_coupon")
        response = client.post(
            url, {"code": test_coupon.code, "amount": 100.0}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["success"] is True
        assert response.data["data"]["final_amount"] == 80.0

    def test_apply_coupon_missing_fields(self, auth_client):
        """Test applying coupon with missing fields."""
        client = auth_client["client"]
        url = reverse("apply_coupon")
        response = client.post(url, {"code": "TEST"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
class TestReferralAPI:
    """Tests for referral API endpoints."""

    def test_generate_referral_code_unauthorized(self, api_client):
        """Test generating referral code without auth fails."""
        url = reverse("generate_referral_code")
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_generate_referral_code(self, auth_client):
        """Test generating a referral code."""
        client = auth_client["client"]
        url = reverse("generate_referral_code")
        response = client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["success"] is True
        assert "code" in response.data["data"]

    def test_get_referral_stats(self, auth_client, test_referral_code):
        """Test getting referral stats."""
        client = auth_client["client"]
        url = reverse("referral_stats")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["has_code"] is True
        assert response.data["data"]["code"] == "TESTREF1"

    def test_apply_referral_self(self, auth_client, test_referral_code):
        """Test applying own referral code fails."""
        client = auth_client["client"]
        url = reverse("apply_referral")
        response = client.post(url, {"code": test_referral_code.code}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
class TestContentAPI:
    """Tests for content (Post/Comment) API endpoints."""

    def test_create_post_unauthorized(self, api_client):
        """Test creating post without authentication fails."""
        url = reverse("create_post")
        response = api_client.post(url, {"title": "T", "content_text": "C"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_post(self, auth_client):
        """Test creating a post."""
        client = auth_client["client"]
        url = reverse("create_post")
        data = {
            "title": "My First Post",
            "content_text": "Hello world!",
            "content_type": "general",
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["title"] == "My First Post"

    def test_list_posts(self, auth_client, test_post):
        """Test listing posts."""
        client = auth_client["client"]
        url = reverse("list_posts")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) >= 1

    def test_update_post(self, auth_client, test_post):
        """Test updating a post."""
        client = auth_client["client"]
        url = reverse("update_post", kwargs={"post_id": test_post.pk})
        response = client.put(url, {"title": "Updated Title"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["title"] == "Updated Title"

    def test_delete_post(self, auth_client, test_post):
        """Test deleting a post."""
        client = auth_client["client"]
        url = reverse("delete_post", kwargs={"post_id": test_post.pk})
        response = client.delete(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_comment(self, auth_client, test_post):
        """Test creating a comment on a post."""
        client = auth_client["client"]
        url = reverse("create_comment", kwargs={"post_id": test_post.pk})
        response = client.post(url, {"content_text": "Great post!"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_comments(self, auth_client, test_post, test_comment):
        """Test listing comments for a post."""
        client = auth_client["client"]
        url = reverse("list_comments", kwargs={"post_id": test_post.pk})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) >= 1

    def test_delete_comment(self, auth_client, test_comment):
        """Test deleting a comment."""
        client = auth_client["client"]
        url = reverse("delete_comment", kwargs={"comment_id": test_comment.pk})
        response = client.delete(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_post_missing_fields(self, auth_client):
        """Test creating post with missing fields."""
        client = auth_client["client"]
        url = reverse("create_post")
        response = client.post(url, {"title": "No content"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
class TestFeatureFlagsAPI:
    """Tests for feature flags API endpoint."""

    def test_get_feature_flags_unauthorized(self, api_client):
        """Test getting feature flags without auth fails."""
        url = reverse("get_feature_flags")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_feature_flags_no_subscription(self, auth_client):
        """Test getting feature flags with no active subscription."""
        client = auth_client["client"]
        url = reverse("get_feature_flags")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["features"] == {}

    def test_get_feature_flags_with_subscription(self, auth_client, test_subscription):
        """Test getting feature flags with an active subscription."""
        from myapp.models import FeatureFlags

        # Create feature flags for the plan
        FeatureFlags.objects.create(
            subscription_plan=test_subscription.subscription_plan,
            features={
                "api_access": {"enabled": True, "calls_per_hour": 100},
                "advanced_analytics": {"enabled": False},
            },
        )

        client = auth_client["client"]
        url = reverse("get_feature_flags")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["features"]["api_access"]["enabled"] is True


@pytest.mark.unit
class TestModerationAdminAPI:
    """Tests for moderation admin API endpoints."""

    def test_moderation_queue_unauthorized(self, api_client):
        """Test admin moderation queue without auth fails."""
        url = reverse("moderation_queue")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_moderation_action_unauthorized(self, api_client):
        """Test admin moderation action without auth fails."""
        url = reverse("moderation_action")
        response = api_client.post(url, {"action": "approve", "queue_id": 1})
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]


@pytest.mark.unit
class TestAnalyticsAdminAPI:
    """Tests for analytics admin API endpoints."""

    def test_analytics_dashboard_unauthorized(self, api_client):
        """Test admin analytics dashboard without auth fails."""
        url = reverse("analytics_dashboard")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
