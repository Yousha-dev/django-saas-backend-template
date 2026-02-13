# myapp/apis/core/discounts/apis.py

import logging
from decimal import Decimal, InvalidOperation

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.permissions import IsUserAccess
from myapp.services.discount_service import DiscountService

logger = logging.getLogger(__name__)


class ValidateCouponAPI(APIView):
    """
    Validate a coupon code for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Validate a coupon code for the authenticated user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "code": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Coupon code to validate",
                ),
                "plan_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Optional subscription plan ID to check eligibility",
                ),
            },
            required=["code"],
        ),
        responses={200: "Coupon validation result"},
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
                {"error": "Coupon code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_id = request.data.get("plan_id")
        result = DiscountService.validate_coupon(
            code=code, user_id=user_id, plan_id=plan_id
        )

        return Response({"message": "Coupon validation result", "data": result})


class ApplyCouponAPI(APIView):
    """
    Apply a coupon code to a purchase for the authenticated user.
    """

    permission_classes = [IsUserAccess]

    @swagger_auto_schema(
        operation_description="Apply a coupon code to an amount for the authenticated user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "code": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Coupon code to apply",
                ),
                "amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Original amount before discount",
                ),
            },
            required=["code", "amount"],
        ),
        responses={200: "Coupon applied successfully", 400: "Invalid request"},
    )
    def post(self, request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "User ID is missing in the token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        code = request.data.get("code")
        amount = request.data.get("amount")

        if not code or amount is None:
            return Response(
                {"error": "Both 'code' and 'amount' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            original_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return Response(
                {"error": "Invalid amount value."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = DiscountService.apply_coupon(
            code=code, user_id=user_id, original_amount=original_amount
        )

        if result.get("success"):
            return Response({"message": "Coupon applied successfully", "data": result})

        return Response(
            {"error": result.get("message", "Failed to apply coupon.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
