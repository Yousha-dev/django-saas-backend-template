# myapp/models/logging.py
"""
Logging and audit trail models.

This module contains:
- ActivityLog: User activity tracking
- AuditLog: System audit trail
"""

from django.db import models

from .base import BaseModel


class ActivityLog(BaseModel):
    """
    User activity log for tracking actions.

    Tracks:
    - User activities and actions
    - Timestamps of activities
    - Activity details for debugging
    """

    activity_id = models.AutoField(
        db_column="ActivityID",
        primary_key=True,
        help_text="Unique identifier for the activity log entry",
    )
    user = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User who performed the activity",
    )
    activity_type = models.CharField(
        db_column="ActivityType",
        max_length=18,
        help_text="Type or category of activity",
    )
    activity_details = models.TextField(
        db_column="ActivityDetails",
        blank=True,
        null=True,
        help_text="Detailed information about the activity",
    )
    activity_date = models.DateTimeField(
        db_column="ActivityDate",
        blank=True,
        null=True,
        help_text="When the activity occurred",
    )

    class Meta:
        managed = True
        db_table = "ActivityLogs"
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=["user", "activity_date"]),
            models.Index(fields=["activity_type", "activity_date"]),
        ]
        ordering = ["-activity_date"]
        app_label = "myapp"

    def __str__(self):
        return f"{self.user} - {self.activity_type} at {self.activity_date}"


class AuditLog(BaseModel):
    """
    System audit log for compliance and debugging.

    Tracks:
    - Database changes (CRUD operations)
    - Affected tables and records
    - User attribution for changes
    """

    audit_log_id = models.AutoField(
        db_column="AuditLogID",
        primary_key=True,
        help_text="Unique identifier for the audit log entry",
    )
    user = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="UserID",
        blank=True,
        null=True,
        help_text="User who performed the action",
    )
    action = models.CharField(
        db_column="Action",
        max_length=255,
        help_text="Action performed (e.g., CREATE, UPDATE, DELETE)",
    )
    table_affected = models.CharField(
        db_column="TableAffected",
        max_length=255,
        blank=True,
        null=True,
        help_text="Database table affected by the action",
    )
    record_id = models.IntegerField(
        db_column="RecordID",
        blank=True,
        null=True,
        help_text="ID of the affected record",
    )

    class Meta:
        managed = True
        db_table = "AuditLogs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["table_affected", "created_at"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"{self.action} on {self.table_affected} ({self.record_id})"
