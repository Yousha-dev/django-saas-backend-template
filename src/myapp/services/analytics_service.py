from datetime import datetime

from django.db.models import Sum
from django.utils import timezone

from myapp.models import MonthlyAnalytics, Payment, Subscription, User


class AnalyticsService:
    """
    Service for aggregating and retrieving analytics data.
    """

    @staticmethod
    def aggregate_monthly_data(year: int, month: int):
        """
        Aggregate data for a specific month and update MonthlyAnalytics model.
        """
        # Define date range
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Count new subscriptions
        new_subs = Subscription.objects.filter(
            created_at__gte=start_date, created_at__lt=end_date, is_active=1
        ).count()

        # Count cancellations
        cancelled = Subscription.objects.filter(
            status="Cancelled", updated_at__gte=start_date, updated_at__lt=end_date
        ).count()

        # Count renewals (mock logic: payments on existing subscriptions - new subs)
        # Better logic would track renewal events specifically
        total_payments_count = Payment.objects.filter(
            payment_date__gte=start_date, payment_date__lt=end_date, status="Completed"
        ).count()
        renewals = max(0, total_payments_count - new_subs)

        # Revenue
        revenue = (
            Payment.objects.filter(
                payment_date__gte=start_date,
                payment_date__lt=end_date,
                status="Completed",
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )

        # Update or Create Analytics Record
        MonthlyAnalytics.objects.update_or_create(
            year=year,
            month=month,
            defaults={
                "new_subscriptions": new_subs,
                "cancellations": cancelled,
                "renewals": renewals,
                "total_payments": revenue,
            },
        )
        return True

    @staticmethod
    def get_dashboard_stats():
        """
        Get high-level stats for the admin dashboard.
        """
        now = timezone.now()
        current_month = now.month
        current_year = now.year

        # Aggregate current month if not ready
        AnalyticsService.aggregate_monthly_data(current_year, current_month)

        try:
            current_analytics = MonthlyAnalytics.objects.get(
                year=current_year, month=current_month
            )
            revenue = current_analytics.total_payments
            new_users = current_analytics.new_subscriptions
        except MonthlyAnalytics.DoesNotExist:
            revenue = 0
            new_users = 0

        # Total active users
        total_users = User.objects.filter(is_active=1).count()
        active_subscriptions = Subscription.objects.filter(status="Active").count()

        return {
            "mrr": revenue,  # Monthly Recurring Revenue (approx)
            "active_subscribers": active_subscriptions,
            "total_users": total_users,
            "new_users_this_month": new_users,
        }
