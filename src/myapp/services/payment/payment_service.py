# myapp/services/payment/payment_service.py
"""
Unified PaymentService orchestrating discount, referral, and payment operations.

This service serves as the single entry point for processing payments,
coordinating coupon validation, price calculation, payment intent creation,
coupon usage recording, and referral rewards.
"""

import logging
from decimal import Decimal
from typing import Any

from django.db import transaction

from myapp.models.choices import PaymentStatus
from myapp.payment_strategies.factory import get_payment_manager

from .discount import DiscountService
from .referral import ReferralService

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Orchestrates the full payment flow:
    1. Validate coupon (if provided)
    2. Calculate discounted price
    3. Create payment intent via provider
    4. Record coupon usage
    5. Reward referrer (if applicable)
    """

    @staticmethod
    @transaction.atomic
    def create_payment(
        user_id: int,
        amount: Decimal,
        currency: str = "USD",
        provider: str = "stripe",
        description: str | None = None,
        coupon_code: str | None = None,
        referral_code: str | None = None,
        plan_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a payment with optional coupon and referral handling.

        Args:
            user_id: ID of the user making the payment
            amount: Base price before discounts
            currency: Currency code (default: USD)
            provider: Payment provider name (stripe, paypal, etc.)
            description: Payment description
            coupon_code: Optional coupon code for discount
            referral_code: Optional referral code to apply
            plan_id: Optional subscription plan ID (for coupon eligibility)
            metadata: Optional metadata dict
            **kwargs: Extra args forwarded to payment provider

        Returns:
            Dict with payment result, discount info, and referral info
        """
        result: dict[str, Any] = {
            "success": False,
            "original_amount": float(amount),
            "final_amount": float(amount),
            "discount_applied": 0.0,
            "coupon_code": coupon_code,
            "referral_code": referral_code,
        }

        final_amount = amount

        # Step 1: Validate and apply coupon
        if coupon_code:
            validation = DiscountService.validate_coupon(
                code=coupon_code,
                user_id=user_id,
                plan_id=plan_id,
            )
            if not validation.get("valid"):
                result["message"] = validation.get("message", "Invalid coupon.")
                return result

            final_amount = DiscountService.calculate_discounted_price(
                original_price=amount,
                discount_data=validation,
            )
            result["discount_applied"] = float(amount - final_amount)
            result["final_amount"] = float(final_amount)

        # Step 2: Apply referral code (for new signups)
        referral_result = None
        if referral_code:
            referral_result = ReferralService.apply_referral(
                referrer_code=referral_code,
                new_user_id=user_id,
            )
            result["referral_applied"] = referral_result.get("success", False)
            if not referral_result.get("success"):
                logger.warning(
                    f"Referral code '{referral_code}' application failed: "
                    f"{referral_result.get('message')}"
                )

        # Step 3: Create payment intent via provider
        manager = get_payment_manager()
        payment_metadata = metadata or {}
        payment_metadata["user_id"] = str(user_id)
        if coupon_code:
            payment_metadata["coupon_code"] = coupon_code
        if referral_code:
            payment_metadata["referral_code"] = referral_code

        payment_result = manager.create_payment(
            amount=final_amount,
            currency=currency,
            provider=provider,
            description=description or f"Payment for user {user_id}",
            metadata=payment_metadata,
            **kwargs,
        )

        if not payment_result.success:
            error_msg = (
                payment_result.error.message
                if payment_result.error
                else payment_result.message
            )
            result["message"] = error_msg or "Payment failed."
            return result

        # Step 4: Record coupon usage (after successful payment intent)
        if coupon_code:
            coupon_result = DiscountService.apply_coupon(
                code=coupon_code,
                user_id=user_id,
                original_amount=amount,
            )
            if not coupon_result.get("success"):
                logger.warning(
                    f"Coupon usage recording failed: {coupon_result.get('message')}"
                )

        # Step 5: Reward referrer
        if referral_result and referral_result.get("success"):
            referrer_id = referral_result.get("referrer_id")
            if referrer_id:
                reward_result = ReferralService.reward_referrer(
                    referrer_id=referrer_id,
                    reward_type=referral_result.get("reward_type", "credit"),
                    amount=referral_result.get("reward_amount", 10.0),
                )
                result["referrer_rewarded"] = reward_result.get("success", False)

        result.update(
            {
                "success": True,
                "transaction_id": payment_result.transaction_id,
                "provider_transaction_id": payment_result.provider_transaction_id,
                "status": payment_result.status.value
                if isinstance(payment_result.status, PaymentStatus)
                else str(payment_result.status),
                "provider": payment_result.provider,
                "message": "Payment created successfully.",
            }
        )

        logger.info(
            f"Payment created for user {user_id}: "
            f"amount={final_amount} {currency}, "
            f"provider={provider}, "
            f"tx={payment_result.transaction_id}"
        )

        return result
