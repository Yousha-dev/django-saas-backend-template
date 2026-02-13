# myapp/models/discount.py
"""
Discount and coupon models.

Provides:
- Coupon: Configurable discount coupons for subscription pricing
"""

from django.db import models
from django.utils import timezone

from .base import BaseModel
from .choices import DiscountType


class Coupon(BaseModel):
    """
    Discount coupons for subscription plans.

    Supports:
    - Percentage or fixed amount discounts
    - Usage limits (max total uses, per user)
    - Date-based validity
    - Plan-specific restrictions
    - Minimum purchase requirements
    """

    coupon_id = models.AutoField(
        db_column="CouponID",
        primary_key=True,
        help_text="Unique identifier for the coupon",
    )
    code = models.CharField(
        db_column="Code",
        max_length=50,
        unique=True,
        help_text="Unique coupon code (e.g., WELCOME20)",
    )
    description = models.TextField(
        db_column="Description",
        blank=True,
        default="",
        help_text="Human-readable description of the coupon",
    )
    discount_type = models.CharField(
        db_column="DiscountType",
        max_length=12,
        choices=DiscountType.choices(),
        help_text="Type of discount: percentage or fixed amount",
    )
    discount_value = models.DecimalField(
        db_column="DiscountValue",
        max_digits=10,
        decimal_places=2,
        help_text="Discount amount (percentage 0-100 or fixed dollar amount)",
    )
    max_uses = models.IntegerField(
        db_column="MaxUses",
        default=0,
        help_text="Maximum total uses (0 = unlimited)",
    )
    current_uses = models.IntegerField(
        db_column="CurrentUses",
        default=0,
        help_text="Number of times this coupon has been used",
    )
    max_uses_per_user = models.IntegerField(
        db_column="MaxUsesPerUser",
        default=1,
        help_text="Maximum uses per user (0 = unlimited)",
    )
    valid_from = models.DateTimeField(
        db_column="ValidFrom",
        help_text="When the coupon becomes valid",
    )
    valid_until = models.DateTimeField(
        db_column="ValidUntil",
        help_text="When the coupon expires",
    )
    applicable_plans = models.ManyToManyField(
        "SubscriptionPlan",
        blank=True,
        related_name="coupons",
        help_text="Plans this coupon applies to (empty = all plans)",
    )
    min_purchase_amount = models.DecimalField(
        db_column="MinPurchaseAmount",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum purchase amount required to use this coupon",
    )
    first_purchase_only = models.BooleanField(
        db_column="FirstPurchaseOnly",
        default=False,
        help_text="Whether this coupon is only valid for first-time purchases",
    )

    class Meta:
        managed = True
        db_table = "Coupons"
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"
        indexes = [
            models.Index(fields=["code", "is_active"]),
            models.Index(fields=["valid_from", "valid_until"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        if self.discount_type == DiscountType.PERCENTAGE.value:
            return f"{self.code}: {self.discount_value}% off"
        return f"{self.code}: ${self.discount_value} off"

    @property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid."""
        now = timezone.now()
        return (
            self.is_active == 1
            and self.is_deleted == 0
            and self.valid_from <= now <= self.valid_until
            and (self.max_uses == 0 or self.current_uses < self.max_uses)
        )

    def can_be_used_by(self, user_id: int) -> bool:
        """Check if a specific user can use this coupon."""
        if not self.is_valid:
            return False

        if self.max_uses_per_user == 0:
            return True

        # Check per-user usage via CouponUsage
        usage_count = CouponUsage.objects.filter(
            coupon=self,
            user_id=user_id,
            is_deleted=0,
        ).count()

        return usage_count < self.max_uses_per_user

    def apply(self):
        """Increment usage count."""
        self.current_uses += 1
        self.save(update_fields=["current_uses", "updated_at"])


class CouponUsage(BaseModel):
    """
    Tracks individual coupon usage per user.

    Used to enforce per-user usage limits and audit trail.
    """

    usage_id = models.AutoField(
        db_column="UsageID",
        primary_key=True,
        help_text="Unique identifier for the usage record",
    )
    coupon = models.ForeignKey(
        Coupon,
        models.CASCADE,
        db_column="CouponID",
        related_name="usages",
        help_text="Coupon that was used",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="UserID",
        related_name="coupon_usages",
        help_text="User who used the coupon",
    )
    discount_applied = models.DecimalField(
        db_column="DiscountApplied",
        max_digits=10,
        decimal_places=2,
        help_text="Actual discount amount applied",
    )
    original_amount = models.DecimalField(
        db_column="OriginalAmount",
        max_digits=10,
        decimal_places=2,
        help_text="Original amount before discount",
    )
    final_amount = models.DecimalField(
        db_column="FinalAmount",
        max_digits=10,
        decimal_places=2,
        help_text="Final amount after discount",
    )

    class Meta:
        managed = True
        db_table = "CouponUsages"
        verbose_name = "Coupon Usage"
        verbose_name_plural = "Coupon Usages"
        indexes = [
            models.Index(fields=["coupon", "user"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"Usage of {self.coupon.code} by User #{self.user_id}"
