from django.urls import path

from .apis import ApplyReferralAPI, GenerateReferralCodeAPI, ReferralStatsAPI

urlpatterns = [
    path("generate/", GenerateReferralCodeAPI.as_view(), name="generate_referral_code"),
    path("apply/", ApplyReferralAPI.as_view(), name="apply_referral"),
    path("stats/", ReferralStatsAPI.as_view(), name="referral_stats"),
]
