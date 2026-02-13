import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.models import Payment, Subscription
from myapp.permissions import IsUserAccess
from myapp.serializers.admin_serializers import (
    RenewalSerializer,
    SubscriptionSerializer,
)

logger = logging.getLogger(__name__)


### 1. Create Subscription API ###
class CreateSubscriptionAPI(APIView):
    """
    Create a new subscription for a user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Create a new subscription for a user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="User ID"
                ),
                "subscription_plan_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Subscription Plan ID"
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
                    description="Billing frequency",
                ),
                "start_date": openapi.Schema(
                    type=openapi.TYPE_STRING, format="date", description="Start date"
                ),
                "end_date": openapi.Schema(
                    type=openapi.TYPE_STRING, format="date", description="End date"
                ),
                "auto_renew": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Auto-renewal flag (0 or 1)"
                ),
                "status": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["Active", "Inactive", "Expired", "Cancelled", "Suspended"],
                    description="Subscription status",
                ),
            },
            required=[
                "user_id",
                "subscription_plan_id",
                "billing_frequency",
                "start_date",
                "end_date",
            ],
        ),
        responses={201: SubscriptionSerializer, 400: "Validation errors"},
    )
    def post(self, request):
        user_id = request.data.get("user_id") or getattr(request, "user_id", None)

        # Check if there is already an active subscription for the user
        existing_subscription = Subscription.objects.filter(
            user=user_id, status="Active", is_active=1, is_deleted=0
        ).exists()

        if existing_subscription:
            return Response(
                {"error": "An active subscription already exists for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        data["user"] = user_id
        data["is_active"] = 1
        data["is_deleted"] = 0
        data["created_by"] = getattr(request, "user_id", None)
        data["status"] = data.get("status", "Active")  # Default status

        serializer = SubscriptionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Subscription created successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListSubscriptionsAPI(APIView):
    """
    List subscriptions with comprehensive filtering options.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List subscriptions with filtering options.",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_QUERY,
                description="Filter by user ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "subscription_plan_id",
                openapi.IN_QUERY,
                description="Filter by subscription plan ID",
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
                "payment_id",
                openapi.IN_QUERY,
                description="Filter by payment ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by subscription status",
                type=openapi.TYPE_STRING,
                enum=["Active", "Inactive", "Expired", "Cancelled", "Suspended"],
                required=False,
            ),
            openapi.Parameter(
                "billing_frequency",
                openapi.IN_QUERY,
                description="Filter by billing frequency",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "auto_renew",
                openapi.IN_QUERY,
                description="Filter by auto-renewal setting",
                type=openapi.TYPE_BOOLEAN,
                required=False,
            ),
            openapi.Parameter(
                "expiring_soon",
                openapi.IN_QUERY,
                description="Show subscriptions expiring in next 30 days",
                type=openapi.TYPE_BOOLEAN,
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
        responses={200: SubscriptionSerializer(many=True), 400: "Bad Request"},
    )
    def get(self, request):
        # Get query parameters
        user_id = request.query_params.get("user_id")
        subscription_plan_id = request.query_params.get("subscription_plan_id")
        subscription_id = request.query_params.get("subscription_id")
        payment_id = request.query_params.get("payment_id")
        status_filter = request.query_params.get("status")
        billing_frequency = request.query_params.get("billing_frequency")
        auto_renew = request.query_params.get("auto_renew")
        expiring_soon = request.query_params.get("expiring_soon", "").lower() == "true"
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        # Build filters
        filters = {"is_deleted": 0}

        if user_id:
            filters["user"] = user_id
        if subscription_plan_id:
            filters["subscription_plan"] = subscription_plan_id
        if subscription_id:
            filters["subscription_id"] = subscription_id
        if status_filter:
            filters["status"] = status_filter
        if billing_frequency:
            filters["billing_frequency"] = billing_frequency
        if auto_renew is not None:
            filters["auto_renew"] = 1 if auto_renew.lower() == "true" else 0

        subscriptions = Subscription.objects.filter(**filters)

        # Handle expiring soon filter
        if expiring_soon:
            today = timezone.now().date()
            expiry_threshold = today + timedelta(days=30)
            subscriptions = subscriptions.filter(
                end_date__lte=expiry_threshold, end_date__gte=today, status="Active"
            )

        # Handle payment filter
        if payment_id:
            subscriptions = subscriptions.filter(
                payment__payment_id=payment_id, payment__is_deleted=0
            )

        # Apply ordering and pagination
        subscriptions = subscriptions.distinct().order_by("-created_at")
        total_count = subscriptions.count()
        subscriptions = subscriptions[offset : offset + limit]

        serializer = SubscriptionSerializer(subscriptions, many=True)

        return Response(
            {
                "message": "Subscriptions retrieved successfully",
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


### 3. Update Subscription API ###
class UpdateSubscriptionAPI(APIView):
    """
    Update an existing subscription.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Update an existing subscription.",
        request_body=SubscriptionSerializer,
        responses={
            200: "Subscription updated successfully",
            404: "Subscription not found",
            400: "Validation errors",
        },
    )
    def put(self, request, subscription_id):
        try:
            subscription = Subscription.objects.get(
                subscription_id=subscription_id, is_deleted=0
            )

            data = request.data.copy()
            data["updated_by"] = getattr(request, "user_id", None)

            serializer = SubscriptionSerializer(subscription, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Subscription updated successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND
            )


### 4. Delete Subscription API ###
class DeleteSubscriptionAPI(APIView):
    """
    Soft delete a subscription.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Soft delete a subscription.",
        responses={
            200: "Subscription deleted successfully",
            404: "Subscription not found",
        },
    )
    def delete(self, request, subscription_id):
        try:
            subscription = Subscription.objects.get(
                subscription_id=subscription_id, is_deleted=0
            )

            subscription.is_deleted = 1
            subscription.is_active = 0  # Also mark as inactive
            subscription.status = "Cancelled"
            subscription.updated_by = getattr(request, "user_id", None)
            subscription.updated_at = timezone.now()
            subscription.save()

            return Response(
                {"message": "Subscription deleted successfully."},
                status=status.HTTP_200_OK,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND
            )


### 5. Subscription Analytics API ###
class SubscriptionAnalyticsAPI(APIView):
    """
    Fetch comprehensive analytics data for subscriptions.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Fetch comprehensive analytics data for subscriptions.",
        responses={200: "Analytics data retrieved successfully", 400: "Bad Request"},
    )
    def get(self, request):
        subscriptions = Subscription.objects.filter(is_deleted=0)
        today = timezone.now().date()

        # Basic counts
        total_subscriptions = subscriptions.count()
        active_subscriptions = subscriptions.filter(
            status="Active", is_active=1, end_date__gte=today
        ).count()

        expired_subscriptions = subscriptions.filter(
            Q(status="Expired") | Q(end_date__lt=today)
        ).count()

        cancelled_subscriptions = subscriptions.filter(status="Cancelled").count()
        suspended_subscriptions = subscriptions.filter(status="Suspended").count()

        # Renewal analytics
        auto_renew_enabled = subscriptions.filter(auto_renew=1, status="Active").count()

        # Expiring soon (next 30 days)
        expiring_soon = subscriptions.filter(
            status="Active", end_date__range=[today, today + timedelta(days=30)]
        ).count()

        # Revenue analytics
        revenue_data = Payment.objects.filter(
            subscription__in=subscriptions, status="Completed", is_deleted=0
        ).aggregate(total_revenue=Sum("amount"), avg_payment=Avg("amount"))

        # Subscription by plan
        subscription_by_plan = (
            subscriptions.filter(is_active=1)
            .values("subscription_plan__name")
            .annotate(count=Count("subscription_id"))
            .order_by("-count")
        )

        # Billing frequency distribution
        billing_frequency_dist = (
            subscriptions.filter(status="Active")
            .values("billing_frequency")
            .annotate(count=Count("subscription_id"))
            .order_by("-count")
        )

        # Monthly subscription trends (last 12 months)
        monthly_trends = []
        for i in range(12):
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            month_subscriptions = subscriptions.filter(
                created_at__year=month_date.year, created_at__month=month_date.month
            ).count()
            monthly_trends.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "new_subscriptions": month_subscriptions,
                }
            )
        monthly_trends.reverse()

        analytics = {
            "overview": {
                "total_subscriptions": total_subscriptions,
                "active_subscriptions": active_subscriptions,
                "expired_subscriptions": expired_subscriptions,
                "cancelled_subscriptions": cancelled_subscriptions,
                "suspended_subscriptions": suspended_subscriptions,
                "auto_renew_enabled": auto_renew_enabled,
                "expiring_soon": expiring_soon,
            },
            "revenue": {
                "total_revenue": float(revenue_data["total_revenue"] or 0),
                "average_payment": float(revenue_data["avg_payment"] or 0),
            },
            "distributions": {
                "by_plan": list(subscription_by_plan),
                "by_billing_frequency": list(billing_frequency_dist),
            },
            "trends": {"monthly_new_subscriptions": monthly_trends},
        }

        return Response({"analytics": analytics}, status=status.HTTP_200_OK)


### 6. Subscription Dashboard Overview API ###
class SubscriptionDashboardOverviewAPI(APIView):
    """
    Get dashboard overview for subscriptions.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get dashboard overview for subscriptions with key metrics.",
        responses={200: "Dashboard data retrieved successfully", 400: "Bad Request"},
    )
    def get(self, request):
        subscriptions = Subscription.objects.filter(is_deleted=0)
        today = timezone.now().date()

        # Key metrics
        total_subscriptions = subscriptions.count()
        active_subscriptions = subscriptions.filter(
            status="Active", is_active=1, end_date__gte=today
        ).count()

        expiring_soon = subscriptions.filter(
            status="Active", end_date__range=[today, today + timedelta(days=30)]
        ).count()

        recently_expired = subscriptions.filter(
            Q(status="Expired") | Q(end_date__range=[today - timedelta(days=30), today])
        ).count()

        # Revenue metrics
        this_month_start = today.replace(day=1)
        this_month_revenue = Payment.objects.filter(
            subscription__in=subscriptions,
            payment_date__gte=this_month_start,
            status="Completed",
            is_deleted=0,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        # Growth metrics
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)

        last_month_new_subs = subscriptions.filter(
            created_at__date__gte=last_month_start, created_at__date__lte=last_month_end
        ).count()

        this_month_new_subs = subscriptions.filter(
            created_at__date__gte=this_month_start
        ).count()

        # Calculate growth rate
        growth_rate = 0
        if last_month_new_subs > 0:
            growth_rate = (
                (this_month_new_subs - last_month_new_subs) / last_month_new_subs
            ) * 100

        # Churn rate (simplified)
        monthly_cancellations = subscriptions.filter(
            status="Cancelled", updated_at__date__gte=this_month_start
        ).count()

        churn_rate = (monthly_cancellations / max(active_subscriptions, 1)) * 100

        return Response(
            {
                "key_metrics": {
                    "total_subscriptions": total_subscriptions,
                    "active_subscriptions": active_subscriptions,
                    "expiring_soon": expiring_soon,
                    "recently_expired": recently_expired,
                },
                "revenue": {
                    "this_month_revenue": float(this_month_revenue),
                    "currency": "USD",
                },
                "growth": {
                    "this_month_new_subscriptions": this_month_new_subs,
                    "last_month_new_subscriptions": last_month_new_subs,
                    "growth_rate_percent": round(growth_rate, 2),
                    "churn_rate_percent": round(churn_rate, 2),
                },
            },
            status=status.HTTP_200_OK,
        )


