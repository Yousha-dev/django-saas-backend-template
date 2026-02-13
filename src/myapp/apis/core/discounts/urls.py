from django.urls import path

from .apis import ApplyCouponAPI, ValidateCouponAPI

urlpatterns = [
    path("validate/", ValidateCouponAPI.as_view(), name="validate_coupon"),
    path("apply/", ApplyCouponAPI.as_view(), name="apply_coupon"),
]
