import base64
import os
import uuid

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from myapp.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token["user_id"] = user.user_id
        token["role"] = user.role
        return token

    def validate(self, attrs):
        email = attrs.get("email", None)
        password = attrs.get("password", None)

        if email is None or password is None:
            raise AuthenticationFailed("Email and password are required.")

        try:
            user = User.objects.get(email=email, is_active=1, is_deleted=0)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid email or password.") from None

        if not user.check_password(password):
            raise AuthenticationFailed("Invalid email or password.")

        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.user_id,
            "role": user.role,
        }


class UserSerializer(serializers.ModelSerializer):
    is_active = serializers.IntegerField(default=1)
    is_deleted = serializers.IntegerField(default=0)
    logo = serializers.CharField(
        write_only=True, required=False, allow_null=True
    )  # Add logo field
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id",
            "full_name",
            "email",
            "password",
            "role",
            "organization",
            "phone",
            "address",
            "state",
            "zipcode",
            "country",
            "logo",
            "logo_url",
            "logo_path",
            "use_user_smtp",
            "smtp_host",
            "smtp_port",
            "smtp_host_user",
            "smtp_host_password",
            "smtp_use_tls",
            "preferred_language",
            "fcm_token",
            "is_active",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("user_id", "created_at", "updated_at")

    def get_logo_url(self, obj):
        """Return the complete URL for the logo"""
        if obj.logo_path:
            return f"{settings.MEDIA_URL}{obj.logo_path}"
        return None

    def create(self, validated_data):
        validated_data["is_active"] = 1 if validated_data.get("is_active", True) else 0
        validated_data["is_deleted"] = 0
        validated_data["created_at"] = timezone.now()

        # Handle logo upload
        logo_data = validated_data.pop("logo", None)

        # Hash the password if not already hashed
        if validated_data.get("password") and not validated_data["password"].startswith(
            "pbkdf2_sha256$"
        ):
            validated_data["password"] = make_password(validated_data["password"])

        instance = super().create(validated_data)

        # Process logo if provided
        if logo_data:
            logo_path = self._handle_logo_upload(logo_data, instance)
            if logo_path:
                instance.logo_path = logo_path
                instance.save()

        return instance

    def update(self, instance, validated_data):
        validated_data["updated_at"] = timezone.now()

        # Handle logo upload
        logo_data = validated_data.pop("logo", None)
        if logo_data:
            # Delete old logo if exists
            if instance.logo_path:
                old_path = os.path.join(settings.MEDIA_ROOT, instance.logo_path)
                if os.path.exists(old_path):
                    os.remove(old_path)

            logo_path = self._handle_logo_upload(logo_data, instance)
            if logo_path:
                validated_data["logo_path"] = logo_path

        return super().update(instance, validated_data)

    def _handle_logo_upload(self, logo_data, instance):
        """Handle the logo upload process"""
        if not logo_data:
            return None

        try:
            format, imgstr = (
                logo_data.split(";base64,")
                if ";base64," in logo_data
                else ("", logo_data)
            )
            ext = format.split("/")[-1] if format else "png"
            data = ContentFile(base64.b64decode(imgstr))

            # Create user-specific upload path
            relative_path = f"users/{instance.user_id}/logo_{uuid.uuid4().hex}.{ext}"
            full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "wb") as f:
                f.write(data.read())

            return relative_path

        except Exception as e:
            raise serializers.ValidationError(f"Error processing logo: {e!s}") from e

    def validate(self, data):
        """Custom validation for user data."""
        # Validate email format and uniqueness
        if "email" in data:
            from django.core.validators import validate_email

            try:
                validate_email(data["email"])
            except ValueError:
                raise serializers.ValidationError(
                    {"email": "Invalid email format."}
                ) from None

            # Check email uniqueness
            if (
                User.objects.filter(email=data["email"], is_deleted=0)
                .exclude(user_id=getattr(self.instance, "user_id", None))
                .exists()
            ):
                raise serializers.ValidationError(
                    {"email": "This email is already in use."}
                )

        # Validate SMTP settings
        if "use_user_smtp" in data and data.get("use_user_smtp") == 1:
            required_smtp_fields = [
                "smtp_host",
                "smtp_port",
                "smtp_host_user",
                "smtp_host_password",
            ]
            for field in required_smtp_fields:
                if not data.get(field):
                    raise serializers.ValidationError(
                        {field: f"{field} is required when custom SMTP is enabled."}
                    )

            # Validate SMTP port range
            if data.get("smtp_port") and (
                data["smtp_port"] < 1 or data["smtp_port"] > 65535
            ):
                raise serializers.ValidationError(
                    {"smtp_port": "SMTP port must be between 1 and 65535."}
                )

        return data
