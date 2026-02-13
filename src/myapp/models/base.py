# myapp/models/base.py
"""
Base model classes providing common functionality for all models.

This module provides:
- BaseModel: Common fields and methods for all models
- TimeStampedModel: Automatic created_at and updated_at timestamps
- SoftDeleteModel: Soft delete functionality using is_active and is_deleted flags
- ActiveModel: Common active flag management
"""

from typing import Any

from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model with common fields for all models.

    Provides:
    - is_active: Active status flag
    - is_deleted: Soft delete flag
    - created_at: Auto-populated creation timestamp
    - updated_at: Auto-populated update timestamp
    - created_by: User who created the record
    - updated_by: User who last updated the record
    """

    is_active = models.IntegerField(
        db_column="IsActive",
        blank=True,
        null=True,
        default=1,
        help_text="Flag indicating if the record is active (1=active, 0=inactive)",
    )
    is_deleted = models.IntegerField(
        db_column="IsDeleted",
        blank=True,
        null=True,
        default=0,
        help_text="Flag indicating if the record is soft-deleted (1=deleted, 0=not deleted)",
    )
    created_at = models.DateTimeField(
        db_column="CreatedAt",
        auto_now_add=True,
        null=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        db_column="UpdatedAt",
        auto_now=True,
        null=True,
        help_text="Timestamp when the record was last updated",
    )
    created_by = models.IntegerField(
        db_column="CreatedBy",
        blank=True,
        null=True,
        help_text="ID of the user who created this record",
    )
    updated_by = models.IntegerField(
        db_column="UpdatedBy",
        blank=True,
        null=True,
        help_text="ID of the user who last updated this record",
    )

    class Meta:
        abstract = True
        get_latest_by = "created_at"

    def soft_delete(self) -> None:
        """Mark the record as deleted without actually removing it from the database."""
        self.is_deleted = 1
        self.is_active = 0
        self.save()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = 0
        self.save()

    def activate(self) -> None:
        """Mark the record as active."""
        self.is_active = 1
        self.save()

    def deactivate(self) -> None:
        """Mark the record as inactive."""
        self.is_active = 0
        self.save()


class TimeStampedModel(models.Model):
    """
    Abstract base model providing timestamp fields.
    """

    created_at = models.DateTimeField(
        db_column="CreatedAt",
        auto_now_add=True,
        null=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        db_column="UpdatedAt",
        auto_now=True,
        null=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        abstract = True
        get_latest_by = "created_at"


class SoftDeleteModel(models.Model):
    """
    Abstract base model providing soft delete functionality.
    """

    is_active = models.IntegerField(
        db_column="IsActive",
        blank=True,
        null=True,
        default=1,
    )
    is_deleted = models.IntegerField(
        db_column="IsDeleted",
        blank=True,
        null=True,
        default=0,
    )

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        """Mark the record as deleted without removing it from the database."""
        self.is_deleted = 1
        self.is_active = 0
        self.save()

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = 0
        self.save()

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """Permanently delete the record from the database."""
        return super().delete()

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """Override delete to use soft delete by default."""
        self.soft_delete()


class ActiveModel(models.Model):
    """
    Abstract base model for active/inactive functionality.
    """

    is_active = models.IntegerField(
        db_column="IsActive",
        blank=True,
        null=True,
        default=1,
    )

    class Meta:
        abstract = True

    def activate(self) -> None:
        """Mark the record as active."""
        self.is_active = 1
        self.save()

    def deactivate(self) -> None:
        """Mark the record as inactive."""
        self.is_active = 0
        self.save()
