# myapp/apis/payment/urls.py
"""
URL configuration for payment API endpoints.
"""

from django.urls import path

from myapp.apis.payment.payment_api import (
    ConfirmPaymentAPI,
    CreatePaymentIntentAPI,
    GetPaymentStatusAPI,
    PaymentProvidersAPI,
    RefundPaymentAPI,
    WebhookAPI,
)

app_name = "payment"

urlpatterns = [
    # Payment intents
    path("create-intent/", CreatePaymentIntentAPI.as_view(), name="create_intent"),
    path("confirm/", ConfirmPaymentAPI.as_view(), name="confirm_payment"),
    path("status/", GetPaymentStatusAPI.as_view(), name="payment_status"),
    path("refund/", RefundPaymentAPI.as_view(), name="refund_payment"),
    # Provider information
    path("providers/", PaymentProvidersAPI.as_view(), name="providers"),
    # Webhooks
    path("webhook/<str:provider>/", WebhookAPI.as_view(), name="webhook"),
]
