from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.models import Payment, Subscription, SubscriptionPlan, User
from myapp.permissions import IsUserAccess
from myapp.serializers.admin_serializers import (
    PaymentSerializer,
    SubscriptionSerializer,
)
from myapp.serializers.auth_serializers import UserSerializer


class ListUsersAPI(APIView):
    """
    List all users with their organization details.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List all users with their organization details.",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="Filter by user ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "subscriptionid",
                openapi.IN_QUERY,
                description="Filter by subscription ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "paymentid",
                openapi.IN_QUERY,
                description="Filter by payment ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "subscriptionplanid",
                openapi.IN_QUERY,
                description="Filter by subscription plan ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "role",
                openapi.IN_QUERY,
                description="Filter by user role",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "limit",
                openapi.IN_QUERY,
                description="Limit number of results",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "offset",
                openapi.IN_QUERY,
                description="Offset for pagination",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={200: UserSerializer(many=True), 500: "Internal server error"},
    )
    def get(self, request):
        try:
            # Get query parameters
            user_id = request.query_params.get("user_id")
            subscriptionid = request.query_params.get("subscriptionid")
            paymentid = request.query_params.get("paymentid")
            subscriptionplanid = request.query_params.get("subscriptionplanid")
            role = request.query_params.get("role")
            limit = request.query_params.get("limit", 50)
            offset = request.query_params.get("offset", 0)

            # Build filters
            filters = {"is_deleted": 0}
            if user_id:
                filters["user_id"] = user_id
            if role:
                filters["role"] = role

            # Start with base queryset
            users = User.objects.filter(**filters)

            # Apply relationship filters
            if subscriptionid:
                users = users.filter(
                    subscriptions__subscription_id=subscriptionid,
                    subscriptions__is_deleted=0,
                )
            if paymentid:
                users = users.filter(
                    subscriptions__payment__payment_id=paymentid,
                    subscriptions__payment__is_deleted=0,
                )
            if subscriptionplanid:
                users = users.filter(
                    subscriptions__subscription_plan=subscriptionplanid,
                    subscriptions__is_deleted=0,
                )

            # Apply pagination
            users = users.distinct().order_by("-created_at")
            total_count = users.count()
            users = users[int(offset) : int(offset) + int(limit)]

            return Response(
                {
                    "users": UserSerializer(users, many=True).data,
                    "total_count": total_count,
                    "limit": int(limit),
                    "offset": int(offset),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Error fetching users: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EditUserAPI(APIView):
    """
    Edit user details including subscription information.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Edit user and subscription details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "full_name": openapi.Schema(
                            type=openapi.TYPE_STRING, description="User full name"
                        ),
                        "email": openapi.Schema(
                            type=openapi.TYPE_STRING, description="User email"
                        ),
                        "role": openapi.Schema(
                            type=openapi.TYPE_STRING, description="User role"
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
                        "state": openapi.Schema(
                            type=openapi.TYPE_STRING, description="State"
                        ),
                        "zipcode": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Zip code"
                        ),
                        "country": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Country"
                        ),
                        "password": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="User password (optional)",
                        ),
                        "is_active": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Is active flag"
                        ),
                        "is_deleted": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Is deleted flag"
                        ),
                    },
                ),
                "subscription": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "subscription_plan_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description="Subscription plan ID",
                        ),
                        "billing_frequency": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Billing frequency"
                        ),
                        "start_date": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Subscription start date",
                        ),
                        "end_date": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Subscription end date",
                        ),
                        "auto_renew": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Auto-renewal flag"
                        ),
                        "status": openapi.Schema(
                            type=openapi.TYPE_STRING, description="Subscription status"
                        ),
                        "is_active": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Is active flag"
                        ),
                        "is_deleted": openapi.Schema(
                            type=openapi.TYPE_INTEGER, description="Is deleted flag"
                        ),
                    },
                ),
            },
        ),
        responses={
            200: "Update successful",
            400: "Validation error",
            404: "User not found",
            500: "Internal server error",
        },
    )
    @transaction.atomic
    def put(self, request, user_id):
        try:
            # Fetch the user
            user = User.objects.filter(user_id=user_id, is_deleted=0).first()

            if not user:
                return Response(
                    {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )

            current_time = timezone.now()

            # Update user if user data is provided
            if request.data.get("user"):
                user_data = {
                    "updated_at": current_time,
                    "updated_by": getattr(request, "user_id", user.user_id),
                }

                # Update user fields
                allowed_fields = [
                    "full_name",
                    "email",
                    "role",
                    "organization",
                    "phone",
                    "address",
                    "state",
                    "zipcode",
                    "country",
                    "is_active",
                    "is_deleted",
                ]

                for field in allowed_fields:
                    if field in request.data["user"]:
                        user_data[field] = request.data["user"][field]

                # Handle password separately
                if "password" in request.data["user"]:
                    user_data["password"] = make_password(
                        request.data["user"]["password"]
                    )

                user_serializer = UserSerializer(user, data=user_data, partial=True)
                if not user_serializer.is_valid():
                    return Response(
                        user_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
                user_serializer.save()
            # Update subscription if subscription data is provided
            subscription_serializer = None
            if request.data.get("subscription"):
                # Get the active subscription for this user
                subscription = Subscription.objects.filter(
                    user=user_id, is_active=1, is_deleted=0
                ).first()

                if subscription:
                    subscription_data = {
                        "updated_at": current_time,
                        "updated_by": getattr(request, "user_id", user.user_id),
                    }

                    # Update subscription fields
                    allowed_sub_fields = [
                        "subscription_plan_id",
                        "billing_frequency",
                        "start_date",
                        "end_date",
                        "auto_renew",
                        "status",
                        "is_active",
                        "is_deleted",
                    ]

                    for field in allowed_sub_fields:
                        if field in request.data["subscription"]:
                            subscription_data[field] = request.data["subscription"][
                                field
                            ]

                    subscription_serializer = SubscriptionSerializer(
                        subscription, data=subscription_data, partial=True
                    )
                    if not subscription_serializer.is_valid():
                        return Response(
                            subscription_serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    subscription_serializer.save()

            # Prepare response data
            response_data = {
                "message": "Update successful",
                "data": {"user": user_serializer.data},
            }

            # Only include updated data in response
            if subscription_serializer:
                response_data["data"]["subscription"] = subscription_serializer.data

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetAllUsersAPI(APIView):
    """
    Get all users with their organization and subscription information.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "search",
                openapi.IN_QUERY,
                description="Search by name or email",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "role",
                openapi.IN_QUERY,
                description="Filter by user role",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by active status (active/inactive)",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "limit",
                openapi.IN_QUERY,
                description="Limit number of results",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "users": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "user_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, description="User ID"
                                ),
                                "fullname": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Full name"
                                ),
                                "email": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Email"
                                ),
                                "role": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Role"
                                ),
                                "organization": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Organization"
                                ),
                                "phone": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Phone"
                                ),
                                "isactive": openapi.Schema(
                                    type=openapi.TYPE_BOOLEAN, description="Is active"
                                ),
                                "subscription_status": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Subscription status",
                                ),
                                "created_at": openapi.Schema(
                                    type=openapi.TYPE_STRING, description="Created date"
                                ),
                            },
                        ),
                    ),
                    "total_count": openapi.Schema(
                        type=openapi.TYPE_INTEGER, description="Total count"
                    ),
                },
            )
        },
        operation_summary="Get all users",
        operation_description="API to fetch all users with their organization and subscription information.",
    )
    def get(self, request):
        try:
            # Get query parameters
            search = request.query_params.get("search", "")
            role = request.query_params.get("role")
            request.query_params.get("status")
            limit = int(request.query_params.get("limit", 100))

            # Build base queryset
            queryset = User.objects.filter(is_deleted=0)

            # Apply filters

            if role:
                queryset = queryset.filter(role=role)

            # Apply filters
            if search:
                queryset = queryset.filter(
                    Q(full_name__icontains=search) | Q(email__icontains=search)
                )

            # Order and limit results
            queryset = queryset.order_by("-created_at")[:limit]

            user_data = []
            for user in queryset:
                # Get subscription status
                subscription = Subscription.objects.filter(
                    user=user.user_id, is_active=1, is_deleted=0
                ).first()

                user_data.append(
                    {
                        "user_id": user.user_id,
                        "fullname": user.full_name,
                        "email": user.email,
                        "role": user.role,
                        "organization": user.organization,
                        "phone": user.phone,
                        "isactive": user.is_active == 1,
                        "subscription_status": subscription.status
                        if subscription
                        else "No Subscription",
                        "created_at": user.created_at.isoformat()
                        if user.created_at
                        else None,
                    }
                )

            return Response(
                {"users": user_data, "total_count": len(user_data)},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetPaymentsAPI(APIView):
    """
    Get all payments with optional filters.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get all payments with optional filters.",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="Filter by user ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "subscription_id",
                openapi.IN_QUERY,
                description="Filter by subscription ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "paymentid",
                openapi.IN_QUERY,
                description="Filter by payment ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "subscriptionplanid",
                openapi.IN_QUERY,
                description="Filter by subscription plan ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by payment status",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "payment_method",
                openapi.IN_QUERY,
                description="Filter by payment method",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "from_date",
                openapi.IN_QUERY,
                description="Filter payments from date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False,
            ),
            openapi.Parameter(
                "to_date",
                openapi.IN_QUERY,
                description="Filter payments to date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False,
            ),
            openapi.Parameter(
                "limit",
                openapi.IN_QUERY,
                description="Limit number of results",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: PaymentSerializer(many=True),
            400: "Bad Request",
            500: "Internal Server Error",
        },
    )
    def get(self, request):
        try:
            # Start with all active and non-deleted payments
            queryset = Payment.objects.filter(is_active=1, is_deleted=0)

            # Apply filters if provided
            user_id = request.query_params.get("user_id")
            if user_id:
                queryset = queryset.filter(subscription__user=user_id)

            subscription_id = request.query_params.get("subscription_id")
            if subscription_id:
                queryset = queryset.filter(subscription=subscription_id)

            paymentid = request.query_params.get("paymentid")
            if paymentid:
                queryset = queryset.filter(payment_id=paymentid)

            subscriptionplanid = request.query_params.get("subscriptionplanid")
            if subscriptionplanid:
                queryset = queryset.filter(
                    subscription__subscription_plan=subscriptionplanid
                )

            payment_status = request.query_params.get("status")
            if payment_status:
                queryset = queryset.filter(status=payment_status)

            payment_method = request.query_params.get("payment_method")
            if payment_method:
                queryset = queryset.filter(payment_method=payment_method)

            from_date = request.query_params.get("from_date")
            if from_date:
                queryset = queryset.filter(payment_date__gte=from_date)

            to_date = request.query_params.get("to_date")
            if to_date:
                queryset = queryset.filter(payment_date__lte=to_date)

            # Apply limit
            limit = request.query_params.get("limit", 100)
            queryset = queryset.order_by("-payment_date")[: int(limit)]

            # Serialize and return the data
            serializer = PaymentSerializer(queryset, many=True)

            return Response(
                {
                    "message": "Payments retrieved successfully",
                    "count": queryset.count(),
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            return Response(
                {"error": f"Invalid parameter value: {e!s}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetDashboardStatsAPI(APIView):
    """
    Get admin dashboard statistics.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get admin dashboard statistics including users, subscriptions, trades, etc.",
        responses={200: "OK", 500: "Internal Server Error"},
    )
    def get(self, request):
        try:
            # Calculate date ranges
            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Basic counts
            total_users = User.objects.filter(is_deleted=0).count()
            active_subscriptions = Subscription.objects.filter(
                status="Active", is_active=1, is_deleted=0
            ).count()

            # Revenue this month
            revenue_this_month = Payment.objects.filter(
                payment_date__gte=month_start.date(),
                status="Completed",
                is_active=1,
                is_deleted=0,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

            # Subscription distribution
            subscription_distribution = {}
            plans = SubscriptionPlan.objects.filter(is_active=1, is_deleted=0)
            for plan in plans:
                count = Subscription.objects.filter(
                    subscription_plan=plan, status="Active", is_active=1, is_deleted=0
                ).count()
                subscription_distribution[plan.name] = count

            stats_data = {
                "total_users": total_users,
                "active_subscriptions": active_subscriptions,
                "revenue_this_month": revenue_this_month,
                "subscription_distribution": subscription_distribution,
            }

            return Response(
                {
                    "message": "Dashboard statistics retrieved successfully",
                    "data": stats_data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
