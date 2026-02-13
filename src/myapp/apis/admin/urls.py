from django.urls import include, path

from myapp.apis.admin.admin_api import (
    EditUserAPI,
    GetAllUsersAPI,
    GetDashboardStatsAPI,
    GetPaymentsAPI,
    ListUsersAPI,
)
from myapp.apis.admin.analytics_api import DashboardStatsAPI
from myapp.apis.admin.moderation_api import (
    ModerationActionAPI,
    ModerationAppealAPI,
    ModerationHistoryAPI,
    ModerationQueueAPI,
)

urlpatterns = [
    path("subscriptions/", include("myapp.apis.admin.subscriptions.urls")),
    path("subscriptionplans/", include("myapp.apis.admin.subscriptionplans.urls")),
    path("users/", ListUsersAPI.as_view(), name="list_users"),
    path("users/<int:user_id>/edit-user", EditUserAPI.as_view(), name="edit_user"),
    path("all-users/", GetAllUsersAPI.as_view(), name="get_all_users"),
    path("payments/", GetPaymentsAPI.as_view(), name="get_payments"),
    path("dashboard/stats/", GetDashboardStatsAPI.as_view(), name="dashboard_stats"),
    # Analytics
    path(
        "analytics/dashboard/", DashboardStatsAPI.as_view(), name="analytics_dashboard"
    ),
    # Moderation
    path("moderation/queue/", ModerationQueueAPI.as_view(), name="moderation_queue"),
    path("moderation/action/", ModerationActionAPI.as_view(), name="moderation_action"),
    path(
        "moderation/history/", ModerationHistoryAPI.as_view(), name="moderation_history"
    ),
    path("moderation/appeal/", ModerationAppealAPI.as_view(), name="moderation_appeal"),
]
