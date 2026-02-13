from django.urls import path

from .api import (
    CreateSubscriptionPlanAPI,
    DeleteSubscriptionPlanAPI,
    ListSubscriptionPlanAPI,
    SubscriptionPlanAnalyticsAPI,
    SubscriptionPlanDashboardOverviewAPI,
    UpdateSubscriptionPlanAPI,
)

urlpatterns = [
    path("list/", ListSubscriptionPlanAPI.as_view(), name="list_subscriptionplans"),
    path(
        "create/", CreateSubscriptionPlanAPI.as_view(), name="create_subscriptionplan"
    ),
    path(
        "<int:subscriptionplan_id>/update/",
        UpdateSubscriptionPlanAPI.as_view(),
        name="update_subscriptionplan",
    ),
    path(
        "<int:subscriptionplan_id>/delete/",
        DeleteSubscriptionPlanAPI.as_view(),
        name="delete_subscriptionplan",
    ),
    path(
        "analytics/",
        SubscriptionPlanAnalyticsAPI.as_view(),
        name="subscriptionplan_analytics",
    ),
    path(
        "dashboard/",
        SubscriptionPlanDashboardOverviewAPI.as_view(),
        name="subscriptionplan_dashboard_overview",
    ),
]
