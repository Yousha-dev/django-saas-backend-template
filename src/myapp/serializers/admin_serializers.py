from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from myapp.models import (
    BillingFrequency,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Renewal,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "subscription_plan_id",
            "name",
            "description",
            "monthly_price",
            "yearly_price",
            "max_operations",
            "max_api_calls_per_hour",
            "feature_details",
            "is_active",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("subscription_plan_id", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_at"] = timezone.now()
        validated_data["updated_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    def validate(self, data):
        """Validate subscription plan data"""
        # Validate prices
        # Validate prices
        if "monthly_price" in data and data["monthly_price"] < 0:
            raise serializers.ValidationError(
                {"monthly_price": "Monthly price cannot be negative."}
            )

        if "yearly_price" in data and data["yearly_price"] < 0:
            raise serializers.ValidationError(
                {"yearly_price": "Yearly price cannot be negative."}
            )

        # Validate specific limits

        if "max_api_calls_per_hour" in data and data["max_api_calls_per_hour"] <= 0:
            raise serializers.ValidationError(
                {
                    "max_api_calls_per_hour": "Maximum API calls per hour must be greater than 0."
                }
            )

        # Validate name
        if "name" in data and not data["name"].strip():
            raise serializers.ValidationError({"name": "Name cannot be empty."})

        return data


class SubscriptionSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)
    status = serializers.ChoiceField(choices=SubscriptionStatus.choices())
    billing_frequency = serializers.ChoiceField(choices=BillingFrequency.choices())
    username = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    plan_name = serializers.CharField(source="subscription_plan.name", read_only=True)
    plan_price = serializers.DecimalField(
        source="subscription_plan.monthly_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Subscription
        fields = [
            "subscription_id",
            "user",
            "username",
            "user_email",
            "subscription_plan",
            "plan_name",
            "plan_price",
            "billing_frequency",
            "start_date",
            "end_date",
            "auto_renew",
            "status",
            "renewal_count",
            "last_renewed_at",
            "is_active",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "subscription_id",
            "created_at",
            "updated_at",
            "last_renewed_at",
        )

    def create(self, validated_data):
        validated_data["created_at"] = timezone.now()
        validated_data["updated_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    def validate(self, data):
        """Validate subscription data"""
        # Validate dates
        if (
            "start_date" in data
            and "end_date" in data
            and data["end_date"] <= data["start_date"]
        ):
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )

        # Validate renewal count
        if "renewal_count" in data and data["renewal_count"] < 0:
            raise serializers.ValidationError(
                {"renewal_count": "Renewal count cannot be negative."}
            )

        if not self.instance:  # create operation
            # For new subscriptions, require these fields
            if not data.get("subscription_plan"):
                raise serializers.ValidationError(
                    {
                        "subscription_plan": "Subscription plan ID is required for new subscriptions."
                    }
                )
            if not data.get("user"):
                raise serializers.ValidationError(
                    {"user": "User ID is required for new subscriptions."}
                )

        # Validate user doesn't have multiple active subscriptions
        if "user" in data and data.get("status") == "Active":
            existing_subscriptions = Subscription.objects.filter(
                user=data["user"], status="Active", is_active=1, is_deleted=0
            )
            if self.instance:
                existing_subscriptions = existing_subscriptions.exclude(
                    subscription_id=self.instance.subscription_id
                )

            if existing_subscriptions.exists():
                raise serializers.ValidationError(
                    {"user": "User already has an active subscription."}
                )

        return data


class RenewalSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)
    subscription_info = serializers.CharField(
        source="subscription.user.full_name", read_only=True
    )
    user_email = serializers.CharField(source="subscription.user.email", read_only=True)
    renewed_by_name = serializers.CharField(
        source="renewed_by.full_name", read_only=True
    )
    plan_name = serializers.CharField(
        source="subscription.subscription_plan.name", read_only=True
    )

    class Meta:
        model = Renewal
        fields = [
            "renewal_id",
            "subscription",
            "subscription_info",
            "user_email",
            "plan_name",
            "renewed_by",
            "renewed_by_name",
            "renewal_date",
            "renewal_cost",
            "notes",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("renewal_id", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_at"] = timezone.now()
        validated_data["updated_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    def validate(self, data):
        """Validate renewal data"""
        # Validate renewal cost
        if "renewal_cost" in data and data["renewal_cost"] < Decimal("0.00"):
            raise serializers.ValidationError(
                {"renewal_cost": "Renewal cost cannot be negative."}
            )

        # Validate renewal date
        if "renewal_date" in data and data["renewal_date"] > timezone.now():
            raise serializers.ValidationError(
                {"renewal_date": "Renewal date cannot be in the future."}
            )

        # Validate required relationships
        if not self.instance and not data.get("subscription"):
            raise serializers.ValidationError(
                {"subscription": "Subscription ID is required."}
            )

        if "subscription" in data:
            subscription = data["subscription"]
            if hasattr(subscription, "is_deleted") and subscription.is_deleted == 1:
                raise serializers.ValidationError(
                    {"subscription": "Cannot renew a deleted subscription."}
                )
            if hasattr(subscription, "is_active") and subscription.is_active == 0:
                raise serializers.ValidationError(
                    {"subscription": "Cannot renew an inactive subscription."}
                )

        return data


class PaymentSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)
    subscription_info = serializers.CharField(
        source="subscription.user.full_name", read_only=True
    )
    user_email = serializers.CharField(source="subscription.user.email", read_only=True)
    plan_name = serializers.CharField(
        source="subscription.subscription_plan.name", read_only=True
    )
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices(), required=False
    )
    status = serializers.ChoiceField(choices=PaymentStatus.choices(), required=False)

    class Meta:
        model = Payment
        fields = [
            "payment_id",
            "subscription",
            "subscription_info",
            "user_email",
            "plan_name",
            "amount",
            "payment_date",
            "payment_method",
            "reference_number",
            "status",
            "payment_response",
            "is_active",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("payment_id", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_at"] = timezone.now()
        validated_data["updated_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()
        return super().update(instance, validated_data)

    def validate(self, data):
        """Validate payment data"""
        # Validate amount
        if "amount" in data and data["amount"] <= Decimal("0.00"):
            raise serializers.ValidationError(
                {"amount": "Payment amount must be greater than zero."}
            )

        # Validate payment date
        if "payment_date" in data and data["payment_date"] > timezone.now().date():
            raise serializers.ValidationError(
                {"payment_date": "Payment date cannot be in the future."}
            )

        # Validate required fields
        if not self.instance and not data.get("subscription"):
            raise serializers.ValidationError(
                {"subscription": "Subscription ID is required."}
            )

        return data
