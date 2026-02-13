# myapp/models/content.py
"""
Generic content models for SaaS applications.

Provides:
- ModeratableContent: Abstract base for any content that can be moderated
- Post: User-generated posts (articles, updates, discussions)
- Comment: User-generated comments on posts or other content
"""

from django.db import models
from django.utils import timezone

from .base import BaseModel
from .choices import ContentStatus


class ModeratableContent(BaseModel):
    """
    Abstract base model for any content that can be moderated.

    Provides common content fields for moderation integration.
    Extend this model for any content type that should support
    automated/manual content moderation.
    """

    content_text = models.TextField(
        db_column="ContentText",
        help_text="The text content to be moderated",
    )
    content_status = models.CharField(
        db_column="ContentStatus",
        max_length=20,
        choices=ContentStatus.choices(),
        default=ContentStatus.PUBLISHED.value,
        help_text="Content moderation status",
    )
    moderated_at = models.DateTimeField(
        db_column="ModeratedAt",
        blank=True,
        null=True,
        help_text="When the content was last moderated",
    )
    moderation_notes = models.TextField(
        db_column="ModerationNotes",
        blank=True,
        null=True,
        help_text="Notes from moderation",
    )

    class Meta:
        abstract = True

    def flag_for_review(self, reason: str = ""):
        """Flag content for moderation review."""
        self.content_status = ContentStatus.UNDER_REVIEW.value
        self.moderation_notes = reason
        self.save(update_fields=["content_status", "moderation_notes", "updated_at"])

    def approve(self):
        """Approve content after moderation."""
        self.content_status = ContentStatus.PUBLISHED.value
        self.moderated_at = timezone.now()
        self.save(update_fields=["content_status", "moderated_at", "updated_at"])

    def remove(self, reason: str = ""):
        """Remove content (soft-delete via moderation)."""
        self.content_status = ContentStatus.REMOVED.value
        self.moderation_notes = reason
        self.moderated_at = timezone.now()
        self.save(
            update_fields=[
                "content_status",
                "moderation_notes",
                "moderated_at",
                "updated_at",
            ]
        )


class Post(ModeratableContent):
    """
    User-generated posts.

    Can represent articles, updates, discussions, or any
    primary content created by users.
    """

    post_id = models.AutoField(
        db_column="PostID",
        primary_key=True,
        help_text="Unique identifier for the post",
    )
    author = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="AuthorID",
        related_name="posts",
        help_text="User who created the post",
    )
    title = models.CharField(
        db_column="Title",
        max_length=500,
        help_text="Post title",
    )
    content_type = models.CharField(
        db_column="ContentType",
        max_length=50,
        default="general",
        help_text="Type of post (article, update, discussion, etc.)",
    )

    class Meta:
        managed = True
        db_table = "Posts"
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        indexes = [
            models.Index(fields=["author", "content_status"]),
            models.Index(fields=["content_status", "created_at"]),
            models.Index(fields=["content_type", "content_status"]),
        ]
        ordering = ["-created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"Post #{self.post_id}: {self.title[:50]}"


class Comment(ModeratableContent):
    """
    User-generated comments on posts or other content.
    """

    comment_id = models.AutoField(
        db_column="CommentID",
        primary_key=True,
        help_text="Unique identifier for the comment",
    )
    author = models.ForeignKey(
        "User",
        models.CASCADE,
        db_column="AuthorID",
        related_name="comments",
        help_text="User who authored the comment",
    )
    post = models.ForeignKey(
        Post,
        models.CASCADE,
        db_column="PostID",
        related_name="comments",
        help_text="Post this comment belongs to",
    )
    parent_comment = models.ForeignKey(
        "self",
        models.CASCADE,
        db_column="ParentCommentID",
        blank=True,
        null=True,
        related_name="replies",
        help_text="Parent comment for threaded replies",
    )

    class Meta:
        managed = True
        db_table = "Comments"
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        indexes = [
            models.Index(fields=["post", "content_status"]),
            models.Index(fields=["author", "content_status"]),
        ]
        ordering = ["created_at"]
        app_label = "myapp"

    def __str__(self):
        return f"Comment #{self.comment_id} on Post #{self.post_id}"
