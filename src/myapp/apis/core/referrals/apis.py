# myapp/apis/core/referrals/apis.py

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.permissions import IsUserAccess
from myapp.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class GenerateReferralCodeAPI(APIView):
    """
    Generate a referral code for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Generate a unique referral code for the authenticated user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "reward_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["credit", "discount", "free_month", "feature_unlock"],
                    description="Type of reward (default: credit)",
                ),
                "reward_amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Amount of reward (default: 10.0)",
                ),
            },
        ),
        responses={200: "Referral code generated", 400: "Error"},
    )
    def post(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        reward_type = request.data.get("reward_type", "credit")
        reward_amount = request.data.get("reward_amount", 10.0)

        result = ReferralService.generate_referral_code(
            user_id=user_id,
            reward_type=reward_type,
            reward_amount=float(reward_amount),
        )

        if result.get("success"):
            return Response(
                {"message": result.get("message"), "data": result},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": result.get("message", "Failed to generate referral code.")},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ApplyReferralAPI(APIView):
    """
    Apply a referral code for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Apply a referral code during signup or onboarding.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "code": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Referral code to apply",
                ),
            },
            required=["code"],
        ),
        responses={200: "Referral applied successfully", 400: "Invalid code"},
    )
    def post(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        code = request.data.get("code")
        if not code:
            return Response(
                {"error": "Referral code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = ReferralService.apply_referral(referrer_code=code, new_user_id=user_id)

        if result.get("success"):
            return Response(
                {"message": result.get("message"), "data": result},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": result.get("message", "Failed to apply referral code.")},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ReferralStatsAPI(APIView):
    """
    Get referral statistics for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Get referral statistics for the authenticated user.",
        responses={200: "Referral statistics"},
    )
    def get(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        stats = ReferralService.get_referral_stats(user_id=user_id)

        return Response(
            {"message": "Referral statistics retrieved successfully", "data": stats},
            status=status.HTTP_200_OK,
        )
