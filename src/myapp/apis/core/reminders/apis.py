import logging
from datetime import timedelta

from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.emailhelper import EmailHelper
from myapp.models import Reminder, User
from myapp.permissions import IsUserAccess
from myapp.serializers.core_serializers import ReminderSerializer

logger = logging.getLogger(__name__)


class CreateReminderAPI(APIView):
    """Create a new reminder."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Create a new reminder.",
        request_body=ReminderSerializer,
        responses={201: ReminderSerializer()},
    )
    def post(self, request):
        user_id = getattr(request, "user_id", None)
        data = request.data.copy()
        data["is_active"] = 1
        data["is_deleted"] = 0
        data["user"] = user_id
        data["created_by"] = user_id

        serializer = ReminderSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListRemindersAPI(APIView):
    """List all active reminders for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List all active reminders for the authenticated user.",
        responses={200: ReminderSerializer(many=True)},
    )
    def get(self, request):
        user_id = getattr(request, "user_id", None)
        reminders = Reminder.objects.filter(
            user_id=user_id, is_active=1, is_deleted=0
        ).order_by("timestamp")
        serializer = ReminderSerializer(reminders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteReminderAPI(APIView):
    """Soft delete a reminder."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Soft delete a reminder.",
        responses={200: "Reminder deleted successfully"},
    )
    def delete(self, request, reminder_id):
        user_id = getattr(request, "user_id", None)
        try:
            reminder = Reminder.objects.get(
                reminder_id=reminder_id, user_id=user_id, is_active=1, is_deleted=0
            )

            reminder.is_deleted = 1
            reminder.updated_by = user_id
            reminder.updated_at = timezone.now()
            reminder.save()
            return Response(
                {"message": "Reminder deleted successfully."}, status=status.HTTP_200_OK
            )
        except Reminder.DoesNotExist:
            return Response(
                {"error": "Reminder not found."}, status=status.HTTP_404_NOT_FOUND
            )


class SendReminderEmailAPI(APIView):
    """Manually send email for a specific reminder."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Send email for a specific reminder.",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "reminder_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                },
            ),
            404: "Reminder not found.",
            400: "Bad request.",
            500: "Internal server error.",
        },
    )
    def post(self, request, reminder_id):
        try:
            user_id = getattr(request, "user_id", None)

            # Get the reminder
            reminder = Reminder.objects.filter(
                reminder_id=reminder_id, user_id=user_id, is_active=1, is_deleted=0
            ).first()

            if not reminder:
                return Response(
                    {"error": "Reminder not found or not accessible."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get recipient list
            recipient_list = list(
                User.objects.filter(
                    user_id=reminder.user_id, is_active=1, is_deleted=0
                ).values_list("email", flat=True)
            )

            if not recipient_list:
                return Response(
                    {"error": "No active recipients found for this reminder."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            email_helper = EmailHelper()

            # Prepare email content
            subject = "Reminder Notification"
            html_message = get_reminder_template(reminder_note=reminder.note)

            # Send email
            email_helper.send_email(
                subject=subject,
                message=reminder.note,  # Plain text fallback
                recipient_list=recipient_list,
                html_message=html_message,
            )

            # Mark reminder as inactive after sending
            reminder.is_active = 0
            reminder.updated_by = user_id
            reminder.updated_at = timezone.now()
            reminder.save()

            return Response(
                {
                    "message": "Reminder email sent successfully.",
                    "reminder_id": reminder_id,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error sending reminder email: {e!s}")
            return Response(
                {"error": f"Error sending reminder email: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AutoSendReminderEmailAPI(APIView):
    """Automatically send reminder emails for due reminders."""

    permission_classes = []  # No permission required for automated task
    authentication_classes = []  # No authentication required

    @swagger_auto_schema(
        operation_description="Automatically send reminder emails 30 minutes before due time.",
        responses={200: "Reminder emails sent successfully"},
    )
    def get(self, request):
        try:
            current_time = timezone.now()
            # Send emails 30 minutes before the reminder timestamp
            notification_time = current_time + timedelta(minutes=30)
            email_helper = EmailHelper()

            due_reminders = Reminder.objects.filter(
                timestamp__lte=notification_time,
                timestamp__gt=current_time,  # Ensure we don't send for past reminders
                is_active=1,
                is_deleted=0,
            )

            sent_count = 0
            for reminder in due_reminders:
                try:
                    # Get all active users for the user
                    recipient_list = (
                        [reminder.user.email]
                        if reminder.user and reminder.user.email
                        else []
                    )

                    if not recipient_list:  # Skip if no recipients
                        continue

                    subject = "Reminder Notification (30 minutes notice)"
                    html_message = get_reminder_template(
                        reminder_note=reminder.note, is_advance_notice=True
                    )

                    # Send email with HTML template
                    email_helper.send_email_async(
                        subject=subject,
                        message=reminder.note,  # Plain text fallback
                        recipient_list=recipient_list,
                        html_message=html_message,
                    )

                    # Mark reminder as inactive after sending
                    reminder.is_active = 0
                    reminder.updated_by = None  # Automated task
                    reminder.updated_at = timezone.now()
                    reminder.save()
                    sent_count += 1

                except Exception as e:
                    print(f"Error processing reminder {reminder.reminder_id}: {e!s}")
                    continue

            return Response(
                {
                    "message": "Email reminders processed successfully (30 minutes advance notice).",
                    "reminders_processed": sent_count,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def get_reminder_template(subscription_name=None, reminder_note=None, end_date=None):
    """
    HTML template for reminders
    """
    subscription_details = ""
    if subscription_name and end_date:
        subscription_details = f"""
        <div style="background-color: #f8f9fa; border-left: 4px solid #00796B; padding: 15px; margin-bottom: 20px;">
            <p style="margin: 0; color: #444444;">
                <strong>Service:</strong> {subscription_name}<br>
                <strong>Subscription End Date:</strong> {end_date.strftime("%B %d, %Y")}
            </p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reminder Notification</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; line-height: 1.6; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #00796B; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Reminder Notification</h1>
            </div>
            <div style="background-color: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: #f8f9fa; border-left: 4px solid #00796B; padding: 15px; margin-bottom: 20px;">
                    <p style="margin: 0; color: #444444;">
                        <strong>Reminder Note:</strong><br>
                        {reminder_note}
                    </p>
                </div>

                {subscription_details}

                <div style="text-align: center;">
                    <a href="#" style="display: inline-block; background-color: #00796B; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Details</a>
                </div>
            </div>
            <div style="text-align: center; padding-top: 20px; color: #666666; font-size: 12px;">
                <p>This is an automated message, please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
