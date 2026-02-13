from django.urls import path

from .apis import (
    AutoSendActionEmailEventAPI,
    AutoSendReminderEmailEventAPI,
    CreateEventAPI,
    DeleteEventAPI,
    ListEventsAPI,
    UpdateEventAPI,
)

urlpatterns = [
    path("create/", CreateEventAPI.as_view(), name="create_event"),
    path("list/", ListEventsAPI.as_view(), name="list_events"),
    path("<int:event_id>/update/", UpdateEventAPI.as_view(), name="update_event"),
    path("<int:event_id>/delete/", DeleteEventAPI.as_view(), name="delete_event"),
    path(
        "auto-send-action-email-event",
        AutoSendActionEmailEventAPI.as_view(),
        name="auto_send_action_email_event",
    ),
    path(
        "auto-send-reminder-email-event",
        AutoSendReminderEmailEventAPI.as_view(),
        name="auto_send_reminder_email_event",
    ),
]
