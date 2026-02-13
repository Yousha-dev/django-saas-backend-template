# myapp/models/referral.py
"""
Referral program models.

Provides:
- ReferralCode: Unique referral codes for users to share
- ReferralTransaction: Records of successful referrals and rewards
"""

from django.db import models
from django.utils import timezone

from .base import BaseModel
from .choices import ReferralRewardType


class ReferralCode(BaseModel):
    """
    Referral codes used for user referral programs.

    Each user can have a unique referral code that they share
    with potential new users to earn rewards.
    """

    referral_code_id = models.AutoField(
        db_column="ReferralCodeID",
        primary_key=True,
        help_text="Unique identifier for the referral code",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="UserID",
        related_name="referral_codes",
        help_text="User who owns this referral code",
    )
    code = models.CharField(
        db_column="Code",
        max_length=20,
        unique=True,
        help_text="Unique referral code string",
    )
    max_uses = models.IntegerField(
        db_column="MaxUses",
        default=0,
        help_text="Maximum times this code can be used (0 = unlimited)",
    )
    current_uses = models.IntegerField(
        db_column="CurrentUses",
        default=0,
        help_text="Number of times this code has been used",
    )
    reward_type = models.CharField(
        db_column="RewardType",
        max_length=20,
        choices=ReferralRewardType.choices(),
        default=ReferralRewardType.CREDIT.value,
        help_text="Type of reward given for successful referral",
    )
    reward_amount = models.DecimalField(
        db_column="RewardAmount",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Amount of reward ($ for credit, % for discount, days for free month)",
    )
    expires_at = models.DateTimeField(
        db_column="ExpiresAt",
        blank=True,
        null=True,
        help_text="When this referral code expires (null = never)",
    )

    class Meta:
        managed = True
        db_table = "ReferralCodes"
        verbose_name = "Referral Code"
        verbose_name_plural = "Referral Codes"
        indexes = [
            models.Index(fields=["code", "is_active"]),
            models.Index(fields=["user", "is_active"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"Referral {self.code} (User #{self.user_id})"

    @property
    def is_valid(self) -> bool:
        """Check if referral code is still usable."""
        now = timezone.now()
        return (
            self.is_active == 1
            and self.is_deleted == 0
            and (self.max_uses == 0 or self.current_uses < self.max_uses)
            and (self.expires_at is None or self.expires_at > now)
        )

    def use(self):
        """Increment usage counter."""
        self.current_uses += 1
        self.save(update_fields=["current_uses", "updated_at"])


class ReferralTransaction(BaseModel):
    """
    Records of successful referral transactions.

    Tracks when a referred user completes registration/subscription
    and whether rewards have been distributed.
    """

    transaction_id = models.AutoField(
        db_column="TransactionID",
        primary_key=True,
        help_text="Unique identifier for the referral transaction",
    )
    referral_code = models.ForeignKey(
        ReferralCode,
        models.CASCADE,
        db_column="ReferralCodeID",
        related_name="transactions",
        help_text="Referral code that was used",
    )
    referred_user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="ReferredUserID",
        related_name="referred_by_transactions",
        help_text="New user who was referred",
    )
    referrer_rewarded = models.BooleanField(
        db_column="ReferrerRewarded",
        default=False,
        help_text="Whether the referrer has received their reward",
    )
    referred_rewarded = models.BooleanField(
        db_column="ReferredRewarded",
        default=False,
        help_text="Whether the referred user has received their reward",
    )
    referrer_reward_amount = models.DecimalField(
        db_column="ReferrerRewardAmount",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Reward amount given to referrer",
    )
    referred_reward_amount = models.DecimalField(
        db_column="ReferredRewardAmount",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Reward amount given to referred user",
    )

    class Meta:
        managed = True
        db_table = "ReferralTransactions"
        verbose_name = "Referral Transaction"
        verbose_name_plural = "Referral Transactions"
        indexes = [
            models.Index(fields=["referral_code", "created_at"]),
            models.Index(fields=["referred_user"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"Referral TX #{self.transaction_id}: {self.referral_code.code} → User #{self.referred_user_id}"