### 7. Renew Subscription API ###
class RenewSubscriptionAPI(APIView):
    """
    Manually renew a subscription.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Manually renew a subscription.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "renewal_cost": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Renewal cost (optional)"
                ),
                "notes": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Renewal notes (optional)"
                ),
            },
        ),
        responses={
            200: "Subscription renewed successfully",
            404: "Subscription not found",
            400: "Validation errors",
        },
    )
    def post(self, request, subscription_id):
        user_id = getattr(request, "user_id", None)

        try:
            subscription = Subscription.objects.get(
                subscription_id=subscription_id, is_deleted=0
            )

            # Calculate new end date based on billing frequency
            current_end_date = subscription.end_date
            billing_frequency = subscription.billing_frequency

            frequency_days = {
                "Weekly": 7,
                "Monthly": 30,
                "Quarterly": 90,
                "Semi-Annually": 180,
                "Yearly": 365,
                "One-Time": 3650,
            }

            days_to_add = frequency_days.get(billing_frequency)
            if not days_to_add:
                return Response(
                    {"error": "Invalid billing frequency for renewal."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Calculate new end date
            new_end_date = current_end_date + timedelta(days=days_to_add)

            # Get renewal cost from request or use plan price
            renewal_cost = request.data.get("renewal_cost")
            if not renewal_cost:
                plan = subscription.subscription_plan
                if billing_frequency == "Yearly" and plan.yearly_price:
                    renewal_cost = plan.yearly_price
                else:
                    renewal_cost = plan.monthly_price

            # Update subscription details
            subscription.end_date = new_end_date
            subscription.renewal_count = (subscription.renewal_count or 0) + 1
            subscription.last_renewed_at = timezone.now()
            subscription.status = "Active"
            subscription.is_active = 1
            subscription.updated_by = user_id
            subscription.updated_at = timezone.now()
            subscription.save()

            # Create renewal record
            renewal_data = {
                "subscription": subscription.subscription_id,
                "renewed_by": user_id,
                "renewal_date": timezone.now(),
                "renewal_cost": renewal_cost,
                "notes": request.data.get("notes", "Manual renewal triggered by user."),
                "is_active": 1,
                "is_deleted": 0,
            }

            renewal_serializer = RenewalSerializer(data=renewal_data)
            if renewal_serializer.is_valid():
                renewal_serializer.save()

                return Response(
                    {
                        "message": "Subscription renewed successfully.",
                        "data": {
                            "subscription": SubscriptionSerializer(subscription).data,
                            "renewal": renewal_serializer.data,
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    renewal_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

        except Subscription.DoesNotExist:
            return Response(
                {"error": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND
            )


### 8. Auto-Renew Subscriptions API ###
class AutoRenewSubscriptionsAPI(APIView):
    """
    Automatically process subscriptions daily for renewal or expiration.
    """

    permission_classes = []  # No permission required for cron job
    authentication_classes = []  # No authentication required

    @swagger_auto_schema(
        operation_description="Automatically renew subscriptions or mark them as expired.",
        responses={
            200: "Auto-renewal process completed successfully",
            500: "Internal server error",
        },
    )
    def post(self, request):
        try:
            today = timezone.now().date()
            current_time = timezone.now()

            # Find subscriptions that need auto-renewal
            auto_renew_subscriptions = Subscription.objects.filter(
                auto_renew=1,
                end_date__lt=today,
                status="Active",
                is_active=1,
                is_deleted=0,
            )

            renewed_count = 0
            renewal_errors = []

            for subscription in auto_renew_subscriptions:
                try:
                    # Calculate new end date
                    billing_frequency = subscription.billing_frequency
                    frequency_days = {
                        "Weekly": 7,
                        "Monthly": 30,
                        "Quarterly": 90,
                        "Semi-Annually": 180,
                        "Yearly": 365,
                        "One-Time": 3650,
                    }

                    days_to_add = frequency_days.get(billing_frequency)
                    if not days_to_add:
                        continue

                    new_end_date = subscription.end_date + timedelta(days=days_to_add)

                    # Determine renewal cost
                    plan = subscription.subscription_plan
                    if billing_frequency == "Yearly" and plan.yearly_price:
                        renewal_cost = plan.yearly_price
                    else:
                        renewal_cost = plan.monthly_price

                    # Update subscription
                    subscription.end_date = new_end_date
                    subscription.renewal_count = (subscription.renewal_count or 0) + 1
                    subscription.last_renewed_at = current_time
                    subscription.status = "Active"
                    subscription.updated_at = current_time
                    subscription.updated_by = None  # System renewal
                    subscription.save()

                    # Create renewal record
                    renewal_data = {
                        "subscription": subscription.subscription_id,
                        "renewed_by": None,  # System renewal
                        "renewal_date": current_time,
                        "renewal_cost": renewal_cost,
                        "notes": "Auto-renewal by system.",
                        "is_active": 1,
                        "is_deleted": 0,
                    }

                    renewal_serializer = RenewalSerializer(data=renewal_data)
                    if renewal_serializer.is_valid():
                        renewal_serializer.save()
                        renewed_count += 1
                    else:
                        renewal_errors.append(
                            {
                                "subscription_id": subscription.subscription_id,
                                "error": renewal_serializer.errors,
                            }
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing auto-renewal for subscription {subscription.subscription_id}: {e!s}"
                    )
                    renewal_errors.append(
                        {
                            "subscription_id": subscription.subscription_id,
                            "error": str(e),
                        }
                    )
                    continue

            # Mark non-auto-renew subscriptions as expired
            expired_subscriptions = Subscription.objects.filter(
                auto_renew=0,
                end_date__lt=today,
                status="Active",
                is_active=1,
                is_deleted=0,
            )

            expired_count = 0
            expiration_errors = []

            for subscription in expired_subscriptions:
                try:
                    subscription.status = "Expired"
                    subscription.is_active = 0
                    subscription.updated_at = current_time
                    subscription.updated_by = None  # System update
                    subscription.save()
                    expired_count += 1
                except Exception as e:
                    logger.error(
                        f"Error marking subscription {subscription.subscription_id} as expired: {e!s}"
                    )
                    expiration_errors.append(
                        {
                            "subscription_id": subscription.subscription_id,
                            "error": str(e),
                        }
                    )
                    continue

            return Response(
                {
                    "message": "Auto-renewal process completed successfully.",
                    "details": {
                        "subscriptions_renewed": renewed_count,
                        "subscriptions_expired": expired_count,
                        "renewal_errors": len(renewal_errors),
                        "expiration_errors": len(expiration_errors),
                        "processed_at": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                    "errors": {
                        "renewal_errors": renewal_errors,
                        "expiration_errors": expiration_errors,
                    }
                    if (renewal_errors or expiration_errors)
                    else None,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            error_msg = f"Error in auto-renewal process: {e!s}"
            logger.error(error_msg)
            return Response(
                {
                    "error": error_msg,
                    "details": {
                        "error_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
