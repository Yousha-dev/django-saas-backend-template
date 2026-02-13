import logging
from decimal import Decimal
from typing import Any

from django.utils import timezone

from myapp.models.choices import PaymentStatus

logger = logging.getLogger(__name__)


class DiscountService:
    """
    Service to manage coupons and discounts.

    Integrates with the Coupon and CouponUsage models to validate,
    apply, and track discount coupon usage.
    """

    @staticmethod
    def validate_coupon(
        code: str, user_id: int, plan_id: int | None = None
    ) -> dict[str, Any]:
        """
        Validate a coupon code for a specific user and optional plan.

        Checks:
        - Coupon exists and is active
        - Coupon is within valid date range
        - Usage limits not exceeded (global and per-user)
        - Plan eligibility (if applicable_plans specified)
        - First purchase restriction (if enabled)

        Returns:
            Dict with 'valid', 'discount_type', 'amount', 'coupon_id', etc.
        """
        from myapp.models import Coupon

        logger.info(f"Validating coupon '{code}' for user {user_id}")

        try:
            coupon = Coupon.objects.filter(
                code__iexact=code,
                is_active=1,
                is_deleted=0,
            ).first()

            if not coupon:
                return {"valid": False, "message": "Invalid coupon code."}

            # Check date validity
            now = timezone.now()
            if now < coupon.valid_from:
                return {"valid": False, "message": "This coupon is not yet active."}
            if now > coupon.valid_until:
                return {"valid": False, "message": "This coupon has expired."}

            # Check global usage limit
            if coupon.max_uses > 0 and coupon.current_uses >= coupon.max_uses:
                return {
                    "valid": False,
                    "message": "This coupon has reached its usage limit.",
                }

            # Check per-user usage limit
            if not coupon.can_be_used_by(user_id):
                return {"valid": False, "message": "You have already used this coupon."}

            # Check plan eligibility
            if (
                plan_id
                and coupon.applicable_plans.exists()
                and not coupon.applicable_plans.filter(
                    subscription_plan_id=plan_id
                ).exists()
            ):
                return {
                    "valid": False,
                    "message": "This coupon is not valid for the selected plan.",
                }

            # Check first purchase restriction
            if coupon.first_purchase_only:
                from myapp.models import Payment

                has_previous_payment = Payment.objects.filter(
                    user_id=user_id,
                    status=PaymentStatus.COMPLETED.value,
                    is_deleted=0,
                ).exists()
                if has_previous_payment:
                    return {
                        "valid": False,
                        "message": "This coupon is only valid for first-time purchases.",
                    }

            return {
                "valid": True,
                "coupon_id": coupon.coupon_id,
                "discount_type": coupon.discount_type,
                "amount": float(coupon.discount_value),
                "code": coupon.code,
                "description": coupon.description,
                "min_purchase_amount": float(coupon.min_purchase_amount)
                if coupon.min_purchase_amount
                else None,
            }

        except Exception as e:
            logger.error(f"Error validating coupon '{code}': {e}")
            return {"valid": False, "message": "Error validating coupon."}

    @staticmethod
    def apply_coupon(
        code: str, user_id: int, original_amount: Decimal
    ) -> dict[str, Any]:
        """
        Apply a validated coupon and record the usage.

        Args:
            code: Coupon code
            user_id: User applying the coupon
            original_amount: Original price before discount

        Returns:
            Dict with discount details and final amount
        """
        from myapp.models import Coupon, CouponUsage

        try:
            coupon = Coupon.objects.get(code__iexact=code, is_active=1, is_deleted=0)

            # Calculate discount
            discount_data = {
                "valid": True,
                "discount_type": coupon.discount_type,
                "amount": float(coupon.discount_value),
            }
            final_amount = DiscountService.calculate_discounted_price(
                original_amount, discount_data
            )
            discount_applied = original_amount - final_amount

            # Check minimum purchase amount
            if (
                coupon.min_purchase_amount
                and original_amount < coupon.min_purchase_amount
            ):
                return {
                    "success": False,
                    "message": f"Minimum purchase of ${coupon.min_purchase_amount} required.",
                }

            # Record usage
            CouponUsage.objects.create(
                coupon=coupon,
                user_id=user_id,
                discount_applied=discount_applied,
                original_amount=original_amount,
                final_amount=final_amount,
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=user_id,
            )

            # Increment coupon usage counter
            coupon.apply()

            logger.info(
                f"Coupon '{code}' applied for user {user_id}: ${discount_applied} discount"
            )

            return {
                "success": True,
                "discount_applied": float(discount_applied),
                "original_amount": float(original_amount),
                "final_amount": float(final_amount),
                "coupon_code": code,
            }

        except Coupon.DoesNotExist:
            return {"success": False, "message": "Coupon not found."}
        except Exception as e:
            logger.error(f"Error applying coupon '{code}': {e}")
            return {"success": False, "message": "Error applying coupon."}

    @staticmethod
    def calculate_discounted_price(
        original_price: Decimal, discount_data: dict[str, Any]
    ) -> Decimal:
        """
        Calculate the new price based on discount data.

        Args:
            original_price: Original price as Decimal
            discount_data: Dict with 'valid', 'discount_type', 'amount'

        Returns:
            Discounted price as Decimal (never below 0)
        """
        if not discount_data.get("valid"):
            return original_price

        amount = discount_data.get("amount", 0)
        dtype = discount_data.get("discount_type")

        if dtype == "percentage":
            discount = original_price * (Decimal(str(amount)) / Decimal("100"))
            return max(Decimal("0"), original_price - discount)
        elif dtype == "fixed":
            return max(Decimal("0"), original_price - Decimal(str(amount)))

        return original_price
