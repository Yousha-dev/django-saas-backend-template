# myapp/apis/admin/moderation_api.py

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.services.moderation_service import ModerationService

logger = logging.getLogger(__name__)


class ModerationQueueAPI(APIView):
    """
    API for admins to view flagged content and pending moderation.
    """

    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get list of flagged content waiting for review.",
        responses={200: "List of pending moderation items"},
    )
    def get(self, request):
        """Get pending moderation queue items."""
        limit = int(request.query_params.get("limit", 50))
        service = ModerationService()
        items = service.get_pending_items(limit=limit)

        return Response(
            {"message": "Moderation queue retrieved successfully", "data": items}
        )


class ModerationActionAPI(APIView):
    """
    API for admins to take action on reported content.
    """

    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Approve, reject, delete, or request changes for flagged content.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "action": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["approve", "reject", "delete", "request_changes"],
                    description="Action to take on the content",
                ),
                "queue_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Moderation queue item ID"
                ),
                "notes": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Optional notes explaining the decision",
                ),
                "send_notification": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Whether to send notification to reporter (default: True)",
                ),
            },
            required=["action", "queue_id"],
        ),
        responses={200: "Action applied successfully"},
    )
    def post(self, request):
        """Take moderation action on a queue item."""
        action = request.data.get("action")
        queue_id = request.data.get("queue_id")
        notes = request.data.get("notes", "")
        send_notification = request.data.get("send_notification", True)

        if not action or not queue_id:
            return Response(
                {"error": "Missing action or queue_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ModerationService()
        result = service.take_action(
            queue_id=queue_id,
            action=action,
            moderator_id=request.user.user_id,
            notes=notes,
            send_notification=send_notification,
        )

        if result.get("success"):
            return Response({"message": result.get("message"), "queue_id": queue_id})

        return Response(
            {"error": result.get("message")}, status=status.HTTP_400_BAD_REQUEST
        )


class ModerationHistoryAPI(APIView):
    """
    API for users to view their moderation history.
    """

    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get moderation history for a specific user.",
        manual_parameters=[
            openapi.Parameter(
                name="user_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="User ID to get history for",
                required=True,
            ),
            openapi.Parameter(
                name="limit",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="Maximum number of items to return (default: 20)",
                required=False,
            ),
        ],
        responses={200: "List of user's moderation history"},
    )
    def get(self, request):
        """Get moderation history for a user."""
        user_id = request.query_params.get("user_id")
        limit = int(request.query_params.get("limit", 20))

        if not user_id:
            return Response(
                {"error": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ModerationService()
        items = service.get_user_moderation_history(user_id=int(user_id), limit=limit)

        return Response(
            {"message": "Moderation history retrieved successfully", "data": items}
        )


class ModerationAppealAPI(APIView):
    """
    API for users to submit appeals for moderation decisions.
    """

    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Submit an appeal for a moderation decision.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "queue_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Original moderation queue item ID",
                ),
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="User ID submitting the appeal",
                ),
                "reason": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Reason for the appeal"
                ),
            },
            required=["queue_id", "user_id", "reason"],
        ),
        responses={200: "Appeal submitted successfully"},
    )
    def post(self, request):
        """Submit an appeal for moderation decision."""
        queue_id = request.data.get("queue_id")
        user_id = request.data.get("user_id")
        reason = request.data.get("reason")

        if not all([queue_id, user_id, reason]):
            return Response(
                {"error": "Missing required fields: queue_id, user_id, reason"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ModerationService()
        result = service.submit_appeal(
            queue_id=int(queue_id), user_id=int(user_id), reason=reason
        )

        if result.get("success"):
            return Response(
                {"message": result.get("message"), "appeal_id": result.get("appeal_id")}
            )

        return Response(
            {"error": result.get("message")}, status=status.HTTP_400_BAD_REQUEST
        )
