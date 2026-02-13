# myapp/models/__init__.py
"""
Models package for the myapp application.

Models are organized by domain for better maintainability:
- Base model classes and mixins
- User and authentication models
- Subscription and billing models
- Event and reminder models
- Analytics models
- Logging models
"""

from .analytics import MonthlyAnalytics
from .base import ActiveModel, BaseModel, SoftDeleteModel, TimeStampedModel
from .choices import (
    AppealStatus,
    BillingFrequency,
    ContentStatus,
    DiscountType,
    EventCategory,
    EventFrequency,
    EventType,
    ModerationStatus,
    NotificationType,
    PaymentMethod,
    PaymentStatus,
    ReferralRewardType,
    SubscriptionStatus,
)
from .content import Comment, ModeratableContent, Post
from .discount import Coupon, CouponUsage
from .event import Event, Reminder
from .features import FeatureDefinition, FeatureFlags
from .logging import ActivityLog, AuditLog
from .moderation import ModerationAppeal, ModerationQueue
from .notification import Notification
from .referral import ReferralCode, ReferralTransaction
from .subscription import Payment, Renewal, Subscription, SubscriptionPlan
from .user import Role, User, UserManager

__all__ = [
    "ActiveModel",
    "ActivityLog",
    "AppealStatus",
    "AuditLog",
    # Base models
    "BaseModel",
    # Choices/Enums
    "BillingFrequency",
    "Comment",
    "ContentStatus",
    # Discount & Referral
    "Coupon",
    "CouponUsage",
    "DiscountType",
    "Event",
    "EventCategory",
    "EventFrequency",
    "EventType",
    "FeatureDefinition",
    # Feature flags
    "FeatureFlags",
    # Content & Moderation
    "ModeratableContent",
    "ModerationAppeal",
    "ModerationQueue",
    "ModerationStatus",
    "MonthlyAnalytics",
    "Notification",
    "NotificationType",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Post",
    "ReferralCode",
    "ReferralRewardType",
    "ReferralTransaction",
    "Reminder",
    "Renewal",
    # Domain models
    "Role",
    "SoftDeleteModel",
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "TimeStampedModel",
    "User",
    "UserManager",
]
