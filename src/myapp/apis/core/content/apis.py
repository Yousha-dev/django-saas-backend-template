# myapp/apis/core/content/apis.py

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.models import Comment, Post
from myapp.permissions import IsUserAccess

logger = logging.getLogger(__name__)


# ─── Post APIs ───────────────────────────────────────────────


class CreatePostAPI(APIView):
    """Create a new post for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Create a new post.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "title": openapi.Schema(type=openapi.TYPE_STRING),
                "content_text": openapi.Schema(type=openapi.TYPE_STRING),
                "content_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["general", "article", "update", "discussion"],
                    description="Type of post (default: general)",
                ),
            },
            required=["title", "content_text"],
        ),
        responses={201: "Post created successfully", 400: "Validation error"},
    )
    def post(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        title = request.data.get("title")
        content_text = request.data.get("content_text")
        content_type = request.data.get("content_type", "general")

        if not title or not content_text:
            return Response(
                {"error": "Both 'title' and 'content_text' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        post_obj = Post.objects.create(
            author_id=user_id,
            title=title,
            content_text=content_text,
            content_type=content_type,
            is_active=1,
            is_deleted=0,
            created_by=user_id,
        )

        return Response(
            {
                "message": "Post created successfully.",
                "data": {
                    "post_id": post_obj.post_id,
                    "title": post_obj.title,
                    "content_text": post_obj.content_text,
                    "content_type": post_obj.content_type,
                    "content_status": post_obj.content_status,
                    "created_at": post_obj.created_at,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ListPostsAPI(APIView):
    """List posts for the authenticated user."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List posts for the authenticated user.",
        manual_parameters=[
            openapi.Parameter(
                "content_type",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by content type",
                required=False,
            ),
        ],
        responses={200: "List of posts"},
    )
    def get(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        filters = {"author_id": user_id, "is_active": 1, "is_deleted": 0}
        content_type = request.query_params.get("content_type")
        if content_type:
            filters["content_type"] = content_type

        posts = Post.objects.filter(**filters).values(
            "post_id",
            "title",
            "content_text",
            "content_type",
            "content_status",
            "created_at",
            "updated_at",
        )

        return Response(
            {"message": "Posts retrieved successfully", "data": list(posts)},
            status=status.HTTP_200_OK,
        )


class UpdatePostAPI(APIView):
    """Update an existing post."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Update an existing post.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "title": openapi.Schema(type=openapi.TYPE_STRING),
                "content_text": openapi.Schema(type=openapi.TYPE_STRING),
                "content_type": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: "Post updated", 404: "Not found"},
    )
    def put(self, request, post_id):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            post_obj = Post.objects.get(
                post_id=post_id, author_id=user_id, is_deleted=0
            )
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if "title" in request.data:
            post_obj.title = request.data["title"]
        if "content_text" in request.data:
            post_obj.content_text = request.data["content_text"]
        if "content_type" in request.data:
            post_obj.content_type = request.data["content_type"]

        post_obj.updated_by = user_id
        post_obj.save()

        return Response(
            {
                "message": "Post updated successfully.",
                "data": {
                    "post_id": post_obj.post_id,
                    "title": post_obj.title,
                    "content_text": post_obj.content_text,
                    "content_type": post_obj.content_type,
                },
            },
            status=status.HTTP_200_OK,
        )


class DeletePostAPI(APIView):
    """Soft-delete a post."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Soft-delete a post by ID.",
        responses={200: "Post deleted", 404: "Not found"},
    )
    def delete(self, request, post_id):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            post_obj = Post.objects.get(
                post_id=post_id, author_id=user_id, is_deleted=0
            )
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        post_obj.is_deleted = 1
        post_obj.is_active = 0
        post_obj.updated_by = user_id
        post_obj.save()

        return Response(
            {"message": "Post deleted successfully."},
            status=status.HTTP_200_OK,
        )


# ─── Comment APIs ────────────────────────────────────────────


class CreateCommentAPI(APIView):
    """Create a comment on a post."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Create a comment on a post.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "content_text": openapi.Schema(type=openapi.TYPE_STRING),
                "parent_comment_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Optional parent comment ID for threaded replies",
                ),
            },
            required=["content_text"],
        ),
        responses={201: "Comment created", 400: "Validation error"},
    )
    def post(self, request, post_id):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Verify post exists
        if not Post.objects.filter(post_id=post_id, is_deleted=0).exists():
            return Response(
                {"error": "Post not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        content_text = request.data.get("content_text")
        if not content_text:
            return Response(
                {"error": "'content_text' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parent_id = request.data.get("parent_comment_id")
        comment = Comment.objects.create(
            author_id=user_id,
            post_id=post_id,
            parent_comment_id=parent_id,
            content_text=content_text,
            is_active=1,
            is_deleted=0,
            created_by=user_id,
        )

        return Response(
            {
                "message": "Comment created successfully.",
                "data": {
                    "comment_id": comment.comment_id,
                    "post_id": post_id,
                    "content_text": comment.content_text,
                    "parent_comment_id": parent_id,
                    "created_at": comment.created_at,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ListCommentsAPI(APIView):
    """List comments for a post."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="List all comments for a specific post.",
        responses={200: "List of comments"},
    )
    def get(self, request, post_id):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        comments = Comment.objects.filter(post_id=post_id, is_deleted=0).values(
            "comment_id",
            "author_id",
            "content_text",
            "content_status",
            "parent_comment_id",
            "created_at",
        )

        return Response(
            {"message": "Comments retrieved successfully", "data": list(comments)},
            status=status.HTTP_200_OK,
        )


class DeleteCommentAPI(APIView):
    """Soft-delete a comment (owner only)."""

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Soft-delete a comment by ID.",
        responses={200: "Comment deleted", 404: "Not found"},
    )
    def delete(self, request, comment_id):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            comment = Comment.objects.get(
                comment_id=comment_id, author_id=user_id, is_deleted=0
            )
        except Comment.DoesNotExist:
            return Response(
                {"error": "Comment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        comment.is_deleted = 1
        comment.is_active = 0
        comment.updated_by = user_id
        comment.save()

        return Response(
            {"message": "Comment deleted successfully."},
            status=status.HTTP_200_OK,
        )
