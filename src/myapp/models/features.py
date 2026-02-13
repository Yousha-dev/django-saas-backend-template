# myapp/models/features.py
"""
Generic feature flags system for subscription plans.

This module provides a flexible, domain-agnostic feature flag system
that can work with any type of application (project management,
e-commerce, analytics, SaaS, etc.).

Instead of hardcoded feature fields, we use a generic
JSON-based feature flags system.
"""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models


class FeatureFlags(models.Model):
    """
    Generic feature flags for subscription plans.

    Stores feature configuration as JSON, allowing any
    application to define custom feature toggles without schema changes.

    Example feature_flags JSON:
    {
        "ai_analytics": {"enabled": true, "limit": 1000},
        "advanced_analytics": {"enabled": true},
        "api_access": {"enabled": true, "calls_per_hour": 100},
        "real_time_data": {"enabled": false},
        "export_formats": {"csv": true, "pdf": true, "excel": true},
        "team_collaboration": {"enabled": true, "max_members": 5},
        "custom_reports": {"enabled": true, "max_per_month": 10},
        "integrations": {"slack": false, "webhook": true}
    }
    """

    id = models.AutoField(primary_key=True)
    subscription_plan = models.OneToOneField(
        "SubscriptionPlan",
        on_delete=models.CASCADE,
        related_name="feature_flags",
        help_text="Subscription plan this feature flag belongs to",
    )
    features = models.JSONField(
        help_text="JSON object containing feature configuration",
        default=dict,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "FeatureFlags"
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"
        app_label = "myapp"

    def __str__(self):
        return f"Feature flags for {self.subscription_plan}"

    def get_feature(self, feature_path: str, default: Any = None) -> Any:
        """
        Get a feature value using dot notation.

        Args:
            feature_path: Dot-separated path to feature (e.g., 'api_access.enabled')
            default: Value to return if feature is not found

        Returns:
            The feature value or default

        Examples:
            flags.get_feature('api_access.enabled') -> True
            flags.get_feature('api_access.calls_per_hour') -> 100
            flags.get_feature('nonexistent.feature', default=0) -> 0
        """
        keys = feature_path.split(".")
        value = self.features

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default

        return value if value is not None else default

    def is_enabled(self, feature_path: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature_path: Dot-separated path to feature (e.g., 'api_access.enabled')

        Returns:
            True if feature exists and is truthy, False otherwise
        """
        value = self.get_feature(feature_path, default=False)
        return bool(value)

    def set_feature(self, feature_path: str, value: Any) -> None:
        """
        Set a feature value.

        Args:
            feature_path: Dot-separated path to feature (e.g., 'api_access.enabled')
            value: Value to set

        Example:
            flags.set_feature('api_access.enabled', True)
        """
        keys = feature_path.split(".")
        current = self.features.copy() if isinstance(self.features, dict) else {}

        # Navigate to the parent of the target key
        target = current
        for key in keys[:-1]:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            target = target[key]

        # Set the value
        target[keys[-1]] = value
        self.features = target
        self.save(update_fields=["features"])

    def enable(self, feature_path: str) -> None:
        """Enable a feature (set to True)."""
        self.set_feature(feature_path, True)

    def disable(self, feature_path: str) -> None:
        """Disable a feature (set to False)."""
        self.set_feature(feature_path, False)

    def get_all_features(self) -> dict[str, Any]:
        """Return all feature flags as a dictionary."""
        return self.features if isinstance(self.features, dict) else {}

    def clean(self) -> None:
        """Validate that features is a proper JSON object."""
        if not isinstance(self.features, dict):
            raise ValidationError({"features": "Features must be a JSON object."})


class FeatureDefinition:
    """
    Constants for well-known feature paths.

    Centralizes feature path definitions to avoid typos and
    provide documentation for available features.

    Application-agnostic features can be added here without
    modifying the model structure.
    """

    # API & Rate Limiting
    API_ENABLED: str = "api_access.enabled"
    API_CALLS_PER_HOUR: str = "api_access.calls_per_hour"
    API_DAILY_LIMIT: str = "api_access.daily_limit"
    API_MONTHLY_LIMIT: str = "api_access.monthly_limit"

    # Analytics Features
    AI_ANALYTICS_ENABLED: str = "ai_analytics.enabled"
    AI_ANALYTICS_LIMIT: str = "ai_analytics.limit"
    ADVANCED_ANALYTICS_ENABLED: str = "advanced_analytics.enabled"

    # Data Export
    EXPORT_CSV: str = "export_formats.csv"
    EXPORT_PDF: str = "export_formats.pdf"
    EXPORT_EXCEL: str = "export_formats.excel"
    EXPORT_REAL_TIME: str = "export_formats.real_time"

    # Collaboration
    TEAM_COLLABORATION_ENABLED: str = "team_collaboration.enabled"
    TEAM_MAX_MEMBERS: str = "team_collaboration.max_members"
    TEAM_SHARING_ENABLED: str = "team_collaboration.sharing.enabled"

    # Reporting
    CUSTOM_REPORTS_ENABLED: str = "custom_reports.enabled"
    CUSTOM_REPORTS_MAX_PER_MONTH: str = "custom_reports.max_per_month"
    SCHEDULED_REPORTS: str = "custom_reports.scheduled"

    # Integrations
    WEBHOOK_ENABLED: str = "integrations.webhook.enabled"
    WEBHOOK_URL: str = "integrations.webhook.url"
    SLACK_ENABLED: str = "integrations.slack.enabled"

    # Real-time Features
    REAL_TIME_UPDATES: str = "real_time_data.enabled"
    WEBSOCKET_ENABLED: str = "real_time_data.websocket"

    # Storage & Quotas
    STORAGE_LIMIT_MB: str = "storage.limit_mb"
    STORAGE_USED_MB: str = "storage.used_mb"

    # Notification Settings
    EMAIL_NOTIFICATIONS: str = "notifications.email.enabled"
    SMS_NOTIFICATIONS: str = "notifications.sms.enabled"
    PUSH_NOTIFICATIONS: str = "notifications.push.enabled"

    # Custom Domain (for SaaS apps)
    CUSTOM_DOMAIN: str = "branding.custom_domain"
    WHITE_LABELING: str = "branding.white_label_enabled"

    @classmethod
    def all_known_features(cls) -> list[str]:
        """Return all defined feature path constants."""
        return [
            cls.API_ENABLED,
            cls.API_CALLS_PER_HOUR,
            cls.API_DAILY_LIMIT,
            cls.API_MONTHLY_LIMIT,
            cls.AI_ANALYTICS_ENABLED,
            cls.AI_ANALYTICS_LIMIT,
            cls.ADVANCED_ANALYTICS_ENABLED,
            cls.EXPORT_CSV,
            cls.EXPORT_PDF,
            cls.EXPORT_EXCEL,
            cls.EXPORT_REAL_TIME,
            cls.TEAM_COLLABORATION_ENABLED,
            cls.TEAM_MAX_MEMBERS,
            cls.TEAM_SHARING_ENABLED,
            cls.CUSTOM_REPORTS_ENABLED,
            cls.CUSTOM_REPORTS_MAX_PER_MONTH,
            cls.SCHEDULED_REPORTS,
            cls.WEBHOOK_ENABLED,
            cls.WEBHOOK_URL,
            cls.SLACK_ENABLED,
            cls.REAL_TIME_UPDATES,
            cls.WEBSOCKET_ENABLED,
            cls.STORAGE_LIMIT_MB,
            cls.STORAGE_USED_MB,
            cls.EMAIL_NOTIFICATIONS,
            cls.SMS_NOTIFICATIONS,
            cls.PUSH_NOTIFICATIONS,
            cls.CUSTOM_DOMAIN,
            cls.WHITE_LABELING,
        ]
