import logging
from datetime import timedelta

import stripe
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from myapp.emailhelper import EmailHelper
from myapp.models import (
    PaymentMethod,
    PaymentStatus,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)
from myapp.serializers.admin_serializers import (
    PaymentSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
)
from myapp.serializers.auth_serializers import UserSerializer

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateStripePaymentIntentAPI(APIView):
    """
    Create a Stripe PaymentIntent and return its client secret.
    """

    permission_classes = []

    @swagger_auto_schema(
        operation_description="Create Stripe Payment Intent",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Payment amount"
                ),
                "currency": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Currency code", default="usd"
                ),
            },
            required=["amount"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "client_secret": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Stripe client secret"
                    )
                },
            ),
            400: "Bad Request",
            503: "Service temporarily unavailable",
        },
    )
    def post(self, request):
        # Check if Stripe is enabled
        stripe_enabled = getattr(settings, "STRIPE_ENABLED", False)

        if not stripe_enabled:
            return Response(
                {
                    "error": "Stripe payment service is temporarily disabled for maintenance.",
                    "service_status": "disabled",
                    "message": "Please try again later or contact support for alternative payment methods.",
                    "support_email": getattr(
                        settings, "SUPPORT_EMAIL", "support@example.com"
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            amount = request.data.get("amount")
            currency = request.data.get("currency", "usd")

            if not amount:
                return Response(
                    {"error": "Amount is required."}, status=status.HTTP_400_BAD_REQUEST
                )

            amount_cents = int(float(amount) * 100)

            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                payment_method_types=["card"],
                metadata={"integration_check": "accept_a_payment"},
            )

            return Response(
                {"client_secret": payment_intent.client_secret},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Stripe payment error: {e!s}")
            return Response(
                {"error": f"Payment processing error: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentServiceStatusAPI(APIView):
    """
    Check the status of payment services.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Check payment service status",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "stripe_enabled": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "service_status": openapi.Schema(type=openapi.TYPE_STRING),
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                },
            )
        },
    )
    def get(self, request):
        stripe_enabled = getattr(settings, "STRIPE_ENABLED", False)

        return Response(
            {
                "stripe_enabled": stripe_enabled,
                "service_status": "enabled" if stripe_enabled else "disabled",
                "message": "Payment services are operational"
                if stripe_enabled
                else "Payment services are temporarily disabled for maintenance",
            },
            status=status.HTTP_200_OK,
        )


class ListSubscriptionPlansAPI(APIView):
    """
    List all active subscription plans.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="List all active subscription plans.",
        responses={200: SubscriptionPlanSerializer(many=True), 400: "Bad Request."},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=1, is_deleted=0)
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteUserAPI(APIView):
    """
    Delete a user account.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Delete an existing user account.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="User ID to delete"
                ),
            },
            required=["user_id"],
        ),
        responses={200: "User deleted successfully.", 404: "User not found."},
    )
    def delete(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(user_id=user_id)
            user.delete()
            return Response(
                {"message": "User deleted successfully."}, status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class RegisterUserSubscriptionAPI(APIView):
    """
    Register a new user with associated subscription and payment records.
    """

    permission_classes = [AllowAny]

    def calculate_subscription_dates(self, frequency):
        """Calculate subscription start and end dates based on frequency."""
        start_date = timezone.now().date()

        frequencies = {
            "Monthly": 30,
            "Yearly": 365,
            "Weekly": 7,
            "Semi-Annually": 180,
            "Quarterly": 90,
            "One-Time": 3650,
        }
        days = frequencies.get(frequency, 30)
        end_date = start_date + timedelta(days=days)

        return start_date, end_date

    @swagger_auto_schema(
        operation_description="Register a new user with associated subscription and payment records.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "fullname": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User full name"
                ),
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User email"
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User password"
                ),
                "role": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User role", default="User"
                ),
                "organization": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Organization name"
                ),
                "phone": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Phone number"
                ),
                "address": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Address"
                ),
                "state": openapi.Schema(type=openapi.TYPE_STRING, description="State"),
                "zipcode": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Zip code"
                ),
                "country": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Country"
                ),
                "logo": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Base64 encoded logo image"
                ),
                "subscription_plan_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Subscription plan ID"
                ),
                "frequency": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Billing frequency"
                ),
                "subscriptionStatus": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[choice[0] for choice in SubscriptionStatus.choices()],
                    description="Subscription status",
                ),
                "Autorenew": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Auto-renewal flag"
                ),
                "paymentAmount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Payment amount"
                ),
                "paymentMethod": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[choice[0] for choice in PaymentMethod.choices()],
                    description="Payment method",
                ),
                "ReferenceNumber": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Payment reference number"
                ),
                "paymentStatus": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[choice[0] for choice in PaymentStatus.choices()],
                    description="Payment status",
                ),
                "PaymentResponse": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Payment response"
                ),
            },
            required=[
                "fullname",
                "email",
                "password",
                "subscriptionplanid",
                "frequency",
                "paymentAmount",
                "paymentMethod",
            ],
        ),
        responses={
            201: "Registration successful",
            400: "Validation error",
            500: "Internal server error",
        },
    )
    @transaction.atomic
    def post(self, request):
        try:
            data = request.data
            current_time = timezone.now()

            # Check if this is a paid subscription and Stripe is disabled
            # stripe_enabled = getattr(settings, 'STRIPE_ENABLED', False)
            # payment_amount = data.get('paymentAmount', 0)

            # if float(payment_amount) > 0 and not stripe_enabled:
            #     return Response({
            #         'error': 'Payment processing is currently disabled. Please contact support to complete your subscription.',
            #         'support_email': 'support@duedoom.com',
            #         'service_status': 'disabled'
            #     }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # 1. Create User
            user_data = {
                "full_name": data.get("fullname"),
                "email": data.get("email"),
                "password": data.get("password"),
                "role": data.get("role", "User"),
                "organization": data.get("organization"),
                "phone": data.get("phone"),
                "address": data.get("address"),
                "state": data.get("state"),
                "zipcode": data.get("zipcode"),
                "country": data.get("country"),
                "logo": data.get("logo"),
                "is_active": 1,
                "is_deleted": 0,
                "created_at": current_time,
            }

            user_serializer = UserSerializer(data=user_data)
            if not user_serializer.is_valid():
                return Response(
                    user_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

            user = user_serializer.save()

            # 2. Create Subscription
            frequency = data.get("frequency", "Monthly")
            subscription_status = data.get("subscriptionStatus", "Active")
            start_date, end_date = self.calculate_subscription_dates(frequency)

            subscription_data = {
                "user": user.user_id,
                "subscription_plan": data.get("subscriptionplanid"),
                "billing_frequency": frequency,
                "start_date": start_date,
                "end_date": end_date,
                "auto_renew": data.get("Autorenew", 0),
                "status": subscription_status,
                "renewal_count": 0,
                "is_active": 1,
                "is_deleted": 0,
                "created_by": user.user_id,
                "created_at": current_time,
            }

            subscription_serializer = SubscriptionSerializer(data=subscription_data)
            if not subscription_serializer.is_valid():
                return Response(
                    subscription_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

            subscription = subscription_serializer.save()

            # 3. Create Payment
            payment_data = {
                "subscription": subscription.subscription_id,
                "amount": data.get("paymentAmount"),
                "payment_date": current_time.date(),
                "payment_method": data.get("paymentMethod", "CreditCard"),
                "reference_number": data.get("ReferenceNumber"),
                "status": data.get("paymentStatus", "Completed"),
                "payment_response": data.get("PaymentResponse"),
                "is_active": 1,
                "is_deleted": 0,
                "created_by": user.user_id,
                "created_at": current_time,
            }

            payment_serializer = PaymentSerializer(data=payment_data)
            if not payment_serializer.is_valid():
                return Response(
                    payment_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

            payment_serializer.save()

            return Response(
                {
                    "message": "Registration successful",
                    "data": {
                        "user": user_serializer.data,
                        "subscription": subscription_serializer.data,
                        "payment": payment_serializer.data,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegisterUserAPI(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "fullname": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User's full name"
                ),
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User email"
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User password"
                ),
                "role": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["Admin", "User"],
                    description="Role of the user: Admin or User",
                ),
                "organization": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Organization name"
                ),
                "phone": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Phone number"
                ),
                "address": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Address"
                ),
                "state": openapi.Schema(type=openapi.TYPE_STRING, description="State"),
                "zipcode": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Zip code"
                ),
                "country": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Country"
                ),
                "logo": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Base64 encoded logo"
                ),
            },
            required=["fullname", "email", "password", "role"],
        ),
        responses={201: "User registered successfully", 400: "Invalid data"},
        operation_summary="Register User",
        operation_description="Register a new user with organization details.",
    )
    def post(self, request):
        role = request.data.get("role")
        email = request.data.get("email")
        password = request.data.get("password")

        if role not in ["Admin", "User"]:
            return Response(
                {"error": "Invalid role. Allowed roles are 'Admin' and 'User'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle user creation
        user_data = {
            "full_name": request.data.get("fullname"),
            "email": email,
            "password": make_password(password),
            "role": role,
            "organization": request.data.get("organization"),
            "phone": request.data.get("phone"),
            "address": request.data.get("address"),
            "state": request.data.get("state"),
            "zipcode": request.data.get("zipcode"),
            "country": request.data.get("country"),
            "logo": request.data.get("logo"),  # Base64 encoded logo
            "is_active": 1,
            "is_deleted": 0,
            "created_by": None,
            "updated_by": None,
        }
        user_serializer = UserSerializer(data=user_data)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPI(APIView):
    permission_classes = [AllowAny]

    def get_ability_rules(self, role):
        """Helper method to return ability rules based on user role"""
        if role == "Admin" or role == "User":
            return [
                {
                    "action": "manage",
                    "subject": "all",
                }
            ]
        else:
            return []

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User's email"
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User's password"
                ),
            },
            required=["email", "password"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "refresh": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Refresh token"
                    ),
                    "access": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Access token"
                    ),
                    "user_id": openapi.Schema(
                        type=openapi.TYPE_INTEGER, description="User ID"
                    ),
                    "role": openapi.Schema(
                        type=openapi.TYPE_STRING, description="User role"
                    ),
                    "userData": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(
                                type=openapi.TYPE_INTEGER, description="User ID"
                            ),
                            "fullName": openapi.Schema(
                                type=openapi.TYPE_STRING, description="Full name"
                            ),
                            "username": openapi.Schema(
                                type=openapi.TYPE_STRING, description="Username"
                            ),
                            "email": openapi.Schema(
                                type=openapi.TYPE_STRING, description="Email"
                            ),
                            "avatar": openapi.Schema(
                                type=openapi.TYPE_STRING, description="Avatar URL"
                            ),
                            "role": openapi.Schema(
                                type=openapi.TYPE_STRING, description="User role"
                            ),
                            "organization": openapi.Schema(
                                type=openapi.TYPE_STRING, description="Organization"
                            ),
                            "abilityRules": openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "action": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="Action",
                                        ),
                                        "subject": openapi.Schema(
                                            type=openapi.TYPE_STRING,
                                            description="Subject",
                                        ),
                                    },
                                ),
                            ),
                        },
                    ),
                },
            ),
            401: "Invalid credentials",
        },
        operation_summary="Login API",
        operation_description="Allows users to log in and returns JWT tokens along with user details.",
    )
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        try:
            # Fetch the user
            user = User.objects.filter(email=email, is_active=1, is_deleted=0).first()
            if not user:
                return Response(
                    {"error": "Email not found"}, status=status.HTTP_404_NOT_FOUND
                )

            if not user.check_password(password):
                return Response(
                    {"error": "Incorrect password"}, status=status.HTTP_401_UNAUTHORIZED
                )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            refresh["user_id"] = user.user_id
            refresh["role"] = user.role

            # Get ability rules based on user role
            ability_rules = self.get_ability_rules(user.role)

            # Construct userData response
            userData = {
                "id": user.user_id,
                "fullName": user.full_name if user.full_name else "User",
                "username": user.email.split("@")[0] if user.email else "user",
                "email": user.email if user.email else "user@example.com",
                "avatar": f"{settings.MEDIA_URL}{user.logo_path}"
                if user.logo_path
                else "/static/images/default-avatar.png",
                "role": user.role if user.role else "User",
                "organization": user.organization,
                "abilityRules": ability_rules,
            }

            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user_id": user.user_id,
                    "role": user.role,
                    "userData": userData,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RequestPasswordResetAPI(APIView):
    """Request a password reset link via email."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User's email address"
                ),
            },
            required=["email"],
        ),
        responses={
            200: openapi.Response(description="Reset link sent successfully"),
            404: "User not found",
            500: "Internal server error",
        },
    )
    def post(self, request):
        try:
            email = request.data.get("email")
            if not email:
                return Response(
                    {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.filter(email=email, is_active=1, is_deleted=0).first()

            if not user:
                return Response(
                    {"error": "No active account found with this email"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Generate secure token
            signer = TimestampSigner()
            token = signer.sign(user.user_id)

            # Create reset link
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            # Prepare email content
            subject = "Password Reset Request"
            message = f"Click the link below to reset your password. This link will expire in 1 hour.\n\n{reset_url}"
            html_message = get_password_reset_template(reset_url, user.full_name)

            # Send email
            email_helper = EmailHelper()
            email_sent = email_helper.send_email(
                subject=subject,
                message=message,
                recipient_list=[email],
                html_message=html_message,
            )

            if email_sent:
                return Response(
                    {"message": "Password reset link has been sent to your email"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Failed to send reset email"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(f"Error in password reset request: {e!s}")
            return Response(
                {"error": "An error occurred while processing your request"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResetPasswordAPI(APIView):
    """Reset password using the token from email."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "token": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Reset token from email"
                ),
                "new_password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="New password"
                ),
            },
            required=["token", "new_password"],
        ),
        responses={
            200: openapi.Response(description="Password reset successfully"),
            400: "Invalid token or password",
            500: "Internal server error",
        },
    )
    def post(self, request):
        try:
            token = request.data.get("token")
            new_password = request.data.get("new_password")

            if not all([token, new_password]):
                return Response(
                    {"error": "Token and new password are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify token
            signer = TimestampSigner()
            try:
                user_id = signer.unsign(token, max_age=3600)
                user = User.objects.get(user_id=user_id, is_active=1, is_deleted=0)
            except (SignatureExpired, BadSignature, User.DoesNotExist):
                return Response(
                    {"error": "Invalid or expired reset token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update password
            user.set_password(new_password)
            user.updated_at = timezone.now()
            user.save()

            # Send confirmation email
            email_helper = EmailHelper()
            subject = "Password Reset Successful"
            message = "Your password has been successfully reset. If you did not make this change, please contact support immediately."

            email_helper.send_email(
                subject=subject,
                message=message,
                recipient_list=[user.email],
                html_message=get_generic_email_template(
                    message=message, title="Password Reset Successful"
                ),
            )

            return Response(
                {"message": "Password has been reset successfully"},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in password reset: {e!s}")
            return Response(
                {"error": "An error occurred while resetting password"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChangeUserPasswordAPI(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "old_password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Old password"
                ),
                "new_password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="New password"
                ),
            },
            required=["old_password", "new_password"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Success message"
                    ),
                },
            ),
            400: "Invalid request or incorrect old password",
            404: "User not found",
            500: "Internal server error",
        },
        operation_summary="Change User Password",
        operation_description="API to change a user's password with validation of old password.",
    )
    def put(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID not found in the request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not all([old_password, new_password]):
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.filter(
                user_id=user_id, is_active=1, is_deleted=0
            ).first()

            if not user:
                return Response(
                    {"error": "User not found or inactive"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not user.check_password(old_password):
                return Response(
                    {"error": "Current password is incorrect"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(new_password)
            user.updated_at = timezone.now()
            user.save()

            return Response(
                {"message": "Password updated successfully"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeactivateUserAPI(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="User ID"
                ),
            },
            required=["user_id"],
        ),
        responses={
            200: "User deactivated successfully",
            404: "User not found",
        },
        operation_summary="Deactivate user",
        operation_description="API to deactivate a user account.",
    )
    def post(self, request):
        user_id = request.data.get("user_id")
        try:
            user = User.objects.get(user_id=user_id, is_active=1)
            user.is_active = 0
            user.updated_at = timezone.now()
            user.save()
            return Response(
                {"message": "User deactivated successfully"}, status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class SendEmailAPI(APIView):
    """Generic email sending endpoint with HTML template support."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser]

    @swagger_auto_schema(
        operation_description="Send email with optional attachment and HTML template",
        manual_parameters=[
            openapi.Parameter(
                "from_email",
                openapi.IN_FORM,
                description="Sender email (optional)",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "to_email",
                openapi.IN_FORM,
                description="Recipient email(s) (optional, defaults to support@duedoom.com)",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "subject",
                openapi.IN_FORM,
                description="Email subject",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "message",
                openapi.IN_FORM,
                description="Email message",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "attachment",
                openapi.IN_FORM,
                description="File attachment (optional)",
                type=openapi.TYPE_FILE,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response("Email sent successfully"),
            400: "Bad request",
            500: "Internal server error",
        },
    )
    def post(self, request):
        try:
            from_email = request.data.get("from_email")
            to_email = request.data.get(
                "to_email", getattr(settings, "SUPPORT_EMAIL", "support@example.com")
            )
            subject = request.data.get("subject")
            message = request.data.get("message")
            attachment = request.FILES.get("attachment")

            if not subject or not message:
                return Response(
                    {"error": "Subject and message are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            to_emails = [
                email.strip() for email in to_email.split(",") if email.strip()
            ]
            if not to_emails:
                to_emails = [getattr(settings, "SUPPORT_EMAIL", "support@example.com")]

            if from_email:
                try:
                    validate_email(from_email)
                except ValueError:
                    return Response({"error": "Invalid sender email"}, status=400)

            html_message = get_generic_email_template(
                message=message, title=subject, has_attachment=bool(attachment)
            )

            email_helper = EmailHelper()

            attachments = None
            if attachment:
                attachments = [
                    {
                        "filename": attachment.name,
                        "content": attachment.read(),
                        "mimetype": attachment.content_type,
                    }
                ]

            email_sent = email_helper.send_email(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=to_emails,
                html_message=html_message,
                attachments=attachments,
            )

            if email_sent:
                return Response(
                    {"message": "Email sent successfully"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Failed to send email"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(f"Error sending email: {e!s}")
            return Response(
                {"error": f"Error sending email: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def get_password_reset_template(reset_url: str, username: str = "User") -> str:
    """HTML template specifically for password reset emails"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Reset Request</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; line-height: 1.6; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header -->
            <div style="background-color: #00796B; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Password Reset Request</h1>
            </div>

            <!-- Content -->
            <div style="background-color: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <!-- Greeting -->
                <div style="margin-bottom: 20px; color: #444444;">
                    <h2 style="margin: 0 0 10px 0; color: #333333;">Hello {username},</h2>
                    <p>We received a request to reset your password. If you didn't make this request, you can safely ignore this email.</p>
                </div>

                <!-- Reset Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="
                        background-color: #00796B;
                        color: #ffffff;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 4px;
                        display: inline-block;
                        font-weight: bold;
                    ">Reset Password</a>
                </div>

                <!-- Additional Info -->
                <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #00796B;">
                    <p style="margin: 0; color: #666666;">
                        <strong>Please Note:</strong><br>
                        • This link will expire in 1 hour<br>
                        • For security reasons, please reset your password immediately
                    </p>
                </div>
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding-top: 20px; color: #666666; font-size: 12px;">
                <p>This is an automated message from your Template Platform. Please do not reply.</p>
                <p>If you didn't request a password reset, please contact support.</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_generic_email_template(
    message: str, title: str | None = None, has_attachment: bool = False
) -> str:
    """Generic HTML template for emails"""
    attachment_notice = (
        """
    <div style="background-color: #f8f9fa; border-left: 4px solid #00796B; padding: 15px; margin-bottom: 20px;">
        <p style="margin: 0; color: #444444;">
            <strong>📎 Attachment:</strong><br>
            Please find the attached file with this email.
        </p>
    </div>
    """
        if has_attachment
        else ""
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title or "Notification"}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; line-height: 1.6; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header -->
            <div style="background-color: #00796B; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Notification</h1>
                {f'<p style="color: #ffffff; margin: 10px 0 0 0; font-size: 16px;">{title}</p>' if title else ""}
            </div>

            <!-- Content -->
            <div style="background-color: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <!-- Message -->
                <div style="margin-bottom: 30px; color: #444444;">
                    {message}
                </div>

                {attachment_notice}
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding-top: 20px; color: #666666; font-size: 12px;">
                <p>This is an automated message from the system.</p>
                <p>Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
