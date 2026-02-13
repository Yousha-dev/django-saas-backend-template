import logging

from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.models import Notification
from myapp.permissions import IsUserAccess
from myapp.serializers.core_serializers import NotificationSerializer

logger = logging.getLogger(__name__)


class CreateNotificationAPI(APIView):
    """Create a new notification for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Create a new notification for the authenticated user.",
        request_body=NotificationSerializer,
        responses={
            201: openapi.Response(
                description="Notification created successfully",
                schema=NotificationSerializer,
            ),
            400: openapi.Response(
                description="Validation errors.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
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
    def post(self, request):
        try:
            user_id = getattr(request, "user_id", None)

            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            data = request.data
            data["is_active"] = 1
            data["is_deleted"] = 0
            data["user"] = user_id
            data["created_by"] = user_id

            serializer = NotificationSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Notification created successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Error creating notification: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ListNotificationsAPI(APIView):
    """List all active notifications for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List all active notifications for the authenticated user.",
        responses={
            200: NotificationSerializer(many=True),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            500: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
        },
    )
    def get(self, request):
        try:
            user_id = getattr(request, "user_id", None)

            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            notifications = Notification.objects.filter(
                user_id=user_id, is_active=1, is_deleted=0
            ).order_by("-created_at")

            serializer = NotificationSerializer(notifications, many=True)
            return Response(
                {
                    "message": "Notifications retrieved successfully",
                    "count": notifications.count(),
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Error retrieving notifications: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MarkNotificationAsReadAPI(APIView):
    """Mark a specific notification as read for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Mark a specific notification as read.",
        responses={
            200: openapi.Response(
                description="Notification marked as read successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                        ),
                    },
                ),
            ),
            400: openapi.Response(
                description="Bad request.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            404: openapi.Response(
                description="Notification not found.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
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
    def put(self, request, notification_id):
        try:
            user_id = getattr(request, "user_id", None)

            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."}, status=400
                )

            notification = Notification.objects.filter(
                notification_id=notification_id,
                user_id=user_id,
                is_active=1,
                is_deleted=0,
            ).first()

            if not notification:
                return Response(
                    {"error": "Notification not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            notification.is_read = 1
            notification.updated_by = user_id
            notification.updated_at = timezone.now()
            notification.save()

            return Response(
                {
                    "message": "Notification marked as read successfully.",
                    "data": NotificationSerializer(notification).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Error marking notification as read: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteNotificationAPI(APIView):
    """Delete a specific notification for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Delete a specific notification.",
        responses={
            200: openapi.Response(
                description="Notification deleted successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"message": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            404: openapi.Response(
                description="Notification not found.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            400: openapi.Response(
                description="Bad request.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
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
    def delete(self, request, notification_id):
        try:
            user_id = getattr(request, "user_id", None)

            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            notification = Notification.objects.filter(
                notification_id=notification_id, user_id=user_id, is_deleted=0
            ).first()

            if not notification:
                return Response(
                    {"error": "Notification not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Soft delete
            notification.is_deleted = 1
            notification.updated_by = user_id
            notification.updated_at = timezone.now()
            notification.save()

            return Response(
                {"message": "Notification deleted successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error deleting notification: {e!s}")
            return Response(
                {"error": f"Error deleting notification: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ClearAllNotificationsAPI(APIView):
    """Clear all notifications for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Clear all notifications for the authenticated user.",
        responses={
            200: openapi.Response(
                description="All notifications cleared successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: openapi.Response(
                description="Bad request.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
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
    def delete(self, request):
        try:
            user_id = getattr(request, "user_id", None)

            if not user_id:
                return Response(
                    {"error": "User ID is missing in the token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get all active notifications for the user
            notifications = Notification.objects.filter(
                user_id=user_id, is_active=1, is_deleted=0
            )

            count = notifications.count()

            # Bulk update to soft delete all notifications
            notifications.update(
                is_deleted=1, updated_by=user_id, updated_at=timezone.now()
            )

            return Response(
                {"message": "All notifications cleared successfully.", "count": count},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error clearing notifications: {e!s}")
            return Response(
                {"error": f"Error clearing notifications: {e!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
