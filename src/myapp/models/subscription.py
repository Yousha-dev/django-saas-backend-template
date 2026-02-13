# myapp/models/subscription.py
"""
Subscription and billing-related models.

This module contains:
- SubscriptionPlan: Available subscription tiers
- Subscription: User's active subscription
- Payment: Payment records
- Renewal: Subscription renewal history
"""

from django.core.exceptions import ValidationError
from django.db import models

from .base import BaseModel
from .choices import BillingFrequency, PaymentMethod, PaymentStatus, SubscriptionStatus


class SubscriptionPlan(BaseModel):
    """
    Subscription plan definitions with pricing and features.

    Defines the available subscription tiers with their:
    - Pricing (monthly and yearly)
    - API limits
    - Feature flags
    """

    subscription_plan_id = models.AutoField(
        db_column="SubscriptionPlanID",
        primary_key=True,
        help_text="Unique identifier for the subscription plan",
    )
    name = models.CharField(
        db_column="Name",
        max_length=255,
        help_text="Plan name (e.g., 'Basic', 'Pro', 'Enterprise')",
    )
    description = models.TextField(
        db_column="Description",
        blank=True,
        null=True,
        help_text="Detailed description of the plan",
    )
    monthly_price = models.DecimalField(
        db_column="MonthlyPrice",
        max_digits=10,
        decimal_places=2,
        help_text="Monthly price in USD",
    )
    yearly_price = models.DecimalField(
        db_column="YearlyPrice",
        max_digits=10,
        decimal_places=2,
        help_text="Yearly price in USD",
    )
    max_operations = models.IntegerField(
        db_column="MaxExchanges",
        default=1,
        help_text="Maximum number of operations allowed per period",
    )
    max_api_calls_per_hour = models.IntegerField(
        db_column="MaxAPICallsPerHour",
        default=100,
        help_text="Maximum API calls allowed per hour",
    )
    feature_details = models.TextField(
        db_column="FeatureDetails",
        help_text="Detailed list of features included in the plan",
    )

    class Meta:
        managed = True
        db_table = "SubscriptionPlans"
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"
        ordering = ["monthly_price"]
        app_label = "myapp"

    def __str__(self):
        return f"{self.name} (${self.monthly_price}/month)"


