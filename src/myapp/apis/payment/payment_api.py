# myapp/apis/payment/payment_api.py
"""
Payment API endpoints using the strategy pattern.

This module provides REST API endpoints for payment processing,
supporting multiple payment providers through a unified interface.
"""

import logging

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from myapp.payment_strategies import PaymentManager, PaymentProviderFactory
from myapp.payment_strategies.base import PaymentError

logger = logging.getLogger(__name__)


# Initialize payment manager with default provider
payment_manager = PaymentManager(
    preferred_provider=getattr(settings, "DEFAULT_PAYMENT_PROVIDER", "stripe")
)


class CreatePaymentIntentAPI(APIView):
    """
    Create a payment intent using the configured payment provider.

    Supports multiple providers: stripe, paypal, bank_transfer
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a payment intent for one-time payment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER, description="Payment amount (e.g., 10.00)"
                ),
                "currency": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Currency code (e.g., USD, EUR)",
                    default="USD",
                ),
                "description": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment description",
                ),
                "provider": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment provider (stripe, paypal, bank_transfer)",
                    enum=["stripe", "paypal", "bank_transfer"],
                ),
                "customer_email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Customer email for receipts",
                ),
            },
            required=["amount"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "transaction_id": openapi.Schema(type=openapi.TYPE_STRING),
                    "amount": openapi.Schema(type=openapi.TYPE_STRING),
                    "currency": openapi.Schema(type=openapi.TYPE_STRING),
                    "status": openapi.Schema(type=openapi.TYPE_STRING),
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "provider": openapi.Schema(type=openapi.TYPE_STRING),
                    "client_secret": openapi.Schema(type=openapi.TYPE_STRING),
                    "redirect_url": openapi.Schema(type=openapi.TYPE_STRING),
                    "instructions": openapi.Schema(type=openapi.TYPE_OBJECT),
                },
            ),
            400: "Bad Request - Invalid parameters",
            503: "Service Unavailable - Payment provider not configured",
        },
    )
    def post(self, request):
        try:
            amount = request.data.get("amount")
            currency = request.data.get("currency", "USD")
            description = request.data.get("description", "Payment")
            provider = request.data.get("provider")
            customer_email = request.data.get("customer_email")

            if not amount:
                return Response(
                    {"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Create payment intent
            result = payment_manager.create_payment_intent(
                amount=float(amount),
                currency=currency,
                description=description,
                customer_email=customer_email,
                provider=provider,
            )

            if result.success:
                response_data = result.to_dict()
                # Add payment instructions for bank transfer
                if "instructions" in result.provider_data:
                    response_data["instructions"] = result.provider_data["instructions"]
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Payment provider not configured or other error
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
                if result.error and result.error.code == "PROVIDER_NOT_CONFIGURED":
                    response_data = {
                        "error": "Payment service is not available",
                        "message": f"{result.provider} is not configured",
                        "service_status": "disabled",
                        "provider": result.provider,
                    }
                else:
                    http_status = status.HTTP_400_BAD_REQUEST
                    response_data = result.to_dict()

                return Response(response_data, status=http_status)

        except PaymentError as e:
            logger.error(f"Payment intent creation error: {e}")
            return Response(
                {
                    "error": e.message,
                    "code": e.code,
                    "provider": e.provider,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger.error(f"Unexpected error in payment intent creation: {e}")
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConfirmPaymentAPI(APIView):
    """
    Confirm a payment intent (for providers requiring explicit confirmation).
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Confirm and process a payment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "transaction_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Transaction/payment intent ID",
                ),
                "payment_method_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment method ID (for Stripe)",
                ),
                "provider": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment provider (auto-detected if not provided)",
                ),
            },
            required=["transaction_id"],
        ),
        responses={
            200: "Payment confirmed successfully",
            400: "Bad Request",
            404: "Transaction not found",
        },
    )
    def post(self, request):
        try:
            transaction_id = request.data.get("transaction_id")
            payment_method_id = request.data.get("payment_method_id")
            provider = request.data.get("provider")

            if not transaction_id:
                return Response(
                    {"error": "Transaction ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = payment_manager.confirm_payment(
                transaction_id=transaction_id,
                payment_method_id=payment_method_id,
                provider=provider,
            )

            return Response(result.to_dict(), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Payment confirmation error: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetPaymentStatusAPI(APIView):
    """
    Get the current status of a payment.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get payment status",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "transaction_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Transaction ID",
                ),
                "provider": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment provider (auto-detected if not provided)",
                ),
            },
            required=["transaction_id"],
        ),
        responses={
            200: "Payment status retrieved",
            404: "Transaction not found",
        },
    )
    def post(self, request):
        try:
            transaction_id = request.data.get("transaction_id")
            provider = request.data.get("provider")

            if not transaction_id:
                return Response(
                    {"error": "Transaction ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = payment_manager.get_payment_status(
                transaction_id=transaction_id,
                provider=provider,
            )

            return Response(result.to_dict(), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Payment status check error: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefundPaymentAPI(APIView):
    """
    Refund a payment (full or partial).
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Refund a payment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "transaction_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Transaction ID to refund"
                ),
                "amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Refund amount (omit for full refund)",
                ),
                "reason": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Refund reason"
                ),
                "provider": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment provider (auto-detected if not provided)",
                ),
            },
            required=["transaction_id"],
        ),
        responses={
            200: "Refund processed",
            400: "Bad Request",
            404: "Transaction not found",
        },
    )
    def post(self, request):
        try:
            from decimal import Decimal

            from myapp.models import Payment
            from myapp.services.payment.refund import RefundService

            transaction_id = request.data.get("transaction_id")
            amount = request.data.get("amount")
            reason = request.data.get("reason", "Refund requested by customer")

            if not transaction_id:
                return Response(
                    {"error": "Transaction ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Look up the payment by reference number
            payment = Payment.objects.filter(
                reference_number=transaction_id,
                is_deleted=0,
            ).first()

            if not payment:
                return Response(
                    {"error": "Payment not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            refund_amount = Decimal(str(amount)) if amount else None
            result = RefundService.process_refund(
                payment_id=payment.payment_id,
                amount=refund_amount,
                reason=reason,
            )

            if result.get("success"):
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Payment refund error: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentProvidersAPI(APIView):
    """
    Get available payment providers and their status.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Get available payment providers",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "available": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_STRING),
                    ),
                    "configured": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_STRING),
                    ),
                    "default_provider": openapi.Schema(type=openapi.TYPE_STRING),
                    "providers": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        additional_properties=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "name": openapi.Schema(type=openapi.TYPE_STRING),
                                "display_name": openapi.Schema(
                                    type=openapi.TYPE_STRING
                                ),
                                "configured": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            },
                        ),
                    ),
                },
            ),
        },
    )
    def get(self, request):
        try:
            factory = PaymentProviderFactory()
            available = factory.get_available_providers()
            configured = factory.get_configured_providers()

            # Get provider details
            providers_info = {}
            for name in available:
                try:
                    provider = factory.create(name)
                    providers_info[name] = {
                        "name": name,
                        "display_name": provider.display_name,
                        "configured": provider.is_configured(),
                    }
                except Exception:
                    providers_info[name] = {
                        "name": name,
                        "display_name": name.title(),
                        "configured": False,
                    }

            return Response(
                {
                    "available": available,
                    "configured": configured,
                    "default_provider": payment_manager.preferred_provider,
                    "providers": providers_info,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error getting payment providers: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WebhookAPI(APIView):
    """
    Handle payment provider webhooks.

    Supports webhooks from Stripe, PayPal, and other providers.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Handle payment webhook",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Raw webhook payload (provider-specific format)",
        ),
        manual_parameters=[
            openapi.Parameter(
                "provider",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                description="Payment provider (stripe, paypal)",
                required=True,
                enum=["stripe", "paypal"],
            ),
        ],
        responses={
            200: "Webhook processed",
            400: "Invalid webhook",
            401: "Webhook signature verification failed",
        },
    )
    def post(self, request, provider: str):
        try:
            # Get raw payload
            payload = request.body

            # Parse and verify webhook
            event = payment_manager.parse_webhook(
                provider=provider,
                payload=payload,
                headers=request.headers,
            )

            # Handle the event
            result = payment_manager.handle_webhook(
                provider=provider,
                event=event,
                request=request,
            )

            return Response(result, status=status.HTTP_200_OK)

        except PaymentError as e:
            logger.error(f"Webhook processing error: {e}")
            return Response(
                {
                    "error": e.message,
                    "code": e.code,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            logger.error(f"Unexpected webhook error: {e}")
            return Response(
                {"error": "Webhook processing failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
