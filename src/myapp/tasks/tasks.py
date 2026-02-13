import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_task(
    self, user_id: int, title: str, message: str, channels: list | None = None
):
    """
    Async task to send notifications via configured channels.

    Args:
        user_id: Target user ID
        title: Notification title
        message: Notification body
        channels: List of channels (email, sms, push). Defaults to user prefs.
    """
    try:
        from myapp.models import User
        from myapp.services.notification_service import NotificationService

        user = User.objects.get(user_id=user_id)
        service = NotificationService()
        results = service.send_notification(
            user=user, title=title, message=message, channels=channels
        )
        logger.info(f"Notification sent to user {user_id}: {results}")
        return results
    except Exception as exc:
        logger.error(f"Error sending notification to user {user_id}: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task
def auto_renew_subscriptions_task():
    """
    Periodic task to auto-renew expiring subscriptions.

    Finds all active subscriptions expiring within 24h that have
    auto_renew enabled and processes renewal.
    """
    try:
        from myapp.models import Subscription
        from myapp.services.subscription_service import SubscriptionService

        now = timezone.now()
        expiring_soon = Subscription.objects.filter(
            status="Active",
            end_date__lte=now + timedelta(hours=24),
            end_date__gt=now,
            is_deleted=0,
        )

        renewed = 0
        failed = 0
        for sub in expiring_soon:
            try:
                result = SubscriptionService.renew_subscription(sub.subscription_id)
                if result.get("success"):
                    renewed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to renew subscription {sub.subscription_id}: {e}")
                failed += 1

        logger.info(f"Auto-renew complete: {renewed} renewed, {failed} failed")
        return {"renewed": renewed, "failed": failed}
    except Exception as e:
        logger.error(f"Error in auto_renew_subscriptions_task: {e}")
        return {"error": str(e)}


@shared_task
def aggregate_monthly_analytics_task(year: int | None = None, month: int | None = None):
    """
    Periodic task to aggregate monthly analytics data.

    Args:
        year: Year to aggregate (defaults to current)
        month: Month to aggregate (defaults to current)
    """
    try:
        from myapp.services.analytics_service import AnalyticsService

        now = timezone.now()
        year = year or now.year
        month = month or now.month

        AnalyticsService.aggregate_monthly_data(year, month)
        logger.info(f"Monthly analytics aggregated for {year}-{month:02d}")
        return {"year": year, "month": month, "status": "completed"}
    except Exception as e:
        logger.error(f"Error aggregating monthly analytics: {e}")
        return {"error": str(e)}


@shared_task
def cleanup_old_records_task(days: int = 90):
    """
    Periodic task to clean up old soft-deleted records.

    Permanently removes records that have been soft-deleted for more
    than the specified number of days.

    Args:
        days: Number of days after soft-delete before permanent removal (default: 90)
    """
    try:
        from myapp.models import (
            ActivityLog,
            Comment,
            Event,
            Notification,
            Post,
            Reminder,
        )

        cutoff = timezone.now() - timedelta(days=days)
        total_deleted = 0

        # Clean up old soft-deleted records across models
        models_to_clean = [
            (Notification, "notification_id"),
            (Event, "event_id"),
            (Reminder, "reminder_id"),
            (Post, "post_id"),
            (Comment, "comment_id"),
        ]

        for model, _pk_field in models_to_clean:
            count = model.objects.filter(
                is_deleted=1,
                updated_at__lt=cutoff,
            ).delete()[0]
            total_deleted += count
            if count:
                logger.info(f"Cleaned up {count} old {model.__name__} records")

        # Clean up old activity logs (keep 90 days)
        log_count = ActivityLog.objects.filter(
            created_at__lt=cutoff,
        ).delete()[0]
        total_deleted += log_count

        logger.info(f"Cleanup complete: {total_deleted} records removed")
        return {"total_deleted": total_deleted}
    except Exception as e:
        logger.error(f"Error in cleanup_old_records_task: {e}")
        return {"error": str(e)}


@shared_task
def send_event_reminders_task():
    """
    Periodic task to send reminders for upcoming events.

    Finds events happening within the next 24 hours that have
    reminders set and sends notifications.
    """
    try:
        from myapp.models import Reminder

        now = timezone.now()
        upcoming_window = now + timedelta(hours=24)

        pending_reminders = Reminder.objects.filter(
            timestamp__gte=now,
            timestamp__lte=upcoming_window,
            is_active=1,
            is_deleted=0,
        ).select_related("user")

        sent = 0
        for reminder in pending_reminders:
            try:
                user = reminder.user
                if not user:
                    continue

                # Queue notification asynchronously
                send_notification_task.delay(
                    user_id=user.user_id,
                    title="Reminder",
                    message=f"Reminder: {reminder.note[:100] if reminder.note else 'You have a reminder'}",
                    channels=["email"],
                )
                sent += 1
            except Exception as e:
                logger.error(f"Error sending reminder {reminder.reminder_id}: {e}")

        logger.info(f"Event reminders: {sent} notifications queued")
        return {"reminders_sent": sent}
    except Exception as e:
        logger.error(f"Error in send_event_reminders_task: {e}")
        return {"error": str(e)}
