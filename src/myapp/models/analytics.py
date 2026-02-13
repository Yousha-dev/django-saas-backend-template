# myapp/models/analytics.py
"""
Analytics and reporting models.

This module contains:
- MonthlyAnalytics: Monthly subscription and payment metrics
"""

from django.db import models

from .base import BaseModel


class MonthlyAnalytics(BaseModel):
    """
    Monthly analytics aggregation for business metrics.

    Tracks:
    - Subscription renewals and cancellations
    - New subscriptions
    - Total payment amounts
    """

    analytics_id = models.AutoField(
        db_column="AnalyticsID",
        primary_key=True,
        help_text="Unique identifier for the analytics record",
    )
    user = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User for whom analytics are tracked (optional)",
    )
    year = models.IntegerField(
        db_column="Year",
        help_text="Calendar year for the analytics",
    )
    month = models.IntegerField(
        db_column="Month",
        help_text="Calendar month (1-12) for the analytics",
    )
    renewals = models.IntegerField(
        db_column="Renewals",
        blank=True,
        null=True,
        help_text="Count of subscription renewals in the period",
    )
    cancellations = models.IntegerField(
        db_column="Cancellations",
        blank=True,
        null=True,
        help_text="Count of subscription cancellations in the period",
    )
    new_subscriptions = models.IntegerField(
        db_column="NewSubscriptions",
        blank=True,
        null=True,
        help_text="Count of new subscriptions in the period",
    )
    total_payments = models.DecimalField(
        db_column="TotalPayments",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Total payment amount received in the period",
    )

    class Meta:
        managed = True
        db_table = "MonthlyAnalytics"
        verbose_name = "Monthly Analytics"
        verbose_name_plural = "Monthly Analytics"
        ordering = ["-year", "-month"]
        unique_together = [["year", "month"]]
        app_label = "myapp"

    def __str__(self):
        return f"Analytics for {self.year}-{self.month:02d}"

    @property
    def period(self) -> str:
        """Return formatted period string."""
        return f"{self.year}-{self.month:02d}"

    @property
    def total_changes(self) -> int:
        """Calculate total subscription changes."""
        return (
            (self.new_subscriptions or 0)
            + (self.renewals or 0)
            - (self.cancellations or 0)
        )
