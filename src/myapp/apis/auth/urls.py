from django.urls import path

from myapp.views import CustomTokenObtainPairView

from .auth_api import (
    ChangeUserPasswordAPI,
    CreateStripePaymentIntentAPI,
    DeactivateUserAPI,
    DeleteUserAPI,
    ListSubscriptionPlansAPI,
    LoginAPI,
    PaymentServiceStatusAPI,
    RegisterUserAPI,
    RegisterUserSubscriptionAPI,
    RequestPasswordResetAPI,
    ResetPasswordAPI,
    SendEmailAPI,
)

urlpatterns = [
    path(
        "subscriptionplans/",
        ListSubscriptionPlansAPI.as_view(),
        name="list_subscriptionplans",
    ),
    path("users/delete-user/", DeleteUserAPI.as_view(), name="delete_user"),
    path("register/", RegisterUserSubscriptionAPI.as_view(), name="register"),
    path("register-user/", RegisterUserAPI.as_view(), name="register_user"),
    path("login/", LoginAPI.as_view(), name="login"),
    path(
        "request-password-reset/",
        RequestPasswordResetAPI.as_view(),
        name="request-password-reset",
    ),
    path("reset-password/", ResetPasswordAPI.as_view(), name="reset-password"),
    path(
        "users/change-password/",
        ChangeUserPasswordAPI.as_view(),
        name="change-user-password",
    ),
    path("users/deactivate-user/", DeactivateUserAPI.as_view(), name="deactivate_user"),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(
        "payment/create-intent/",
        CreateStripePaymentIntentAPI.as_view(),
        name="create-stripe-payment-intent",
    ),
    path(
        "payment/status/",
        PaymentServiceStatusAPI.as_view(),
        name="payment-service-status",
    ),  # Add this
    path("send-email/", SendEmailAPI.as_view(), name="send_email"),
]
