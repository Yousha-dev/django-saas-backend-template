# views.py

# Create your views here.
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.views import TokenObtainPairView

from myapp.serializers.auth_serializers import CustomTokenObtainPairSerializer

custom_headers = [
    openapi.Parameter(
        "X-User-ID",
        openapi.IN_HEADER,
        description="User ID extracted from token",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "X-Role",
        openapi.IN_HEADER,
        description="Role extracted from token",
        type=openapi.TYPE_STRING,
    ),
]


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_summary="Obtain Token",
        operation_description=(
            "Generate an access and refresh token.\n\n"
            "Custom Claims included in the token payload:\n"
            "- `user_id`: User's ID.\n"
            "- `role`: User's role."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User's email"
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, description="User's password"
                ),
            },
            required=["email", "password"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "refresh": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Refresh token"
                    ),
                    "access": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Access token"
                    ),
                    "user_id": openapi.Schema(
                        type=openapi.TYPE_INTEGER, description="User ID"
                    ),
                    "role": openapi.Schema(
                        type=openapi.TYPE_STRING, description="User role"
                    ),
                },
            ),
            401: "Invalid email or password",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
