# myapp/models/notification.py
"""
Notification models for user alerts.

This module contains:
- Notification: User notifications and alerts
"""

from django.core.exceptions import ValidationError
from django.db import models

from .base import BaseModel
from .choices import NotificationType


class Notification(BaseModel):
    """
    User notification model for in-app alerts.

    Handles:
    - Subscription expiry notifications
    - Renewal reminders
    - System announcements
    """

    notification_id = models.AutoField(
        db_column="NotificationID",
        primary_key=True,
        help_text="Unique identifier for the notification",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User who should receive this notification",
    )
    title = models.TextField(
        db_column="Title",
        help_text="Notification title or headline",
    )
    message = models.TextField(
        db_column="Message",
        help_text="Full notification message content",
    )
    type = models.CharField(
        db_column="Type",
        max_length=7,
        choices=NotificationType.choices(),
        help_text="Notification category type",
    )
    is_read = models.IntegerField(
        db_column="IsRead",
        blank=True,
        null=True,
        help_text="Whether user has read this notification (1=yes, 0=no)",
    )

    class Meta:
        managed = True
        db_table = "Notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["type", "created_at"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"{self.type}: {self.title}"

    def clean(self):
        """Validate notification data."""
        if self.type and self.type not in dict(NotificationType.choices()):
            raise ValidationError({"type": "Invalid notification type selected."})

    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = 1
        self.save(update_fields=["is_read"])

    def mark_as_unread(self):
        """Mark notification as unread."""
        self.is_read = 0
        self.save(update_fields=["is_read"])
