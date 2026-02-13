from django.core.validators import validate_email
from django.utils import timezone
from rest_framework import serializers

from myapp.models import (
    Event,
    EventCategory,
    EventFrequency,
    EventType,
    Notification,
    NotificationType,
    Reminder,
)
from myapp.serializers.admin_serializers import SubscriptionSerializer


class NotificationSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)
    is_read = serializers.IntegerField(default=0)
    type = serializers.ChoiceField(choices=NotificationType.choices())

    class Meta:
        model = Notification
        fields = [
            "notification_id",
            "user",
            "title",
            "message",
            "type",
            "is_read",
            "is_active",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("notification_id", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_at"] = timezone.now()
        validated_data["updated_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    def validate(self, data):
        """
        Custom validation for notification data.
        - Ensure type is valid
        - Validate daysuntilexpiry is positive if provided
        """
        # Validate daysuntilexpiry if provided
        if (
            "daysuntilexpiry" in data
            and data["daysuntilexpiry"] is not None
            and data["daysuntilexpiry"] < 0
        ):
            raise serializers.ValidationError(
                {"daysuntilexpiry": "Days until expiry must be a positive number."}
            )

        # Ensure at least one related entity is provided
        # if not self.instance:  # create operation
        #     if ('extensionsubscriptionid' not in data or data['extensionsubscriptionid'] is None) and \
        #     ('contractid' not in data or data['contractid'] is None):
        #         raise serializers.ValidationError(
        #             "Either extensionsubscriptionid or contractid must be provided."
        #         )

        return data


class ReminderSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)
    timestamp = serializers.DateTimeField(required=True)

    class Meta:
        model = Reminder
        fields = [
            "reminder_id",
            "user",
            "note",
            "timestamp",
            "is_active",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("reminder_id", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_at"] = timezone.now()
        validated_data["updated_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    def validate(self, data):
        # Validate timestamp
        if "timestamp" in data and data["timestamp"] < timezone.now():
            raise serializers.ValidationError(
                {"timestamp": "Reminder timestamp cannot be in the past."}
            )

        # Validate note length
        if "note" in data and len(data["note"]) > 2000:  # Adjust max length as needed
            raise serializers.ValidationError(
                {"note": "Note cannot exceed 2000 characters."}
            )

        return data


class EventSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)
    type = serializers.ChoiceField(choices=EventType.choices())
    category = serializers.ChoiceField(choices=EventCategory.choices())
    frequency = serializers.ChoiceField(
        choices=EventFrequency.choices(), allow_null=True, required=False
    )

    class Meta:
        model = Event
        fields = [
            "event_id",
            "user",
            "type",
            "title",
            "category",
            "start_time",
            "end_time",
            "location",
            "description",
            "repeated",
            "frequency",
            "start_date",
            "end_date",
            "email_to",
            "email_cc",
            "email_subject",
            "email_body",
            "is_active",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("event_id", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_at"] = timezone.now()
        validated_data["updated_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    def validate_emails(self, emails_str):
        """Helper method to validate multiple email addresses"""
        if not emails_str:
            return

        emails = [email.strip() for email in emails_str.split(",")]
        for email in emails:
            try:
                validate_email(email)
            except ValueError:
                raise serializers.ValidationError(
                    f"Invalid email format: {email}"
                ) from None

    def validate(self, data):
        # Skip required field checks for partial updates
        is_partial = getattr(self, "partial", False)

        # Validate start date
        if not is_partial and not data.get("start_date"):
            raise serializers.ValidationError({"start_date": "Start date is required."})
        # Validate end date
        if not is_partial and not data.get("end_date"):
            raise serializers.ValidationError({"end_date": "End date is required."})
        # Validate date order
        if (
            data.get("start_date")
            and data.get("end_date")
            and data["start_date"] > data["end_date"]
        ):
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )

        # Validate required fields for repeated events
        if data.get("repeated") == 1:
            # For repeated events, start and end dates cannot be the same
            if data["start_date"] == data["end_date"]:
                raise serializers.ValidationError(
                    {
                        "end_date": "For repeated events, start and end dates cannot be the same."
                    }
                )

            # Validate frequency is provided for repeated events
            if not data.get("frequency"):
                raise serializers.ValidationError(
                    {"frequency": "Frequency is required for repeated events."}
                )

        # Validate required fields based on event type
        if data.get("type") == "Action":
            # Validate email subject and body for Action type
            if not data.get("email_subject"):
                raise serializers.ValidationError(
                    {
                        "email_subject": "Email subject is required for Action type events."
                    }
                )
            if not data.get("email_body"):
                raise serializers.ValidationError(
                    {"email_body": "Email body is required for Action type events."}
                )

        # Validate times
        if (
            data.get("start_time")
            and data.get("end_time")
            and data["start_time"] > data["end_time"]
        ):
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )

        # Validate email fields
        if data.get("email_to"):
            self.validate_emails(data["email_to"])
        if data.get("email_cc"):
            self.validate_emails(data["email_cc"])

        # Validate description length
        if data.get("description") and len(data["description"]) > 2000:
            raise serializers.ValidationError(
                {"description": "Description cannot exceed 2000 characters."}
            )

        # Validate location length
        if data.get("location") and len(data["location"]) > 255:
            raise serializers.ValidationError(
                {"location": "Location cannot exceed 255 characters."}
            )

        return data


# Dashboard summary serializer
class DashboardSerializer(serializers.Serializer):
    """Serializer for user dashboard summary."""

    subscription = SubscriptionSerializer()
    summary = serializers.DictField()
    api_usage_stats = serializers.DictField()
