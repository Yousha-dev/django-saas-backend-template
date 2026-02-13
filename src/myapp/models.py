# myapp/models.py
"""
Refactored models module with modular structure.

The actual models are organized in:
    myapp/models/base.py          - Base model classes
    myapp/models/choices.py       - Choice definitions
    myapp/models/user.py          - User model
    myapp/models/subscription.py   - Subscription, Payment, Renewal
    myapp/models/event.py          - Event, Reminder
    myapp/models/analytics.py      - MonthlyAnalytics
    myapp/models/logging.py        - ActivityLog, AuditLog
    myapp/models/notification.py    - Notification
"""

# Import all models from the modular package
# Django's built-in managed=False models for auth tables
from django.db import models

from myapp.models import *


class AuthGroup(models.Model):
    """Proxy for Django's auth_group table."""

    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = "auth_group"


class AuthGroupPermissions(models.Model):
    """Proxy for Django's auth_group_permissions table."""

    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey("AuthPermission", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "auth_group_permissions"
        unique_together = (("group", "permission"),)


class AuthPermission(models.Model):
    """Proxy for Django's auth_permission table."""

    name = models.CharField(max_length=255)
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "auth_permission"
        unique_together = (("content_type", "codename"),)


class AuthUser(models.Model):
    """Proxy for Django's auth_user table."""

    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "auth_user"


class AuthUserGroups(models.Model):
    """Proxy for Django's auth_user_groups table."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "auth_user_groups"
        unique_together = (("user", "group"),)


class AuthUserUserPermissions(models.Model):
    """Proxy for Django's auth_user_user_permissions table."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "auth_user_user_permissions"
        unique_together = (("user", "permission"),)


class DjangoAdminLog(models.Model):
    """Proxy for Django's django_admin_log table."""

    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey(
        "DjangoContentType", models.DO_NOTHING, blank=True, null=True
    )
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "django_admin_log"


class DjangoContentType(models.Model):
    """Proxy for Django's django_content_type table."""

    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "django_content_type"
        unique_together = (("app_label", "model"),)


class DjangoMigrations(models.Model):
    """Proxy for Django's django_migrations table."""

    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "django_migrations"


class DjangoSession(models.Model):
    """Proxy for Django's django_session table."""

    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "django_session"


__all__ = [
    "ActiveModel",
    "ActivityLog",
    "AuditLog",
    # Django auth proxies
    "AuthGroup",
    "AuthGroupPermissions",
    "AuthPermission",
    "AuthUser",
    "AuthUserGroups",
    "AuthUserUserPermissions",
    # Base models
    "BaseModel",
    # Choices
    "BillingFrequency",
    "DjangoAdminLog",
    "DjangoContentType",
    "DjangoMigrations",
    "DjangoSession",
    "Event",
    "EventCategory",
    "EventFrequency",
    "EventType",
    "MonthlyAnalytics",
    "Notification",
    "NotificationType",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Reminder",
    "Renewal",
    "SoftDeleteModel",
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "TimeStampedModel",
    # Domain models
    "User",
]
