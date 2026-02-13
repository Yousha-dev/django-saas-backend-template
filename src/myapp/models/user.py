# myapp/models/user.py
"""
User and authentication-related models.

This module contains:
- UserManager: Custom manager for creating users
- User: Main user model extending AbstractBaseUser with authentication and profile information
- SMTP configuration for custom email sending
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models

from .base import BaseModel


class Role:
    """User role constants."""

    ADMIN = "Admin"
    USER = "User"
    MODERATOR = "Moderator"

    CHOICES = [
        (ADMIN, "Administrator"),
        (USER, "Standard User"),
        (MODERATOR, "Moderator"),
    ]


class UserManager(BaseUserManager):
    """
    Custom manager for User model.

    Provides create_user() and create_superuser() methods
    compatible with Django's auth system.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with an email and password.
        """
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", Role.USER)
        extra_fields.setdefault("is_active", 1)
        extra_fields.setdefault("is_deleted", 0)
        extra_fields.setdefault("is_staff", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with admin privileges.
        """
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", 1)
        extra_fields.setdefault("is_deleted", 0)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, BaseModel):
    """
    User model representing application users.

    Extends AbstractBaseUser (Django auth) and BaseModel (timestamps/soft-delete).

    Features:
    - Email-based authentication (no username)
    - set_password() / check_password() from AbstractBaseUser
    - Profile information (name, organization, contact)
    - SMTP configuration for custom email sending
    """

    # Primary key
    user_id = models.AutoField(
        db_column="UserID",
        primary_key=True,
        help_text="Unique identifier for the user",
    )

    # Authentication fields
    full_name = models.CharField(
        db_column="FullName",
        max_length=255,
        help_text="User's full name",
    )
    email = models.CharField(
        db_column="Email",
        unique=True,
        max_length=255,
        help_text="User's email address (used for login)",
    )
    # Override AbstractBaseUser's 'password' field to use existing db_column
    password = models.CharField(
        db_column="PasswordHash",
        max_length=255,
        help_text="Hashed password",
    )
    role = models.CharField(
        db_column="Role",
        max_length=12,
        choices=Role.CHOICES,
        help_text="User role determining permissions",
    )

    # Django auth integration fields
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )
    is_superuser = models.BooleanField(
        default=False,
        help_text="Designates that this user has all permissions.",
    )
    last_login = models.DateTimeField(
        db_column="LastLogin",
        blank=True,
        null=True,
        help_text="Last login timestamp",
    )

    # Organization / Profile fields
    organization = models.CharField(
        db_column="Organization",
        max_length=255,
        blank=True,
        null=True,
        help_text="User's organization or company name",
    )
    phone = models.CharField(
        db_column="Phone",
        max_length=20,
        blank=True,
        null=True,
        help_text="User's phone number",
    )
    address = models.TextField(
        db_column="Address",
        blank=True,
        null=True,
        help_text="User's postal address",
    )
    state = models.CharField(
        db_column="State",
        max_length=45,
        blank=True,
        null=True,
        help_text="User's state or province",
    )
    zipcode = models.CharField(
        db_column="ZipCode",
        max_length=45,
        blank=True,
        null=True,
        help_text="User's postal or ZIP code",
    )
    country = models.CharField(
        db_column="Country",
        max_length=45,
        blank=True,
        null=True,
        help_text="User's country",
    )
    logo_path = models.CharField(
        db_column="LogoPath",
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to user's uploaded logo image",
    )

    # i18n and push notification fields
    preferred_language = models.CharField(
        db_column="PreferredLanguage",
        max_length=10,
        default="en",
        help_text="User's preferred language code (e.g., 'en', 'es', 'fr')",
    )
    fcm_token = models.CharField(
        db_column="FCMToken",
        max_length=500,
        blank=True,
        null=True,
        help_text="Firebase Cloud Messaging token for push notifications",
    )

    # SMTP settings for custom email sending
    use_user_smtp = models.IntegerField(
        db_column="UseCustomSMTP",
        blank=True,
        null=True,
        help_text="Flag to use custom SMTP configuration instead of default",
    )
    smtp_host = models.CharField(
        db_column="SMTPHost",
        max_length=255,
        blank=True,
        null=True,
        help_text="Custom SMTP server hostname",
    )
    smtp_port = models.IntegerField(
        db_column="SMTPPort",
        blank=True,
        null=True,
        help_text="Custom SMTP server port",
    )
    smtp_host_user = models.CharField(
        db_column="SMTPHostUser",
        max_length=255,
        blank=True,
        null=True,
        help_text="Custom SMTP username",
    )
    smtp_host_password = models.CharField(
        db_column="SMTPHostPassword",
        max_length=255,
        blank=True,
        null=True,
        help_text="Custom SMTP password",
    )
    smtp_use_tls = models.IntegerField(
        db_column="SMTPUseTLS",
        blank=True,
        null=True,
        help_text="Flag to use TLS for custom SMTP",
    )

    # Manager
    objects = UserManager()

    # AbstractBaseUser configuration
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        managed = True
        db_table = "Users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email", "is_active"]),
            models.Index(fields=["role", "is_active"]),
        ]
        app_label = "myapp"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"

    @property
    def id(self) -> int:
        """Alias for user_id to support generic access patterns."""
        return self.user_id

    @property
    def password_hash(self) -> str:
        """Backward-compatible alias for the password field."""
        return self.password

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        """Backward-compatible setter — sets the raw password field value."""
        self.password = value

    def clean(self) -> None:
        """Validate email format before saving."""
        if self.email:
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError(
                    {"email": "Enter a valid email address."}
                ) from None

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == Role.ADMIN

    def is_moderator(self) -> bool:
        """Check if user has moderator role."""
        return self.role == Role.MODERATOR

    def has_custom_smtp(self) -> bool:
        """Check if user has configured custom SMTP."""
        return bool(self.use_user_smtp and self.smtp_host)

    def has_perm(self, perm, obj=None) -> bool:
        """
        Return True if the user has the specified permission.
        Superusers have all permissions.
        """
        if self.is_superuser:
            return True
        return self.role == Role.ADMIN

    def has_module_perms(self, app_label) -> bool:
        """
        Return True if the user has permissions in the given app.
        Superusers have all permissions.
        """
        if self.is_superuser:
            return True
        return self.role == Role.ADMIN
