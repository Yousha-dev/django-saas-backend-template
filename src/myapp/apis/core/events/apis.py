import calendar
import logging
from datetime import date, datetime, timedelta

from django.core.mail import get_connection
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.emailhelper import EmailHelper
from myapp.models import Event, User
from myapp.permissions import IsUserAccess
from myapp.serializers.core_serializers import EventSerializer, NotificationSerializer

logger = logging.getLogger(__name__)


### 1. Create Event API ###
class CreateEventAPI(APIView):
    """
    Create a new event for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Create a new event for the authenticated user.",
        request_body=EventSerializer,
        responses={201: "Event created successfully.", 400: "Validation errors."},
    )
    def post(self, request):
        user_id = getattr(request, "user_id", None)

        if not user_id:
            return Response({"error": "User ID is missing in the token."}, status=400)

        if not user_id:
            return Response({"error": "User ID is missing in the token."}, status=400)

        data = request.data.copy()
        data["user"] = user_id
        data["created_by"] = user_id
        # Set default values for is_active and is_deleted
        data["is_active"] = 1
        data["is_deleted"] = 0
        serializer = EventSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Event created successfully.", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


### 2. List Events API ###
class ListEventsAPI(APIView):
    """
    List all active events for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List all active events for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                "type",
                openapi.IN_QUERY,
                description="Filter by event type",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                description="Filter by event category",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "startdate",
                openapi.IN_QUERY,
                description="Filter by start date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False,
            ),
            openapi.Parameter(
                "enddate",
                openapi.IN_QUERY,
                description="Filter by end date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False,
            ),
        ],
        responses={200: EventSerializer(many=True), 400: "Bad Request."},
    )
    def get(self, request):
        user_id = getattr(request, "user_id", None)

        if not user_id:
            return Response({"error": "User ID is missing in the token."}, status=400)

        filters = {"user_id": user_id, "is_active": True, "is_deleted": False}

        # Add optional filters
        event_type = request.query_params.get("type")
        if event_type:
            filters["type"] = event_type

        category = request.query_params.get("category")
        if category:
            filters["category"] = category

        start_date = request.query_params.get("start_date")
        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                filters["start_date__gte"] = start_date
            except ValueError:
                return Response(
                    {"error": "Invalid start date format. Use YYYY-MM-DD."}, status=400
                )

        end_date = request.query_params.get("end_date")
        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                filters["end_date__lte"] = end_date
            except ValueError:
                return Response(
                    {"error": "Invalid end date format. Use YYYY-MM-DD."}, status=400
                )

        events = Event.objects.filter(**filters)
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


### 3. Update Event API ###
class UpdateEventAPI(APIView):
    """
    Update an existing event for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Update an existing event for the authenticated user.",
        request_body=EventSerializer,
        responses={
            200: "Event updated successfully.",
            404: "Event not found.",
            400: "Validation errors.",
        },
    )
    def put(self, request, event_id):
        user_id = getattr(request, "user_id", None)
        user_id = getattr(request, "user_id", None)

        if not user_id:
            return Response({"error": "User ID is missing in the token."}, status=400)

        if not user_id:
            return Response({"error": "User ID is missing in the token."}, status=400)

        try:
            event = Event.objects.get(pk=event_id, user_id=user_id, is_deleted=0)
            data = request.data.copy()
            data["updated_by"] = user_id
            serializer = EventSerializer(event, data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Event updated successfully.", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found."}, status=status.HTTP_404_NOT_FOUND
            )


### 4. Delete Event API ###
class DeleteEventAPI(APIView):
    """
    Soft delete an event for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Soft delete an event for the authenticated user.",
        responses={200: "Event deleted successfully.", 404: "Event not found."},
    )
    def delete(self, request, event_id):
        user_id = getattr(request, "user_id", None)
        user_id = getattr(request, "user_id", None)

        if not user_id:
            return Response({"error": "User ID is missing in the token."}, status=400)

        if not user_id:
            return Response({"error": "User ID is missing in the token."}, status=400)

        try:
            event = Event.objects.get(pk=event_id, user_id=user_id, is_deleted=False)
            event.is_deleted = 1
            event.updated_by = user_id
            event.updated_at = timezone.now()
            event.save()
            return Response(
                {"message": "Event deleted successfully."}, status=status.HTTP_200_OK
            )
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found."}, status=status.HTTP_404_NOT_FOUND
            )


