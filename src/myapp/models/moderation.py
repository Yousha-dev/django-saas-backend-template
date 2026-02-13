# myapp/models/moderation.py
"""
Content moderation models.

Provides:
- ModerationQueue: Queue for reported/flagged content awaiting moderation
- ModerationAppeal: Appeals submitted by users against moderation decisions
"""

from django.db import models

from .base import BaseModel
from .choices import AppealStatus, ModerationStatus


class ModerationQueue(BaseModel):
    """
    Moderation queue for reported/flagged content.

    Stores content reports from users or automated systems,
    and tracks the moderation workflow through to resolution.
    """

    moderation_queue_id = models.AutoField(
        db_column="ModerationQueueID",
        primary_key=True,
        help_text="Unique identifier for the moderation queue entry",
    )
    content_type = models.CharField(
        db_column="ContentType",
        max_length=50,
        help_text="Type of content being moderated (e.g., post, comment, profile)",
    )
    content_id = models.IntegerField(
        db_column="ContentID",
        help_text="ID of the content being moderated",
    )
    reporter_id = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="ReporterID",
        blank=True,
        null=True,
        related_name="reported_content",
        help_text="User who reported the content",
    )
    reason = models.TextField(
        db_column="Reason",
        help_text="Reason for the report/flag",
    )
    details = models.TextField(
        db_column="Details",
        blank=True,
        default="",
        help_text="Additional details about the report",
    )
    status = models.CharField(
        db_column="Status",
        max_length=20,
        choices=ModerationStatus.choices(),
        default=ModerationStatus.PENDING.value,
        help_text="Current moderation status",
    )
    moderator_id = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="ModeratorID",
        blank=True,
        null=True,
        related_name="moderated_content",
        help_text="Moderator who handled this item",
    )
    moderation_notes = models.TextField(
        db_column="ModerationNotes",
        blank=True,
        null=True,
        help_text="Notes from the moderator",
    )
    moderated_at = models.DateTimeField(
        db_column="ModeratedAt",
        blank=True,
        null=True,
        help_text="When the content was moderated",
    )
    auto_flagged = models.BooleanField(
        db_column="AutoFlagged",
        default=False,
        help_text="Whether this was flagged by automated moderation",
    )
    auto_flag_reason = models.TextField(
        db_column="AutoFlagReason",
        blank=True,
        null=True,
        help_text="Reason from automated moderation system",
    )
    severity = models.IntegerField(
        db_column="Severity",
        default=1,
        help_text="Severity level (1=low, 5=critical)",
    )

    class Meta:
        managed = True
        db_table = "ModerationQueue"
        verbose_name = "Moderation Queue Item"
        verbose_name_plural = "Moderation Queue Items"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["content_type", "content_id"]),
            models.Index(fields=["severity", "status"]),
        ]
        ordering = ["-severity", "-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"ModerationQueue #{self.moderation_queue_id} - {self.content_type}:{self.content_id} ({self.status})"


class ModerationAppeal(BaseModel):
    """
    Appeals submitted by users against moderation decisions.

    Allows users to contest moderation actions and have them reviewed.
    """

    moderation_appeal_id = models.AutoField(
        db_column="ModerationAppealID",
        primary_key=True,
        help_text="Unique identifier for the appeal",
    )
    original_queue = models.ForeignKey(
        ModerationQueue,
        models.CASCADE,
        db_column="OriginalQueueID",
        related_name="appeals",
        help_text="The original moderation queue item being appealed",
    )
    user = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="UserID",
        related_name="moderation_appeals",
        help_text="User submitting the appeal",
    )
    reason = models.TextField(
        db_column="Reason",
        help_text="Reason for the appeal",
    )
    status = models.CharField(
        db_column="Status",
        max_length=20,
        choices=AppealStatus.choices(),
        default=AppealStatus.PENDING.value,
        help_text="Current appeal status",
    )
    reviewer = models.ForeignKey(
        "User",
        models.SET_NULL,
        db_column="ReviewerID",
        blank=True,
        null=True,
        related_name="reviewed_appeals",
        help_text="Admin/moderator who reviewed the appeal",
    )
    reviewer_notes = models.TextField(
        db_column="ReviewerNotes",
        blank=True,
        null=True,
        help_text="Notes from the reviewer",
    )
    reviewed_at = models.DateTimeField(
        db_column="ReviewedAt",
        blank=True,
        null=True,
        help_text="When the appeal was reviewed",
    )

    class Meta:
        managed = True
        db_table = "ModerationAppeals"
        verbose_name = "Moderation Appeal"
        verbose_name_plural = "Moderation Appeals"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "status"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"Appeal #{self.moderation_appeal_id} for Queue #{self.original_queue_id} ({self.status})"
