# myapp/models/event.py
"""
Event and reminder-related models.

This module contains:
- Event: Calendar events and scheduling
- Reminder: User reminders and notifications
"""

from django.core.exceptions import ValidationError
from django.db import models

from .base import BaseModel
from .choices import EventCategory, EventFrequency, EventType


class Event(BaseModel):
    """
    Calendar event model for scheduling and reminders.

    Supports:
    - One-time and recurring events
    - Multiple event types and categories
    - Email notifications for events
    """

    event_id = models.AutoField(
        db_column="EventID",
        primary_key=True,
        help_text="Unique identifier for the event",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User who owns this event",
    )
    type = models.CharField(
        db_column="Type",
        max_length=8,
        choices=EventType.choices(),
        help_text="Event type (Action or Reminder)",
    )
    title = models.TextField(
        db_column="Title",
        help_text="Event title or name",
    )
    category = models.CharField(
        db_column="Category",
        max_length=8,
        choices=EventCategory.choices(),
        help_text="Event category for grouping",
    )
    start_time = models.TimeField(
        db_column="StartTime",
        help_text="Event start time",
    )
    end_time = models.TimeField(
        db_column="EndTime",
        help_text="Event end time",
    )
    location = models.CharField(
        db_column="Location",
        max_length=255,
        blank=True,
        null=True,
        help_text="Physical location of the event",
    )
    description = models.TextField(
        db_column="Description",
        blank=True,
        null=True,
        help_text="Detailed description of the event",
    )
    repeated = models.IntegerField(
        db_column="Repeated",
        help_text="Whether this is a recurring event (1=yes, 0=no)",
    )
    frequency = models.CharField(
        db_column="Frequency",
        max_length=7,
        choices=EventFrequency.choices(),
        blank=True,
        null=True,
        help_text="Frequency for recurring events",
    )
    start_date = models.DateField(
        db_column="StartDate",
        help_text="First occurrence date for recurring events",
    )
    end_date = models.DateField(
        db_column="EndDate",
        blank=True,
        null=True,
        help_text="Last occurrence date for recurring events",
    )

    # Email notification fields
    email_to = models.TextField(
        db_column="EmailTo",
        help_text="Comma-separated list of email recipients",
    )
    email_cc = models.TextField(
        db_column="EmailCC",
        blank=True,
        null=True,
        help_text="CC recipients for event notification",
    )
    email_subject = models.TextField(
        db_column="EmailSubject",
        blank=True,
        null=True,
        help_text="Subject line for event email",
    )
    email_body = models.TextField(
        db_column="EmailBody",
        blank=True,
        null=True,
        help_text="Email body content",
    )

    class Meta:
        managed = True
        db_table = "Events"
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ["start_date", "start_time"]
        app_label = "myapp"

    def __str__(self):
        return f"{self.title} - {self.start_date}"

    def clean(self):
        """Validate event data."""
        if self.type and self.type not in dict(EventType.choices()):
            raise ValidationError({"type": "Invalid event type selected."})
        if self.category and self.category not in dict(EventCategory.choices()):
            raise ValidationError({"category": "Invalid event category selected."})
        if self.frequency and self.frequency not in dict(EventFrequency.choices()):
            raise ValidationError({"frequency": "Invalid event frequency selected."})
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be after start date."})

    def is_recurring(self) -> bool:
        """Check if this is a recurring event."""
        return bool(self.repeated and self.frequency)

    def is_past(self) -> bool:
        """Check if event has already passed."""
        from datetime import date

        if self.end_date:
            return self.end_date < date.today()
        return False


class Reminder(BaseModel):
    """
    User reminder model for ad-hoc reminders.

    Simple reminder system for:
    - Personal notes and reminders
    - Timestamp-based notifications
    - User-specific alert management
    """

    reminder_id = models.AutoField(
        db_column="ReminderID",
        primary_key=True,
        help_text="Unique identifier for the reminder",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User who created this reminder",
    )
    note = models.TextField(
        db_column="Note",
        blank=True,
        null=True,
        help_text="Reminder note or message",
    )
    timestamp = models.DateTimeField(
        db_column="Timestamp",
        help_text="When the reminder should trigger",
    )

    class Meta:
        managed = True
        db_table = "Reminders"
        verbose_name = "Reminder"
        verbose_name_plural = "Reminders"
        ordering = ["timestamp"]
        app_label = "myapp"

    def __str__(self):
        return f"Reminder for {self.user}: {self.note[:50]}..."

    def is_due(self) -> bool:
        """Check if reminder is due (past timestamp but not completed)."""
        from django.utils import timezone

        return self.timestamp <= timezone.now()

    def is_overdue(self) -> bool:
        """Check if reminder is overdue by more than 1 hour."""
        from datetime import timedelta

        from django.utils import timezone

        return self.timestamp < timezone.now() - timedelta(hours=1)
