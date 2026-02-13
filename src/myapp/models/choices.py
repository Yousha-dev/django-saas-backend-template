# myapp/models/choices.py
"""
Choice field definitions for model enums and dropdowns.

Centralized choice definitions make it easier to:
- Maintain consistent values across models
- Add new options in one place
- Document valid choices
"""

from collections.abc import Sequence as SequenceType
from enum import Enum


class BillingFrequency(str, Enum):
    """Billing frequency options for subscriptions."""

    MONTHLY = "Monthly"
    YEARLY = "Yearly"
    WEEKLY = "Weekly"
    SEMI_ANNUALLY = "Semi-Annually"
    QUARTERLY = "Quarterly"
    ONE_TIME = "One-Time"
    OTHER = "Other"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ")) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class SubscriptionStatus(str, Enum):
    """Status options for subscriptions."""

    ACTIVE = "Active"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"
    PENDING = "Pending"
    SUSPENDED = "Suspended"
    RENEWAL_PENDING = "RenewalPending"
    TRIAL = "Trial"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ")) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]

    @classmethod
    def active_statuses(cls) -> list[str]:
        """Return statuses considered 'active' for API access."""
        return [cls.ACTIVE.value, cls.TRIAL.value]


class PaymentStatus(str, Enum):
    """Status options for payments."""

    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    REFUNDED = "Refunded"
    PARTIALLY_REFUNDED = "Partial"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class PaymentMethod(str, Enum):
    """Payment method options."""

    CREDIT_CARD = "CreditCard"
    DEBIT_CARD = "DebitCard"
    PAYPAL = "PayPal"
    BANK_TRANSFER = "BankTransfer"
    CRYPTO = "Crypto"
    APPLE_PAY = "ApplePay"
    GOOGLE_PAY = "GooglePay"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ")) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class NotificationType(str, Enum):
    """Types of notifications."""

    EXPIRY = "Expiry"
    RENEWAL = "Renewal"
    SYSTEM = "System"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class EventType(str, Enum):
    """Types of events."""

    ACTION = "Action"
    REMINDER = "Reminder"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class EventCategory(str, Enum):
    """Categories for events."""

    PERSONAL = "Personal"
    WORK = "Work"
    BIRTHDAY = "Birthday"
    DEADLINE = "Deadline"
    OTHER = "Other"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class EventFrequency(str, Enum):
    """Frequency options for recurring events."""

    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    YEARLY = "Yearly"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class ModerationStatus(str, Enum):
    """Status options for moderation queue items."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELETED = "deleted"
    CHANGES_REQUESTED = "changes_requested"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ").title()) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class ContentStatus(str, Enum):
    """Status options for moderatable content."""

    DRAFT = "draft"
    PUBLISHED = "published"
    FLAGGED = "flagged"
    REMOVED = "removed"
    UNDER_REVIEW = "under_review"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ").title()) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class AppealStatus(str, Enum):
    """Status options for moderation appeals."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class DiscountType(str, Enum):
    """Discount type options for coupons."""

    PERCENTAGE = "percentage"
    FIXED = "fixed"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]


class ReferralRewardType(str, Enum):
    """Reward type options for referral programs."""

    CREDIT = "credit"
    DISCOUNT = "discount"
    FREE_MONTH = "free_month"
    FEATURE_UNLOCK = "feature_unlock"

    @classmethod
    def choices(cls) -> SequenceType[tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ").title()) for item in cls]

    @classmethod
    def values(cls) -> SequenceType[str]:
        return [item.value for item in cls]
