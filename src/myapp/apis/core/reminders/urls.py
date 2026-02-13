from django.urls import path

from .apis import (
    AutoSendReminderEmailAPI,
    CreateReminderAPI,
    DeleteReminderAPI,
    ListRemindersAPI,
    SendReminderEmailAPI,
)

urlpatterns = [
    path("create/", CreateReminderAPI.as_view(), name="create_reminder"),
    path("list/", ListRemindersAPI.as_view(), name="list_reminders"),
    path(
        "<int:reminder_id>/delete/", DeleteReminderAPI.as_view(), name="delete_reminder"
    ),
    path(
        "<int:reminder_id>/send-email-reminder/",
        SendReminderEmailAPI.as_view(),
        name="send_email_reminder",
    ),
    path(
        "auto-send-email-reminder/",
        AutoSendReminderEmailAPI.as_view(),
        name="auto_send_email_reminder",
    ),
]
