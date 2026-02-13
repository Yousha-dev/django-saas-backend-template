from django.urls import path

from .apis import (
    CreateCommentAPI,
    CreatePostAPI,
    DeleteCommentAPI,
    DeletePostAPI,
    ListCommentsAPI,
    ListPostsAPI,
    UpdatePostAPI,
)

urlpatterns = [
    # Posts
    path("posts/create/", CreatePostAPI.as_view(), name="create_post"),
    path("posts/list/", ListPostsAPI.as_view(), name="list_posts"),
    path("posts/<int:post_id>/update/", UpdatePostAPI.as_view(), name="update_post"),
    path("posts/<int:post_id>/delete/", DeletePostAPI.as_view(), name="delete_post"),
    # Comments
    path(
        "posts/<int:post_id>/comments/create/",
        CreateCommentAPI.as_view(),
        name="create_comment",
    ),
    path(
        "posts/<int:post_id>/comments/list/",
        ListCommentsAPI.as_view(),
        name="list_comments",
    ),
    path(
        "comments/<int:comment_id>/delete/",
        DeleteCommentAPI.as_view(),
        name="delete_comment",
    ),
]
