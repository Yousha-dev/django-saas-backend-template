from decimal import Decimal

from django.db.models import Avg, Count, Max, Min, Sum
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.models import Subscription, SubscriptionPlan
from myapp.permissions import IsUserAccess
from myapp.serializers.admin_serializers import SubscriptionPlanSerializer


### 1. Create SubscriptionPlan API ###
class CreateSubscriptionPlanAPI(APIView):
    """
    Create a new subscription plan.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Create a new subscription plan.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Plan name"
                ),
                "description": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Plan description"
                ),
                "monthlyprice": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Monthly price"
                ),
                "yearlyprice": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Yearly price"
                ),
                "max_operations": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Maximum operations allowed per period",
                ),
                "max_api_calls_per_hour": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Max API calls per hour"
                ),
                "feature_details": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Feature details description",
                ),
                "featuredetails": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Detailed features"
                ),
            },
            required=[
                "name",
                "monthlyprice",
                "max_operations",
                "max_api_calls_per_hour",
            ],
        ),
        responses={201: SubscriptionPlanSerializer, 400: "Validation errors"},
    )
    def post(self, request):
        data = request.data.copy()
        data["is_active"] = 1
        data["is_deleted"] = 0
        data["created_by"] = getattr(request, "user_id", None)

        serializer = SubscriptionPlanSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Subscription plan created successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListSubscriptionPlanAPI(APIView):
    """
    List all subscription plans with optional filters.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List all subscription plans with optional filters.",
        manual_parameters=[
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
                "user_id",
                openapi.IN_QUERY,
                description="Filter by User ID",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                "active_only",
                openapi.IN_QUERY,
                description="Show only active plans",
                type=openapi.TYPE_BOOLEAN,
                required=False,
            ),
            openapi.Parameter(
                "min_price",
                openapi.IN_QUERY,
                description="Filter by minimum monthly price",
                type=openapi.TYPE_NUMBER,
                required=False,
            ),
            openapi.Parameter(
                "max_price",
                openapi.IN_QUERY,
                description="Filter by maximum monthly price",
                type=openapi.TYPE_NUMBER,
                required=False,
            ),
        ],
        responses={200: SubscriptionPlanSerializer(many=True), 400: "Bad Request"},
    )
    def get(self, request):
        subscription_plan_id = request.query_params.get("subscription_plan_id")
        subscription_id = request.query_params.get("subscription_id")
        payment_id = request.query_params.get("payment_id")
        user_id = request.query_params.get("user_id")
        active_only = request.query_params.get("active_only", "").lower() == "true"
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        filters = {"is_deleted": 0}

        if active_only:
            filters["is_active"] = 1

        if subscription_plan_id:
            filters["subscription_plan_id"] = subscription_plan_id

        if min_price:
            filters["monthly_price__gte"] = Decimal(min_price)

        if max_price:
            filters["monthly_price__lte"] = Decimal(max_price)

        plans = SubscriptionPlan.objects.filter(**filters)

        if subscription_id:
            plans = plans.filter(subscription__subscription_id=subscription_id)

        if payment_id:
            plans = plans.filter(
                subscription__payment__payment_id=payment_id,
                subscription__payment__is_deleted=0,
            )

        if user_id:
            plans = plans.filter(subscription__user=user_id, subscription__is_deleted=0)

        plans = plans.distinct().order_by("monthly_price")

        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(
            {
                "message": "Subscription plans retrieved successfully",
                "count": plans.count(),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


### 3. Update SubscriptionPlan API ###
class UpdateSubscriptionPlanAPI(APIView):
    """
    Update an existing subscription plan.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Update an existing subscription plan.",
        request_body=SubscriptionPlanSerializer,
        responses={
            200: "SubscriptionPlan updated successfully",
            404: "Plan not found",
            400: "Validation errors",
        },
    )
    def put(self, request, subscription_plan_id):
        try:
            plan = SubscriptionPlan.objects.get(
                subscription_plan_id=subscription_plan_id, is_deleted=0
            )

            data = request.data.copy()
            data["updated_by"] = getattr(request, "user_id", None)

            serializer = SubscriptionPlanSerializer(plan, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Subscription plan updated successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "Subscription plan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


### 4. Delete SubscriptionPlan API ###
class DeleteSubscriptionPlanAPI(APIView):
    """
    Soft delete a subscription plan.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Soft delete a subscription plan.",
        responses={
            200: "SubscriptionPlan deleted successfully",
            404: "SubscriptionPlan not found",
            400: "Cannot delete plan with active subscriptions",
        },
    )
    def delete(self, request, subscription_plan_id):
        try:
            plan = SubscriptionPlan.objects.get(
                subscription_plan_id=subscription_plan_id, is_deleted=0
            )

            # Check if there are active subscriptions using this plan
            active_subscriptions = Subscription.objects.filter(
                subscription_plan=plan, status="Active", is_active=1, is_deleted=0
            ).count()

            if active_subscriptions > 0:
                return Response(
                    {
                        "error": f"Cannot delete plan. {active_subscriptions} active subscription(s) are using this plan."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            plan.is_deleted = 1
            plan.is_active = 0  # Also mark as inactive
            plan.updated_by = getattr(request, "user_id", None)
            plan.updated_at = timezone.now()
            plan.save()

            return Response(
                {"message": "Subscription plan deleted successfully."},
                status=status.HTTP_200_OK,
            )
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "Subscription plan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


### 5. SubscriptionPlan Analytics API ###
class SubscriptionPlanAnalyticsAPI(APIView):
    """
    Fetch analytics data for subscription plans.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Fetch comprehensive analytics data for subscription plans.",
        responses={200: "Analytics data retrieved successfully", 400: "Bad Request"},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_deleted=0)
        active_plans = plans.filter(is_active=1)

        # Basic counts
        total_plans = plans.count()
        active_plans_count = active_plans.count()

        # Price statistics
        price_stats = active_plans.aggregate(
            avg_monthly_price=Avg("monthly_price"),
            min_monthly_price=plans.aggregate(min_price=Min("monthly_price"))[
                "min_price"
            ],
            max_monthly_price=plans.aggregate(max_price=Max("monthly_price"))[
                "max_price"
            ],
            avg_yearly_price=Avg("yearly_price"),
            total_monthly_revenue_potential=Sum("monthly_price"),
        )

        # Feature distribution — count plans that have FeatureFlags configured
        from myapp.models.features import FeatureFlags

        plans_with_flags = FeatureFlags.objects.filter(
            subscription_plan__in=active_plans
        ).count()
        feature_stats = {
            "plans_with_feature_flags": plans_with_flags,
            "plans_without_feature_flags": active_plans_count - plans_with_flags,
        }

        # Operation limits distribution
        operation_limits = (
            active_plans.values("max_operations")
            .annotate(plan_count=Count("subscription_plan_id"))
            .order_by("max_operations")
        )

        # API rate limits distribution
        api_limits = (
            active_plans.values("max_api_calls_per_hour")
            .annotate(plan_count=Count("subscription_plan_id"))
            .order_by("max_api_calls_per_hour")
        )

        # Subscription usage per plan
        plan_usage = []
        for plan in active_plans:
            active_subscriptions = Subscription.objects.filter(
                subscription_plan=plan, status="Active", is_active=1, is_deleted=0
            ).count()

            total_subscriptions = Subscription.objects.filter(
                subscription_plan=plan, is_deleted=0
            ).count()

            plan_usage.append(
                {
                    "plan_id": plan.subscription_plan_id,
                    "plan_name": plan.name,
                    "monthly_price": float(plan.monthly_price),
                    "active_subscriptions": active_subscriptions,
                    "total_subscriptions": total_subscriptions,
                    "monthly_revenue": float(plan.monthly_price * active_subscriptions),
                }
            )

        # Revenue analysis
        total_monthly_revenue = sum(item["monthly_revenue"] for item in plan_usage)

        return Response(
            {
                "analytics": {
                    "overview": {
                        "total_plans": total_plans,
                        "active_plans": active_plans_count,
                        "inactive_plans": total_plans - active_plans_count,
                    },
                    "pricing": {
                        "average_monthly_price": float(
                            price_stats["avg_monthly_price"] or 0
                        ),
                        "minimum_monthly_price": float(
                            price_stats["min_monthly_price"] or 0
                        ),
                        "maximum_monthly_price": float(
                            price_stats["max_monthly_price"] or 0
                        ),
                        "average_yearly_price": float(
                            price_stats["avg_yearly_price"] or 0
                        ),
                        "total_monthly_revenue": total_monthly_revenue,
                    },
                    "features": {
                        "tier_1_enabled": feature_stats["tier1_plans"],
                        "tier_2_enabled": feature_stats["tier2_plans"],
                        "tier_3_enabled": feature_stats["tier3_plans"],
                    },
                    "limits": {
                        "operation_limits_distribution": list(operation_limits),
                        "api_limits_distribution": list(api_limits),
                    },
                    "usage": plan_usage,
                }
            },
            status=status.HTTP_200_OK,
        )


### 6. SubscriptionPlan Dashboard Overview API ###
class SubscriptionPlanDashboardOverviewAPI(APIView):
    """
    Get dashboard overview for subscription plans.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get dashboard overview for subscription plans with key metrics.",
        responses={200: "Dashboard data retrieved successfully", 400: "Bad Request"},
    )
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_deleted=0)
        active_plans = plans.filter(is_active=1)

        total_plans = plans.count()
        active_plans_count = active_plans.count()

        # Get subscription counts and revenue for each plan
        plan_performance = []
        total_active_subscriptions = 0
        total_monthly_revenue = Decimal("0.00")

        for plan in active_plans:
            active_subs = Subscription.objects.filter(
                subscription_plan=plan, status="Active", is_active=1, is_deleted=0
            ).count()

            monthly_revenue = plan.monthly_price * active_subs
            total_active_subscriptions += active_subs
            total_monthly_revenue += monthly_revenue

            plan_performance.append(
                {
                    "plan_id": plan.subscription_plan_id,
                    "plan_name": plan.name,
                    "monthly_price": float(plan.monthly_price),
                    "yearly_price": float(plan.yearly_price)
                    if plan.yearly_price
                    else 0,
                    "active_subscriptions": active_subs,
                    "monthly_revenue": float(monthly_revenue),
                    "max_operations": plan.max_operations,
                    "max_api_calls": plan.max_api_calls_per_hour,
                    "features": getattr(plan, "feature_flags", None).get_all_features()
                    if hasattr(plan, "feature_flags")
                    and getattr(plan, "feature_flags", None)
                    else {},
                }
            )

        # Sort by revenue (highest first)
        plan_performance.sort(key=lambda x: x["monthly_revenue"], reverse=True)

        # Get most popular plan
        most_popular_plan = (
            max(plan_performance, key=lambda x: x["active_subscriptions"])
            if plan_performance
            else None
        )

        # Get highest revenue plan
        highest_revenue_plan = plan_performance[0] if plan_performance else None

        # Calculate average metrics
        avg_price = (
            sum(p["monthly_price"] for p in plan_performance) / len(plan_performance)
            if plan_performance
            else 0
        )

        return Response(
            {
                "overview": {
                    "total_plans": total_plans,
                    "active_plans": active_plans_count,
                    "inactive_plans": total_plans - active_plans_count,
                    "total_active_subscriptions": total_active_subscriptions,
                    "total_monthly_revenue": float(total_monthly_revenue),
                    "average_plan_price": round(avg_price, 2),
                },
                "top_performers": {
                    "most_popular_plan": most_popular_plan,
                    "highest_revenue_plan": highest_revenue_plan,
                },
                "plan_performance": plan_performance[:10],  # Top 10 plans
            },
            status=status.HTTP_200_OK,
        )
