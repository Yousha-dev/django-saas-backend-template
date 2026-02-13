import logging

from django.db import transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.models import FeatureFlags, Payment, Subscription, User
from myapp.permissions import IsUserAccess
from myapp.serializers.admin_serializers import (
    PaymentSerializer,
    SubscriptionSerializer,
)
from myapp.serializers.auth_serializers import UserSerializer
from myapp.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class GetUserAPI(APIView):
    """
    Retrieve a user's profile information including logo URL and organization details.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get user profile details including organization information.",
        responses={
            200: UserSerializer,
            404: openapi.Response(
                description="User not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Error message"
                        )
                    },
                ),
            ),
            500: "Internal server error",
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = self.get_object(user_id)
            if not user:
                return Response(
                    {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )

            serializer = UserSerializer(user)
            return Response(
                {
                    "message": "User profile retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Error retrieving user profile: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_object(self, user_id):
        try:
            return User.objects.get(user_id=user_id, is_deleted=0)
        except User.DoesNotExist:
            return None


class UpdateUserAPI(APIView):
    """
    Edit a user's information including logo and organization details.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Edit an existing user's profile and organization details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "fullname": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User full name"
                ),
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User email"
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
                "isactive": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Is active"
                ),
                "useusersmtp": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Use custom SMTP (1=true, 0=false)",
                ),
                "smtphost": openapi.Schema(
                    type=openapi.TYPE_STRING, description="SMTP host server"
                ),
                "smtpport": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="SMTP port number (1-65535)"
                ),
                "smtphostuser": openapi.Schema(
                    type=openapi.TYPE_STRING, description="SMTP username"
                ),
                "smtphostpassword": openapi.Schema(
                    type=openapi.TYPE_STRING, description="SMTP password"
                ),
                "smtpusetls": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Use TLS for SMTP (1=true, 0=false)",
                ),
            },
            required=["fullname", "email"],
        ),
        responses={
            200: UserSerializer,
            404: "User not found",
            400: "Validation error",
            500: "Internal server error",
        },
    )
    def put(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = self.get_object(user_id)
            if not user:
                return Response(
                    {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Update the updatedat and updatedby fields
            data = request.data.copy()
            data["updated_at"] = timezone.now()
            data["updated_by"] = user_id

            serializer = UserSerializer(user, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "User updated successfully", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {"error": f"Error updating user: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_object(self, user_id):
        try:
            return User.objects.get(user_id=user_id, is_deleted=0)
        except User.DoesNotExist:
            return None


class GetUserPaymentsAPI(APIView):
    """
    Get all payments for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get all payments for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by start date (YYYY-MM-DD)",
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by end date (YYYY-MM-DD)",
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by payment status",
                required=False,
            ),
            openapi.Parameter(
                "payment_method",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by payment method",
                required=False,
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "total_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                    "data": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT),
                    ),
                },
            ),
            400: "Bad Request",
            500: "Internal Server Error",
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get query parameters for filtering
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            payment_status = request.query_params.get("status")
            payment_method = request.query_params.get("payment_method")

            # Get all active payments for the user's subscriptions
            queryset = Payment.objects.filter(
                subscription__user=user_id, is_active=1, is_deleted=0
            ).select_related("subscription", "subscription__subscription_plan")

            # Apply date filters
            if start_date:
                queryset = queryset.filter(payment_date__gte=start_date)
            if end_date:
                queryset = queryset.filter(payment_date__lte=end_date)

            # Apply status filter
            if payment_status:
                queryset = queryset.filter(status=payment_status)

            # Apply payment method filter
            if payment_method:
                queryset = queryset.filter(payment_method=payment_method)

            # Order by payment date (newest first)
            queryset = queryset.order_by("-payment_date")

            serializer = PaymentSerializer(queryset, many=True)

            # Calculate total amount
            total_amount = sum(
                float(payment.amount) for payment in queryset if payment.amount
            )

            return Response(
                {
                    "message": "Payments retrieved successfully",
                    "count": queryset.count(),
                    "total_amount": total_amount,
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in GetUserPaymentsAPI: {e!s}")
            return Response(
                {"error": f"An unexpected error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ListBillingHistoryAPI(APIView):
    """
    Get billing history for subscriptions for the authenticated user.
    Includes payment details and subscription information.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get billing history for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                "start_date",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by start date (YYYY-MM-DD)",
                required=False,
            ),
            openapi.Parameter(
                "end_date",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by end date (YYYY-MM-DD)",
                required=False,
            ),
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by payment status",
                required=False,
            ),
            openapi.Parameter(
                "limit",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="Limit number of results",
                required=False,
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "total_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                    "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "data": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "payment_details": openapi.Schema(
                                    type=openapi.TYPE_OBJECT
                                ),
                                "subscription_details": openapi.Schema(
                                    type=openapi.TYPE_OBJECT
                                ),
                                "payment_type": openapi.Schema(
                                    type=openapi.TYPE_STRING
                                ),
                                "payment_date": openapi.Schema(
                                    type=openapi.TYPE_STRING
                                ),
                            },
                        ),
                    ),
                },
            ),
            400: "Bad Request",
            500: "Internal Server Error",
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get query parameters
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            payment_status = request.query_params.get("status")
            limit = request.query_params.get("limit")

            # Base query for subscription payments
            subscription_payments = Payment.objects.filter(
                subscription__user=user_id, is_active=1, is_deleted=0
            ).select_related("subscription", "subscription__subscription_plan")

            # Apply date filters if provided
            if start_date:
                subscription_payments = subscription_payments.filter(
                    payment_date__gte=start_date
                )
            if end_date:
                subscription_payments = subscription_payments.filter(
                    payment_date__lte=end_date
                )

            # Apply status filter if provided
            if payment_status:
                subscription_payments = subscription_payments.filter(
                    status=payment_status
                )

            # Prepare billing history
            billing_history = []
            total_amount = 0

            # Process subscription payments
            for payment in subscription_payments:
                try:
                    payment_data = PaymentSerializer(payment).data
                    subscription_data = SubscriptionSerializer(
                        payment.subscription
                    ).data

                    billing_history.append(
                        {
                            "payment_details": payment_data,
                            "subscription_details": subscription_data,
                            "payment_type": "subscription",
                            "payment_date": payment.payment_date.isoformat()
                            if payment.payment_date
                            else None,
                            "amount": float(payment.amount) if payment.amount else 0,
                            "subscription_plan_name": getattr(
                                payment.subscription.subscription_plan, "name", "N/A"
                            )
                            if payment.subscription
                            and payment.subscription.subscription_plan
                            else "N/A",
                        }
                    )
                    total_amount += float(payment.amount) if payment.amount else 0
                except Exception as e:
                    logger.error(
                        f"Error processing subscription payment {payment.payment_id}: {e!s}"
                    )
                    continue

            # Sort combined history by payment date (newest first)
            billing_history.sort(key=lambda x: x["payment_date"] or "", reverse=True)

            # Apply limit if specified
            if limit:
                try:
                    limit = int(limit)
                    billing_history = billing_history[:limit]
                except ValueError:
                    pass

            return Response(
                {
                    "message": "Billing history retrieved successfully",
                    "total_amount": round(total_amount, 2),
                    "count": len(billing_history),
                    "data": billing_history,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in ListBillingHistoryAPI: {e!s}")
            return Response(
                {"error": f"An unexpected error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetAvailableSubscriptionPlansAPI(APIView):
    """Get all available subscription plans"""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get all available subscription plans for user to choose from.",
        manual_parameters=[
            openapi.Parameter(
                "include_current",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                description="Include user's current plan in the results",
                required=False,
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "current_plan": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "available_plans": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT),
                    ),
                },
            )
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = User.objects.get(user_id=user_id, is_deleted=0)
            include_current = (
                request.query_params.get("include_current", "false").lower() == "true"
            )

            # Get user's current subscription info using updated service
            current_features = SubscriptionService.get_subscription_features(user)
            current_plan_id = current_features["plan_id"]

            # Get all available plans using updated service
            all_plans = SubscriptionService.get_available_plans()

            # Filter out current plan if requested
            if not include_current:
                available_plans = [
                    plan for plan in all_plans if plan["plan_id"] != current_plan_id
                ]
            else:
                available_plans = all_plans

            # Add comparison info for each plan
            for plan in available_plans:
                plan["is_current_plan"] = plan["plan_id"] == current_plan_id

                # Add upgrade/downgrade info using updated service
                is_upgrade, upgrade_info = SubscriptionService.is_plan_upgrade(
                    user, plan["plan_id"]
                )
                plan["change_type"] = upgrade_info.get("change_type", "unknown")
                plan["price_difference"] = upgrade_info.get("price_difference", 0)
                plan["is_valid_change"] = is_upgrade

            return Response(
                {
                    "message": "Available subscription plans retrieved successfully",
                    "current_plan": {
                        "plan_id": current_features["plan_id"],
                        "plan_name": current_features["plan_name"],
                        "monthly_price": current_features["monthly_price"],
                    },
                    "available_plans": available_plans,
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching available plans for user {user_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChangeSubscriptionPlanAPI(APIView):
    """Change user's subscription plan"""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Change user's subscription to a different plan.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "plan_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of the subscription plan to change to",
                ),
                "billing_frequency": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[
                        "Monthly",
                        "Yearly",
                        "Weekly",
                        "Semi-Annually",
                        "Quarterly",
                        "One-Time",
                    ],
                    description="Billing frequency (optional, keeps current if not specified)",
                ),
            },
            required=["plan_id"],
        ),
        responses={
            200: "Subscription plan changed successfully",
            400: "Invalid request",
            404: "Plan not found",
        },
    )
    @transaction.atomic
    def post(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = User.objects.get(user_id=user_id, is_deleted=0)

            plan_id = request.data.get("plan_id")
            billing_frequency = request.data.get("billing_frequency")

            if not plan_id:
                return Response(
                    {"error": "plan_id is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Check if the plan exists and is active using updated service
            available_plans = SubscriptionService.get_available_plans()
            new_plan = next(
                (plan for plan in available_plans if plan["plan_id"] == plan_id), None
            )

            if not new_plan:
                return Response(
                    {"error": "Subscription plan not found or inactive"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get current subscription details
            current_features = SubscriptionService.get_subscription_features(user)

            # Check if it's the same plan
            if current_features["plan_id"] == plan_id:
                return Response(
                    {"message": "You are already subscribed to this plan"},
                    status=status.HTTP_200_OK,
                )

            # Get plan comparison info using updated service
            is_valid, comparison_info = SubscriptionService.is_plan_upgrade(
                user, plan_id
            )

            if not is_valid:
                return Response(
                    {"error": comparison_info.get("error", "Invalid plan comparison")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # For paid upgrades, check if payment processing is enabled
            # if (comparison_info['change_type'] == 'upgrade' and
            #     comparison_info['price_difference'] > 0 and
            #     not getattr(settings, 'STRIPE_ENABLED', False)):
            #     return Response({
            #         'error': 'Payment processing is currently disabled. Please contact support to complete your subscription change.',
            #         'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com')
            #     }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # Change the subscription plan using updated service
            success, message = SubscriptionService.change_user_subscription_plan(
                user, plan_id
            )

            if success:
                # Update billing frequency if provided
                if billing_frequency:
                    current_subscription = SubscriptionService.get_user_subscription(
                        user
                    )
                    current_subscription.billing_frequency = billing_frequency
                    current_subscription.updated_at = timezone.now()
                    current_subscription.updated_by = user_id
                    current_subscription.save()

                return Response(
                    {
                        "message": message,
                        "plan_change_info": comparison_info,
                        "new_plan": new_plan,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error changing subscription plan for user {user_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetUserSubscriptionAPI(APIView):
    """Get user's subscription details"""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get authenticated user's subscription details.",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "subscription": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "usage_stats": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "features": openapi.Schema(type=openapi.TYPE_OBJECT),
                },
            ),
            404: "User not found",
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = User.objects.get(user_id=user_id, is_deleted=0)

            # Get subscription using updated service
            subscription = SubscriptionService.get_user_subscription(user)
            features = SubscriptionService.get_subscription_features(user)
            stats = SubscriptionService.get_subscription_stats(user)

            # Serialize subscription data
            serializer = SubscriptionSerializer(subscription)

            return Response(
                {
                    "message": "Subscription details retrieved successfully",
                    "data": {
                        "subscription": serializer.data,
                        "features": features,
                        "usage_stats": stats,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching subscription for user {user_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Add new API for subscription health check
class SubscriptionHealthCheckAPI(APIView):
    """Check subscription health and renewal status"""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Check subscription health, renewal status, and upcoming renewals.",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "subscription_status": openapi.Schema(type=openapi.TYPE_STRING),
                    "isactive": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "days_until_renewal": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "next_renewal_date": openapi.Schema(type=openapi.TYPE_STRING),
                    "renewal_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                    "requires_payment": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                },
            )
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = User.objects.get(user_id=user_id, is_deleted=0)

            # Get subscription health info
            subscription = SubscriptionService.get_user_subscription(user)
            features = SubscriptionService.get_subscription_features(user)

            # Calculate renewal information
            health_info = {
                "subscription_status": "active"
                if subscription.is_active
                else "inactive",
                "isactive": bool(subscription.is_active),
                "plan_name": features["plan_name"],
                "billing_frequency": subscription.billing_frequency,
                "start_date": subscription.start_date.isoformat()
                if subscription.start_date
                else None,
                "end_date": subscription.end_date.isoformat()
                if subscription.end_date
                else None,
            }

            # Calculate days until renewal if subscription has an end date
            if subscription.end_date:
                from datetime import date

                today = date.today()
                days_until_renewal = (subscription.end_date - today).days
                health_info["days_until_renewal"] = days_until_renewal
                health_info["next_renewal_date"] = subscription.end_date.isoformat()

                # Determine renewal status
                if days_until_renewal <= 0:
                    health_info["subscription_status"] = "expired"
                elif days_until_renewal <= 7:
                    health_info["subscription_status"] = "expiring_soon"

                # Estimate renewal amount (you might want to calculate this differently)
                health_info["renewal_amount"] = features.get("monthly_price", 0)
                health_info["requires_payment"] = features.get("monthly_price", 0) > 0
            else:
                health_info["days_until_renewal"] = None
                health_info["next_renewal_date"] = None
                health_info["renewal_amount"] = 0
                health_info["requires_payment"] = False

            return Response(
                {"message": "Subscription health check completed", "data": health_info},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error checking subscription health for user {user_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetUserSubscriptionStatsAPI(APIView):
    """Get comprehensive subscription statistics for user"""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get comprehensive subscription statistics for the authenticated user.",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "subscription": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "api_limits": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "exchange_limits": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "features_available": openapi.Schema(type=openapi.TYPE_OBJECT),
                },
            ),
            404: "User not found",
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = User.objects.get(user_id=user_id, is_deleted=0)
            stats = SubscriptionService.get_subscription_stats(user)

            return Response(
                {
                    "message": "Subscription statistics retrieved successfully",
                    "data": stats,
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching subscription stats for user {user_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CheckSubscriptionLimitsAPI(APIView):
    """Check user's subscription limits for various features"""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Check user's subscription limits for API calls, operations, and features.",
        manual_parameters=[
            openapi.Parameter(
                "check_type",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=[
                    "api_limit",
                    "operation_limit",
                    "all",
                ],
                description="Type of limit to check",
                required=False,
            )
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "limits": openapi.Schema(type=openapi.TYPE_OBJECT),
                },
            )
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            user = User.objects.get(user_id=user_id, is_deleted=0)
            check_type = request.query_params.get("check_type", "all")

            limits = {}

            if check_type in ["api_limit", "all"]:
                can_make_call, api_info = SubscriptionService.check_api_limit(user)
                limits["api_limit"] = {"can_make_call": can_make_call, **api_info}

            if check_type in ["operation_limit", "all"]:
                can_operate, operation_info = SubscriptionService.check_operation_limit(
                    user
                )
                operation_data = {"can_operate": can_operate}
                if isinstance(operation_info, dict):
                    operation_data.update(operation_info)
                else:
                    operation_data["message"] = str(operation_info)
                limits["operation_limit"] = operation_data

            return Response(
                {
                    "message": "Subscription limits retrieved successfully",
                    "limits": limits,
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error checking subscription limits for user {user_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetFeatureFlagsAPI(APIView):
    """
    Get feature flags for the authenticated user's subscription plan.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get feature flags for the user's current subscription plan.",
        responses={200: "Feature flags for user's plan"},
    )
    def get(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = User.objects.get(user_id=user_id)

            # Get user's active subscription
            subscription = (
                Subscription.objects.filter(user=user, status="Active", is_deleted=0)
                .select_related("subscription_plan")
                .first()
            )

            if not subscription:
                return Response(
                    {
                        "message": "No active subscription found",
                        "data": {"features": {}},
                    },
                    status=status.HTTP_200_OK,
                )

            # Get feature flags for the plan
            try:
                flags = FeatureFlags.objects.get(
                    subscription_plan=subscription.subscription_plan
                )
                features = flags.get_all_features()
            except FeatureFlags.DoesNotExist:
                features = {}

            return Response(
                {
                    "message": "Feature flags retrieved successfully",
                    "data": {
                        "plan": subscription.subscription_plan.name,
                        "features": features,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting feature flags for user {user_id}: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
