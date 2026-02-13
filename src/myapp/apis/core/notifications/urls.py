from django.urls import path

from .apis import (
    ClearAllNotificationsAPI,
    CreateNotificationAPI,
    DeleteNotificationAPI,
    ListNotificationsAPI,
    MarkNotificationAsReadAPI,
)

urlpatterns = [
    path("create/", CreateNotificationAPI.as_view(), name="create_notification"),
    path("list/", ListNotificationsAPI.as_view(), name="list_notifications"),
    path(
        "<int:notification_id>/delete/",
        DeleteNotificationAPI.as_view(),
        name="delete_notification",
    ),
    path("clear-all/", ClearAllNotificationsAPI.as_view(), name="clear_notifications"),
    path(
        "<int:notification_id>/mark-as-read/",
        MarkNotificationAsReadAPI.as_view(),
        name="marks_as_read_notification",
    ),
]