class AutoSendActionEmailEventAPI(APIView):
    """
    Automatically check and send email notifications for Action events
    when the start date is today and the start time is less than 1 hour away.
    """

    permission_classes = []  # No permission required for automated task
    authentication_classes = []  # No authentication required

    def _calculate_recurring_dates(self, start_date, end_date, frequency):
        """
        Calculate all occurrences of a recurring event based on frequency.

        Args:
            start_date: The start date of the recurring event
            end_date: The end date of the recurring event
            frequency: The recurrence frequency (Daily, Weekly, Monthly, Yearly)

        Returns:
            List of dates between start_date and end_date based on frequency
        """
        if start_date > end_date:
            return []

        recurring_dates = [start_date]
        current_date = start_date

        if frequency == "Daily":
            delta = timedelta(days=1)
        elif frequency == "Weekly":
            delta = timedelta(weeks=1)
        elif frequency == "Monthly":
            # For monthly, we need to add months
            while True:
                # Add one month to current date
                month = current_date.month + 1
                year = current_date.year
                if month > 12:
                    month = 1
                    year += 1

                # Handle edge cases like month lengths
                day = min(current_date.day, calendar.monthrange(year, month)[1])

                next_date = date(year, month, day)
                if next_date <= end_date:
                    recurring_dates.append(next_date)
                    current_date = next_date
                else:
                    break
            return recurring_dates
        elif frequency == "Yearly":
            # For yearly, we increment the year
            while True:
                next_date = date(
                    current_date.year + 1, current_date.month, current_date.day
                )
                if next_date <= end_date:
                    recurring_dates.append(next_date)
                    current_date = next_date
                else:
                    break
            return recurring_dates

        # For daily and weekly, we can use simple addition
        if frequency in ["Daily", "Weekly"]:
            while True:
                next_date = current_date + delta
                if next_date <= end_date:
                    recurring_dates.append(next_date)
                    current_date = next_date
                else:
                    break

        return recurring_dates

    def _should_send_email(self, event_date, event_time):
        """
        Check if the event is within 1 hour from now.

        Args:
            event_date: The date of the event
            event_time: The time of the event

        Returns:
            Boolean indicating if email should be sent
        """
        now = timezone.now()
        today = now.date()

        # Only process events for today
        if event_date != today:
            return False

        # Create a datetime combining the event date and time
        event_datetime = datetime.combine(event_date, event_time)
        if timezone.is_naive(event_datetime):
            event_datetime = timezone.make_aware(event_datetime)

        # Calculate time difference in minutes
        time_diff = (event_datetime - now).total_seconds() / 60

        # Send email if event is within the next hour (60 minutes)
        # and hasn't already passed
        return 0 <= time_diff <= 60

    @swagger_auto_schema(
        operation_description="Automatically send emails for Action events that are scheduled within the next hour.",
        responses={
            200: openapi.Response(
                description="Action event emails sent successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "emails_sent": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            500: openapi.Response(
                description="Internal server error.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
        },
    )
    def get(self, request):
        try:
            now = timezone.now()
            today = now.date()

            one_day_future = today + timedelta(days=1)

            email_helper = EmailHelper()
            emails_sent = 0

            # Get all active Action events
            action_events = Event.objects.filter(
                type="Action",
                end_date__gte=today,
                start_date__lte=one_day_future,
                is_active=1,
                is_deleted=0,
            )

            # Process each event
            for event in action_events:
                # Check if repeated and calculate all relevant dates
                event_dates = []
                if event.repeated == 1 and event.frequency:
                    # For recurring events, calculate all event dates
                    event_dates = self._calculate_recurring_dates(
                        event.start_date, event.end_date, event.frequency
                    )
                else:
                    # For non-recurring events, just use the start date
                    event_dates = [event.start_date]

                # Process each occurrence date
                for event_date in event_dates:
                    if self._should_send_email(event_date, event.start_time):
                        # Prepare recipient lists
                        to_recipients = []
                        cc_recipients = []

                        if event.email_to:
                            to_recipients = [
                                email.strip() for email in event.email_to.split(",")
                            ]

                        if event.email_cc:
                            cc_recipients = [
                                email.strip() for email in event.email_cc.split(",")
                            ]

                        if to_recipients:
                            # Prepare email content
                            html_message = get_action_event_email_template(
                                event_title=event.title,
                                event_description=event.description,
                                event_date=event_date,
                                event_time=event.start_time,
                                event_location=event.location or "Not specified",
                            )
                            # Initialize connection and from_email
                            connection = None
                            from_email = None

                            # Check if user has custom SMTP settings
                            try:
                                user = User.objects.get(user_id=event.user_id)
                                if user.use_user_smtp == 1:
                                    try:
                                        # Create connection with user SMTP settings
                                        connection = get_connection(
                                            host=user.smtp_host,
                                            port=user.smtp_port,
                                            username=user.smtp_host_user,
                                            password=user.smtp_host_password,
                                            use_tls=user.smtp_use_tls,
                                            fail_silently=False,
                                        )

                                        # Test the connection
                                        connection.open()
                                        logger.info(
                                            f"User SMTP connection successful for event {event.event_id}"
                                        )
                                        from_email = (
                                            user.smtp_host_user
                                        )  # Use user's email as sender

                                    except Exception as e:
                                        logger.error(
                                            f"Failed to connect using user SMTP settings: {e!s}"
                                        )
                                        connection = None  # Reset connection on failure
                                        from_email = None  # Reset from_email on failure
                                        # Will fall back to default settings
                                    finally:
                                        # If connection was opened successfully, close it to avoid resource leaks
                                        # It will be reopened when sending the email
                                        if connection and connection.connection:
                                            connection.close()
                            except User.DoesNotExist:
                                logger.error(f"User {event.user_id} not found")

                            # Send email with appropriate connection and from_email
                            email_sent = email_helper.send_email(
                                subject=event.email_subject,
                                message=event.email_body,  # Plain text fallback
                                recipient_list=to_recipients,
                                cc=cc_recipients,
                                html_message=html_message,
                                from_email=from_email,
                                connection=connection,
                            )
                            if email_sent:
                                emails_sent += 1

                                # Create notification for the user
                                self._create_notification(
                                    user_id=event.user_id,
                                    event_id=event.event_id,
                                    event_title=event.title,
                                    recipients=", ".join(to_recipients + cc_recipients),
                                )

            return Response(
                {
                    "message": "Action event emails processed successfully.",
                    "emails_sent": emails_sent,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in AutoSendActionEmailEventAPI: {e!s}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _create_notification(self, user_id, event_id, event_title, recipients):
        """Helper method to create a notification for sent event emails"""
        try:
            notification_data = {
                "user": user_id,
                "title": "Event Email Sent",
                "message": f"Action email for event '{event_title}' was sent to {recipients}",
                "type": "System",
                "is_read": 0,
                "is_active": 1,
                "is_deleted": 0,
            }

            serializer = NotificationSerializer(data=notification_data)
            if serializer.is_valid():
                serializer.save()
            else:
                logger.error(
                    f"Event notification validation error: {serializer.errors}"
                )

        except Exception as e:
            logger.error(f"Error creating event notification: {e!s}")


def get_action_event_email_template(
    event_title, event_description, event_date, event_time, event_location
):
    """
    HTML template for action event emails

    Args:
        event_title: Title of the event
        event_description: Description of the event
        event_date: Date of the event
        event_time: Time of the event
        event_location: Location of the event

    Returns:
        str: Formatted HTML email template
    """
    # Format the time for display
    formatted_time = event_time.strftime("%I:%M %p")
    # Format the date for display
    formatted_date = event_date.strftime("%B %d, %Y")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Action Required: {event_title}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; line-height: 1.6; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #00796B; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Action Required</h1>
            </div>
            <div style="background-color: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #333333; margin-top: 0;">{event_title}</h2>

                <div style="background-color: #f8f9fa; border-left: 4px solid #00796B; padding: 15px; margin-bottom: 20px;">
                    <p style="margin: 0; color: #444444;">
                        <strong>️ Action Needed Soon</strong><br>
                        <strong>📅 Date:</strong> {formatted_date}<br>
                        <strong>🕒 Time:</strong> {formatted_time}<br>
                        <strong>📍 Location:</strong> {event_location}
                    </p>
                </div>

                <div style="margin-bottom: 25px;">
                    <h3 style="color: #555555; margin-bottom: 10px;">Action Details:</h3>
                    <p style="color: #666666; margin-top: 0;">{event_description}</p>
                </div>

            </div>
            <div style="text-align: center; padding-top: 20px; color: #666666; font-size: 12px;">
                <p>This action notification is time-sensitive. Please address it promptly.</p>
            </div>
        </div>
    </body>
    </html>
    """


class AutoSendReminderEmailEventAPI(APIView):
    """
    Automatically check and send email reminders for events with type 'Reminder'
    when the start date is 1 day or 1 hour away from current date and time.
    """

    permission_classes = []  # No permission required for automated task
    authentication_classes = []  # No authentication required

    def _calculate_recurring_dates(self, start_date, end_date, frequency):
        """
        Calculate all occurrences of a recurring event based on frequency.

        Args:
            start_date: The start date of the recurring event
            end_date: The end date of the recurring event
            frequency: The recurrence frequency (Daily, Weekly, Monthly, Yearly)

        Returns:
            List of dates between start_date and end_date based on frequency
        """
        if start_date > end_date:
            return []

        recurring_dates = [start_date]
        current_date = start_date

        if frequency == "Daily":
            delta = timedelta(days=1)
        elif frequency == "Weekly":
            delta = timedelta(weeks=1)
        elif frequency == "Monthly":
            # For monthly, we need to add months
            while True:
                # Add one month to current date
                month = current_date.month + 1
                year = current_date.year
                if month > 12:
                    month = 1
                    year += 1

                # Handle edge cases like month lengths
                day = min(current_date.day, calendar.monthrange(year, month)[1])

                next_date = date(year, month, day)
                if next_date <= end_date:
                    recurring_dates.append(next_date)
                    current_date = next_date
                else:
                    break
            return recurring_dates
        elif frequency == "Yearly":
            # For yearly, we increment the year
            while True:
                next_date = date(
                    current_date.year + 1, current_date.month, current_date.day
                )
                if next_date <= end_date:
                    recurring_dates.append(next_date)
                    current_date = next_date
                else:
                    break
            return recurring_dates

        # For daily and weekly, we can use simple addition
        if frequency in ["Daily", "Weekly"]:
            while True:
                next_date = current_date + delta
                if next_date <= end_date:
                    recurring_dates.append(next_date)
                    current_date = next_date
                else:
                    break

        return recurring_dates

    def _should_send_reminder(self, event_date, event_time, now):
        """
        Check if the event requires a reminder (1 day or 1 hour away).

        Args:
            event_date: The date of the event
            event_time: The time of the event
            now: Current datetime

        Returns:
            tuple: (should_send, reminder_type)
                should_send: Boolean indicating if email should be sent
                reminder_type: String 'day' or 'hour' indicating type of reminder
        """
        today = now.date()
        tomorrow = today + timedelta(days=1)

        # Create a datetime combining the event date and time
        event_datetime = datetime.combine(event_date, event_time)
        if timezone.is_naive(event_datetime):
            event_datetime = timezone.make_aware(event_datetime)

        # Calculate time difference
        time_diff_seconds = (event_datetime - now).total_seconds()
        time_diff_hours = time_diff_seconds / 3600

        # 1-day reminder (between 23 and 24 hours away)
        if event_date == tomorrow and 23 <= time_diff_hours <= 24:
            return True, "day"

        # 1-hour reminder (between 50 and 70 minutes away)
        if 0.5 <= time_diff_hours <= 1.5:  # Approximately 50-70 minutes
            return True, "hour"

        return False, None

    def _create_notification(self, user_id, event_id, event_title, reminder_type):
        """Helper method to create a notification for sent event reminder"""
        try:
            notification_data = {
                "user": user_id,
                "title": f"Event Reminder: {reminder_type}",
                "message": f"Reminder email for event '{event_title}' was sent ({reminder_type} reminder)",
                "type": "System",
                "is_read": 0,
                "is_active": 1,
                "is_deleted": 0,
            }

            serializer = NotificationSerializer(data=notification_data)
            if serializer.is_valid():
                serializer.save()
            else:
                logger.error(
                    f"Event reminder notification validation error: {serializer.errors}"
                )

        except Exception as e:
            logger.error(f"Error creating event reminder notification: {e!s}")

    @swagger_auto_schema(
        operation_description="Automatically send reminder emails for events with type 'Reminder' that are scheduled 1 day or 1 hour away.",
        responses={
            200: openapi.Response(
                description="Reminder emails sent successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "day_reminders_sent": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "hour_reminders_sent": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                    },
                ),
            ),
            500: openapi.Response(
                description="Internal server error.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
        },
    )
    def get(self, request):
        try:
            now = timezone.now()
            today = now.date()
            email_helper = EmailHelper()
            day_reminders_sent = 0
            hour_reminders_sent = 0

            # Get events ending today or in the future
            # And starting at most 1 day in the future
            one_day_future = today + timedelta(days=1)
            reminder_events = Event.objects.filter(
                type="Reminder",
                end_date__gte=today,
                start_date__lte=one_day_future,
                is_active=1,
                is_deleted=0,
            )

            # Process each event
            for event in reminder_events:
                # Check if repeated and calculate all relevant dates
                event_dates = []
                if event.repeated == 1 and event.frequency:
                    # For recurring events, calculate all event dates
                    event_dates = self._calculate_recurring_dates(
                        event.startdate, event.enddate, event.frequency
                    )
                else:
                    # For non-recurring events, just use the start date
                    event_dates = [event.startdate]

                # Process each occurrence date
                for event_date in event_dates:
                    should_send, reminder_type = self._should_send_reminder(
                        event_date, event.start_time, now
                    )

                    if should_send:
                        to_recipients = []
                        cc_recipients = []

                        if event.emailto:
                            to_recipients = [
                                email.strip() for email in event.emailto.split(",")
                            ]

                        if event.emailcc:
                            cc_recipients = [
                                email.strip() for email in event.emailcc.split(",")
                            ]

                        if to_recipients:
                            # Prepare email content based on reminder type
                            reminder_period = (
                                "1 day" if reminder_type == "day" else "1 hour"
                            )
                            subject = f"Reminder: {event.title} - {reminder_period} until event"

                            message = f"This is a reminder that '{event.title}' is scheduled for {event_date.strftime('%B %d, %Y')} at {event.starttime.strftime('%I:%M %p')}."

                            html_message = get_reminder_event_email_template(
                                event_title=event.title,
                                event_description=event.description,
                                event_date=event_date,
                                event_time=event.start_time,
                                event_location=event.location or "Not specified",
                                reminder_period=reminder_period,
                            )
                            print(cc_recipients)
                            # Send email
                            email_sent = email_helper.send_email(
                                subject=subject,
                                message=message,  # Plain text fallback
                                recipient_list=to_recipients,
                                cc=cc_recipients,
                                html_message=html_message,
                            )

                            if email_sent:
                                # Update counter based on reminder type
                                if reminder_type == "day":
                                    day_reminders_sent += 1
                                else:  # hour
                                    hour_reminders_sent += 1

                                # Create notification for the user
                                self._create_notification(
                                    user_id=event.user_id,
                                    event_id=event.event_id,
                                    event_title=event.title,
                                    reminder_type=f"{reminder_period} reminder",
                                )

            return Response(
                {
                    "message": "Event reminder emails processed successfully.",
                    "day_reminders_sent": day_reminders_sent,
                    "hour_reminders_sent": hour_reminders_sent,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error in AutoSendReminderEmailEventAPI: {e!s}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def get_reminder_event_email_template(
    event_title,
    event_description,
    event_date,
    event_time,
    event_location,
    reminder_period,
):
    """
    HTML template for reminder event emails

    Args:
        event_title: Title of the event
        event_description: Description of the event
        event_date: Date of the event
        event_time: Time of the event
        event_location: Location of the event
        reminder_period: Period of reminder (e.g., "1 day", "1 hour")

    Returns:
        str: Formatted HTML email template
    """
    # Format the time for display
    formatted_time = event_time.strftime("%I:%M %p")
    # Format the date for display
    formatted_date = event_date.strftime("%B %d, %Y")

    # Set urgency color based on reminder period
    urgency_color = "#FF9800" if reminder_period == "1 hour" else "#4CAF50"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Event Reminder: {event_title}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; line-height: 1.6; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: 00796B; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Event Reminder: {reminder_period} remaining</h1>
            </div>
            <div style="background-color: #ffffff; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #333333; margin-top: 0;">{event_title}</h2>

                <div style="background-color: #f8f9fa; border-left: 4px solid {urgency_color}; padding: 15px; margin-bottom: 20px;">
                    <p style="margin: 0; color: #444444;">
                        <strong>📅 Date:</strong> {formatted_date}<br>
                        <strong>🕒 Time:</strong> {formatted_time}<br>
                        <strong>⏰ Reminder:</strong> {reminder_period} until start<br>
                        <strong>📍 Location:</strong> {event_location}
                    </p>
                </div>

                <div style="margin-bottom: 25px;">
                    <h3 style="color: #555555; margin-bottom: 10px;">Event Details:</h3>
                    <p style="color: #666666; margin-top: 0;">{event_description}</p>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <p style="color: #777777; font-size: 14px;">This is an automated reminder for an upcoming event.</p>
                </div>
            </div>
            <div style="text-align: center; padding-top: 20px; color: #666666; font-size: 12px;">
                <p>This is an automated message. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
