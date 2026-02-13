import logging
import random
import string
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class ReferralService:
    """
    Service to manage referral codes, applications, and rewards.

    Integrates with ReferralCode and ReferralTransaction models
    for full database-backed referral program management.
    """

    @staticmethod
    def generate_referral_code(
        user_id: int, reward_type: str = "credit", reward_amount: float = 10.0
    ) -> dict[str, Any]:
        """
        Generate a unique referral code for a user.

        Args:
            user_id: ID of the user to generate code for
            reward_type: Type of reward (credit, discount, free_month, feature_unlock)
            reward_amount: Amount of reward

        Returns:
            Dict with code details or error
        """
        from myapp.models import ReferralCode

        try:
            # Check if user already has an active referral code
            existing = ReferralCode.objects.filter(
                user_id=user_id,
                is_active=1,
                is_deleted=0,
            ).first()

            if existing:
                return {
                    "success": True,
                    "code": existing.code,
                    "message": "User already has an active referral code.",
                    "referral_code_id": existing.referral_code_id,
                }

            # Generate unique code
            for _ in range(10):  # Max 10 attempts
                chars = string.ascii_uppercase + string.digits
                code = "".join(random.choices(chars, k=8))  # noqa: S311
                if not ReferralCode.objects.filter(code=code).exists():
                    break
            else:
                return {"success": False, "message": "Failed to generate unique code."}

            # Create referral code
            referral_code = ReferralCode.objects.create(
                user_id=user_id,
                code=code,
                max_uses=0,  # Unlimited by default
                current_uses=0,
                reward_type=reward_type,
                reward_amount=Decimal(str(reward_amount)),
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=user_id,
            )

            logger.info(f"Generated referral code '{code}' for user {user_id}")

            return {
                "success": True,
                "code": referral_code.code,
                "referral_code_id": referral_code.referral_code_id,
                "reward_type": reward_type,
                "reward_amount": float(reward_amount),
                "message": "Referral code generated successfully.",
            }

        except Exception as e:
            logger.error(f"Error generating referral code for user {user_id}: {e}")
            return {"success": False, "message": "Error generating referral code."}

    @staticmethod
    @transaction.atomic
    def apply_referral(referrer_code: str, new_user_id: int) -> dict[str, Any]:
        """
        Apply a referral code when a new user signs up.

        Validates the code, creates a referral transaction, and
        increments the usage counter.

        Args:
            referrer_code: The referral code string
            new_user_id: ID of the new user being referred

        Returns:
            Dict with success status and details
        """
        from myapp.models import ReferralCode, ReferralTransaction

        try:
            # Validate code
            code_obj = (
                ReferralCode.objects.filter(
                    code__iexact=referrer_code,
                    is_active=1,
                    is_deleted=0,
                )
                .select_related("user")
                .first()
            )

            if not code_obj:
                return {"success": False, "message": "Invalid referral code."}

            if not code_obj.is_valid:
                return {
                    "success": False,
                    "message": "This referral code is no longer valid.",
                }

            # Prevent self-referral
            if code_obj.user_id == new_user_id:
                return {
                    "success": False,
                    "message": "You cannot use your own referral code.",
                }

            # Check if already referred
            already_referred = ReferralTransaction.objects.filter(
                referred_user_id=new_user_id,
                is_deleted=0,
            ).exists()
            if already_referred:
                return {"success": False, "message": "User has already been referred."}

            # Create transaction record
            tx = ReferralTransaction.objects.create(
                referral_code=code_obj,
                referred_user_id=new_user_id,
                referrer_rewarded=False,
                referred_rewarded=False,
                referrer_reward_amount=code_obj.reward_amount,
                referred_reward_amount=Decimal("0"),
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=new_user_id,
            )

            # Increment usage
            code_obj.use()

            logger.info(
                f"Referral code '{referrer_code}' applied for user {new_user_id}"
            )

            return {
                "success": True,
                "message": "Referral applied successfully.",
                "referrer_id": code_obj.user_id,
                "reward_type": code_obj.reward_type,
                "reward_amount": float(code_obj.reward_amount),
                "transaction_id": tx.transaction_id,
            }

        except Exception as e:
            logger.error(f"Error applying referral code '{referrer_code}': {e}")
            return {"success": False, "message": "Error applying referral code."}

    @staticmethod
    def reward_referrer(
        referrer_id: int, reward_type: str = "credit", amount: float = 10.0
    ) -> dict[str, Any]:
        """
        Give reward to the referrer after the referred user completes
        a qualifying action (e.g., first payment, subscription activation).

        Args:
            referrer_id: User ID of the referrer to reward
            reward_type: Type of reward to give
            amount: Amount of reward

        Returns:
            Dict with success status
        """
        from myapp.models import ReferralTransaction
        from myapp.services.subscription_service import SubscriptionService

        try:
            # Find unrewarded transactions for this referrer
            unrewarded_txs = ReferralTransaction.objects.filter(
                referral_code__user_id=referrer_id,
                referrer_rewarded=False,
                is_deleted=0,
            )

            if not unrewarded_txs.exists():
                return {"success": False, "message": "No unrewarded referrals found."}

            rewarded_count = 0
            for tx in unrewarded_txs:
                if reward_type == "free_month":
                    # Extend subscription by 30 days
                    from myapp.models import User

                    referrer = User.objects.get(user_id=referrer_id)
                    SubscriptionService.extend_subscription(referrer, days=30)
                elif reward_type == "credit":
                    # Credit reward — log for manual processing or integrate with payment
                    logger.info(
                        f"Credit reward of ${amount} for referrer {referrer_id}"
                    )
                elif reward_type == "discount":
                    # Create a discount coupon for the referrer
                    logger.info(
                        f"Discount reward of {amount}% for referrer {referrer_id}"
                    )

                tx.referrer_rewarded = True
                tx.referrer_reward_amount = Decimal(str(amount))
                tx.updated_at = timezone.now()
                tx.save()
                rewarded_count += 1

            logger.info(
                f"Rewarded referrer {referrer_id}: {rewarded_count} referrals, {reward_type}=${amount}"
            )

            return {
                "success": True,
                "message": f"Rewarded {rewarded_count} referral(s).",
                "rewarded_count": rewarded_count,
                "reward_type": reward_type,
                "reward_amount": amount,
            }

        except Exception as e:
            logger.error(f"Error rewarding referrer {referrer_id}: {e}")
            return {"success": False, "message": "Error processing reward."}

    @staticmethod
    def get_referral_stats(user_id: int) -> dict[str, Any]:
        """Get referral statistics for a user."""
        from myapp.models import ReferralCode, ReferralTransaction

        try:
            code_obj = ReferralCode.objects.filter(
                user_id=user_id,
                is_active=1,
                is_deleted=0,
            ).first()

            if not code_obj:
                return {
                    "has_code": False,
                    "total_referrals": 0,
                    "successful_referrals": 0,
                    "total_rewards_earned": 0,
                }

            transactions = ReferralTransaction.objects.filter(
                referral_code=code_obj,
                is_deleted=0,
            )

            total = transactions.count()
            rewarded = transactions.filter(referrer_rewarded=True)
            total_rewards = sum(float(tx.referrer_reward_amount) for tx in rewarded)

            return {
                "has_code": True,
                "code": code_obj.code,
                "total_referrals": total,
                "successful_referrals": rewarded.count(),
                "total_rewards_earned": total_rewards,
                "reward_type": code_obj.reward_type,
                "reward_per_referral": float(code_obj.reward_amount),
            }

        except Exception as e:
            logger.error(f"Error getting referral stats for user {user_id}: {e}")
            return {"has_code": False, "total_referrals": 0, "error": str(e)}