class Subscription(BaseModel):
    """
    User subscription records.

    Tracks:
    - User's current subscription plan
    - Billing frequency and status
    - Renewal history
    """

    subscription_id = models.AutoField(
        db_column="SubscriptionID",
        primary_key=True,
        help_text="Unique identifier for the subscription",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User who owns this subscription",
    )
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        models.PROTECT,
        db_column="SubscriptionPlanID",
        blank=True,
        null=True,
        help_text="The subscription plan",
    )
    billing_frequency = models.CharField(
        db_column="BillingFrequency",
        max_length=13,
        choices=BillingFrequency.choices(),
        help_text="How often the user is billed",
    )
    start_date = models.DateField(
        db_column="StartDate",
        help_text="When the subscription started",
    )
    end_date = models.DateField(
        db_column="EndDate",
        help_text="When the subscription expires or renews",
    )
    auto_renew = models.IntegerField(
        db_column="AutoRenew",
        help_text="Whether subscription auto-renews (1=yes, 0=no)",
    )
    status = models.CharField(
        db_column="Status",
        max_length=14,
        choices=SubscriptionStatus.choices(),
        help_text="Current subscription status",
    )
    renewal_count = models.IntegerField(
        db_column="RenewalCount",
        blank=True,
        null=True,
        help_text="Number of times this subscription has been renewed",
    )
    last_renewed_at = models.DateTimeField(
        db_column="LastRenewedAt",
        blank=True,
        null=True,
        help_text="Timestamp of last renewal",
    )
    provider_subscription_id = models.CharField(
        db_column="ProviderSubscriptionID",
        max_length=255,
        blank=True,
        null=True,
        help_text="External subscription ID from the payment provider (Stripe, PayPal, etc.)",
    )

    class Meta:
        managed = True
        db_table = "Subscriptions"
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["end_date", "status"]),
            models.Index(fields=["status", "auto_renew"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"{self.user} - {self.subscription_plan} ({self.status})"

    def clean(self):
        """Validate subscription data."""
        if self.billing_frequency not in dict(BillingFrequency.choices()):
            raise ValidationError(
                {"billing_frequency": "Invalid billing frequency selected."}
            )
        if self.status not in dict(SubscriptionStatus.choices()):
            raise ValidationError({"status": "Invalid subscription status selected."})

    def is_active_subscription(self) -> bool:
        """Check if subscription is in an active state."""
        return self.status in SubscriptionStatus.active_statuses()

    def days_until_expiry(self) -> int:
        """Calculate days until subscription expires."""
        from datetime import date

        if self.end_date and self.status == SubscriptionStatus.ACTIVE.value:
            delta = self.end_date - date.today()
            return max(0, delta.days)
        return 0


class Payment(BaseModel):
    """
    Payment records for subscriptions.

    Tracks:
    - Payment amounts and methods
    - Payment status and response data
    - Links to subscriptions
    """

    payment_id = models.AutoField(
        db_column="PaymentID",
        primary_key=True,
        help_text="Unique identifier for the payment",
    )
    subscription = models.ForeignKey(
        Subscription,
        models.CASCADE,
        db_column="SubscriptionID",
        blank=True,
        null=True,
        help_text="Subscription this payment is for",
    )
    user = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User who made this payment",
    )
    amount = models.DecimalField(
        db_column="Amount",
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in USD",
    )
    payment_date = models.DateField(
        db_column="PaymentDate",
        help_text="When the payment was processed",
    )
    payment_method = models.CharField(
        db_column="PaymentMethod",
        max_length=50,
        choices=PaymentMethod.choices(),
        blank=True,
        null=True,
        help_text="Method used for payment",
    )
    reference_number = models.CharField(
        db_column="ReferenceNumber",
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction reference from payment processor",
    )
    status = models.CharField(
        db_column="Status",
        max_length=20,
        choices=PaymentStatus.choices(),
        blank=True,
        null=True,
        help_text="Payment processing status",
    )
    payment_response = models.TextField(
        db_column="PaymentResponse",
        blank=True,
        null=True,
        help_text="Full response from payment processor",
    )

    class Meta:
        managed = True
        db_table = "Payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [
            models.Index(fields=["subscription", "payment_date"]),
            models.Index(fields=["status", "payment_date"]),
        ]
        ordering = ["-payment_date"]
        app_label = "myapp"

    def __str__(self):
        return f"Payment ${self.amount} - {self.status}"

    def clean(self):
        """Validate payment data."""
        if self.payment_method and self.payment_method not in dict(
            PaymentMethod.choices()
        ):
            raise ValidationError(
                {"payment_method": "Invalid payment method selected."}
            )
        if self.status and self.status not in dict(PaymentStatus.choices()):
            raise ValidationError({"status": "Invalid payment status selected."})

    def is_completed(self) -> bool:
        """Check if payment was successful."""
        return self.status == PaymentStatus.COMPLETED.value


class Renewal(BaseModel):
    """
    Subscription renewal records.

    Tracks subscription renewals with:
    - Renewal date and cost
    - User who performed the renewal
    - Additional notes
    """

    renewal_id = models.AutoField(
        db_column="RenewalID",
        primary_key=True,
        help_text="Unique identifier for the renewal",
    )
    subscription = models.ForeignKey(
        Subscription,
        models.CASCADE,
        db_column="SubscriptionID",
        blank=True,
        null=True,
        help_text="Subscription that was renewed",
    )
    renewed_by = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="RenewedBy",
        blank=True,
        null=True,
        help_text="User who processed the renewal",
    )
    renewal_date = models.DateTimeField(
        db_column="RenewalDate",
        blank=True,
        null=True,
        help_text="When the renewal occurred",
    )
    renewal_cost = models.DecimalField(
        db_column="RenewalCost",
        max_digits=10,
        decimal_places=2,
        help_text="Cost of the renewal",
    )
    notes = models.TextField(
        db_column="Notes",
        blank=True,
        null=True,
        help_text="Additional notes about the renewal",
    )

    class Meta:
        managed = True
        db_table = "Renewals"
        verbose_name = "Renewal"
        verbose_name_plural = "Renewals"
        ordering = ["-renewal_date"]
        app_label = "myapp"

    def __str__(self):
        return f"Renewal for {self.subscription} - ${self.renewal_cost}"
