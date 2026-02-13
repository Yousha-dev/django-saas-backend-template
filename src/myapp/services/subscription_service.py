# myapp/services/subscription_service.py
"""
Refactored subscription service using generic feature flags.

This service now works with a domain-agnostic feature flag system
instead of hardcoded domain-specific features.

Key improvements:
- Generic feature flag checking via FeatureFlags model
- Type hints for better IDE support
- Improved error handling
- Documentation for all methods
"""

import logging
from datetime import timedelta
from typing import Any

from django.utils import timezone

from myapp.models import Subscription, SubscriptionPlan, User
from myapp.models.choices import SubscriptionStatus
from myapp.models.features import FeatureDefinition, FeatureFlags

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service to handle subscription features and limits using generic feature flags."""

    # ==========================================================================
    # PRIVATE HELPER METHODS
    # ==========================================================================

    @classmethod
    def _get_subscription_plan(
        cls, subscription: Subscription
    ) -> SubscriptionPlan | None:
        """Get subscription plan for a subscription."""
        try:
            return subscription.subscription_plan
        except Exception:
            return None

    @classmethod
    def _get_feature_flags(cls, plan: SubscriptionPlan) -> FeatureFlags | None:
        """Get feature flags for a subscription plan."""
        try:
            return plan.feature_flags
        except Exception:
            return None

    @classmethod
    def _create_trial_subscription(cls, user: User) -> Subscription:
        """Create a trial subscription for a user. Alias for _get_default_subscription."""
        return cls._get_default_subscription(user)

    @classmethod
    def _get_default_subscription(cls, user: User) -> Subscription:
        """Create default subscription for new users only."""
        # Get free/trial plan
        trial_plan = (
            SubscriptionPlan.objects.filter(is_active=1, is_deleted=0, monthly_price=0)
            .order_by("subscription_plan_id")
            .first()
        )

        if not trial_plan:
            # No free plan exists, get cheapest plan for trial
            trial_plan = (
                SubscriptionPlan.objects.filter(is_active=1, is_deleted=0)
                .order_by("monthly_price")
                .first()
            )

        if not trial_plan:
            raise Exception("No subscription plans available in system")

        # Create trial subscription
        subscription = Subscription.objects.create(
            user=user,
            subscription_plan=trial_plan,
            billing_frequency="Monthly",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),  # 30-day trial
            auto_renew=0,
            status="Active",
            is_active=1,
            is_deleted=0,
            created_at=timezone.now(),
            created_by=user.user_id if hasattr(user, "user_id") else 1,
        )

        logger.info(
            f"Created trial subscription for user {user.user_id} with plan {trial_plan.name}"
        )
        return subscription

    @classmethod
    def is_trial_eligible(cls, user: User) -> tuple[bool, str]:
        """Check if user is eligible for a free trial."""
        try:
            # Check if user ever had a free trial (monthly_price = 0)
            had_trial = Subscription.objects.filter(
                user=user, subscription_plan__monthly_price=0, is_deleted=0
            ).exists()

            if had_trial:
                return False, "User has already used their free trial"
            return True, "User is eligible for free trial"

        except Exception as e:
            logger.error(
                f"Error checking trial eligibility for user {user.user_id}: {e!s}"
            )
            return False, f"Error checking trial eligibility: {e!s}"

    @classmethod
    def is_subscription_valid(cls, user: User) -> tuple[bool, str]:
        """Check if user has valid active subscription."""
        try:
            subscription = cls.get_user_subscription(user)

            if subscription.status != "Active":
                return False, f"Subscription is {subscription.status}"

            if subscription.end_date < timezone.now().date():
                return False, "Subscription has expired"
            return True, "Subscription is valid"

        except Exception as e:
            logger.error(
                f"Error checking subscription validity for user {user.user_id}: {e!s}"
            )
            return False, f"Error checking subscription: {e!s}"

    # ==========================================================================
    # PUBLIC API METHODS
    # ==========================================================================

    @classmethod
    def get_user_subscription(cls, user: User) -> Subscription | None:
        """Get user's active subscription."""
        try:
            # First check for any active subscription
            subscription = (
                Subscription.objects.select_related("subscription_plan")
                .filter(user=user, status="Active", is_active=1, is_deleted=0)
                .first()
            )

            # If subscription exists, check if it's expired
            if subscription:
                if subscription.end_date < timezone.now().date():
                    # Mark as expired with proper audit fields
                    subscription.status = "Expired"
                    subscription.updated_by = (
                        user.user_id if hasattr(user, "user_id") else 1
                    )
                    subscription.updated_at = timezone.now()
                    subscription.save()
                    return cls._handle_expired_subscription(user, subscription)
                return subscription

            # No active subscription found, create default
            return cls._get_default_subscription(user)

        except Exception as e:
            logger.error(
                f"Error getting user subscription for user {user.user_id}: {e!s}"
            )
            raise Exception(f"Failed to get user subscription: {e!s}") from e

    @classmethod
    def _handle_expired_subscription(
        cls, user: User, expired_subscription: Subscription
    ) -> Subscription:
        """Handle expired subscription - check if user had trial before."""
        try:
            # Check if user is eligible for trial
            is_eligible, _message = cls.is_trial_eligible(user)

            if is_eligible:
                # User never had trial, give them one
                return cls._create_trial_subscription(user)
            else:
                # User already had trial, return expired subscription
                return expired_subscription

        except Exception as e:
            logger.error(
                f"Error handling expired subscription for user {user.user_id}: {e!s}"
            )
            return expired_subscription

    # ==========================================================================
    # GENERIC FEATURE CHECK METHODS (Domain Agnostic)
    # ==========================================================================

    @classmethod
    def can_use_feature(cls, user: User, feature_path: str) -> tuple[bool, str]:
        """
        Generic method to check if user can access a feature.

        Args:
            user: The user to check
            feature_path: Dot-notation feature path (use FeatureDefinition constants)

        Returns:
            (bool, str) - (is_enabled, message)

        Examples:
            can_use_feature(user, FeatureDefinition.API_ENABLED)
            can_use_feature(user, FeatureDefinition.AI_ANALYTICS_ENABLED)
        """
        try:
            is_valid, validity_msg = cls.is_subscription_valid(user)

            if not is_valid:
                return False, validity_msg

            subscription = cls.get_user_subscription(user)
            flags = cls._get_feature_flags(subscription.subscription_plan)

            if not flags:
                return False, "No feature flags configured for this plan"

            is_enabled = flags.is_enabled(feature_path)
            feature_name = feature_path.split(".")[-1].replace("_", " ").title()

            if is_enabled:
                return True, f"{feature_name} is available in your plan"
            return False, f"{feature_name} is not available in your plan"

        except Exception as e:
            logger.error(
                f"Error checking feature {feature_path} for user {user.user_id}: {e!s}"
            )
            return False, f"Error checking feature: {e!s}"

    @classmethod
    def can_use_automation(cls, user: User) -> tuple[bool, str]:
        """Check if user can use automation features (webhooks, scheduled tasks)."""
        return cls.can_use_feature(user, FeatureDefinition.WEBHOOK_ENABLED)

    @classmethod
    def get_subscription_features(cls, user: User) -> dict[str, Any]:
        """
        Get user's subscription features as a generic dictionary.

        Returns a domain-agnostic feature structure:
        {
            'subscription_id': int,
            'plan_id': int,
            'plan_name': str,
            'plan_description': str,
            'monthly_price': float,
            'yearly_price': float,
            'features': {
                # Generic feature flags - works for any domain
                'api_access': {'enabled': bool, 'calls_per_hour': int},
                'ai_analytics': {'enabled': bool, 'limit': int},
                'advanced_analytics': {'enabled': bool},
                'real_time_data': {'enabled': bool},
                'export_formats': {'csv': bool, 'pdf': bool, 'excel': bool},
                'team_collaboration': {'enabled': bool, 'max_members': int},
                'custom_reports': {'enabled': bool, 'max_per_month': int},
                'integrations': {'slack': bool, 'webhook': bool},
            },
            'subscription_status': str,
            'subscription_start_date': date,
            'subscription_end_date': date,
            'billing_frequency': str,
            'auto_renew': bool,
            'is_valid': bool,
            'validity_message': str
        }
        """
        try:
            subscription = cls.get_user_subscription(user)
            plan = subscription.subscription_plan
            flags = cls._get_feature_flags(plan)

            is_valid, validity_msg = cls.is_subscription_valid(user)

            # Build generic feature flags dict
            features_dict = {}
            if flags:
                features_dict = flags.get_all_features()

            return {
                "subscription_id": subscription.subscription_id,
                "plan_id": plan.subscription_plan_id,
                "plan_name": plan.name,
                "plan_description": plan.description,
                "monthly_price": float(plan.monthly_price) if plan.monthly_price else 0,
                "yearly_price": float(plan.yearly_price) if plan.yearly_price else 0,
                "features": features_dict,
                "subscription_status": subscription.status,
                "subscription_start_date": subscription.start_date,
                "subscription_end_date": subscription.end_date,
                "billing_frequency": subscription.billing_frequency,
                "auto_renew": bool(subscription.auto_renew),
                "is_valid": is_valid,
                "validity_message": validity_msg,
            }

        except Exception as e:
            logger.error(
                f"Error getting subscription features for user {user.user_id}: {e!s}"
            )
            return {
                "error": str(e),
                "features": {},
                "is_valid": False,
                "validity_message": f"Error: {e!s}",
            }

    @classmethod
    def get_api_limit(cls, user: User) -> tuple[bool, str]:
        """Check API rate limit status."""
        is_valid, msg = cls.is_subscription_valid(user)
        if not is_valid:
            return False, msg

        subscription = cls.get_user_subscription(user)
        flags = cls._get_feature_flags(subscription.subscription_plan)

        if not flags:
            return False, "No feature flags configured for this plan"

        max_calls = flags.get_feature(FeatureDefinition.API_CALLS_PER_HOUR, default=0)
        if max_calls > 0:
            return True, f"API limit: {max_calls} calls per hour"
        return False, "API access not configured for this plan"

    @classmethod
    def check_api_limit(cls, user: User) -> tuple[bool, dict[str, Any]]:
        """Check API limit and return detailed info."""
        is_valid, msg = cls.get_api_limit(user)
        if not is_valid:
            return False, {"error": msg}

        subscription = cls.get_user_subscription(user)
        flags = cls._get_feature_flags(subscription.subscription_plan)
        max_calls = flags.get_feature(FeatureDefinition.API_CALLS_PER_HOUR, default=0)

        return True, {
            "max_calls_per_hour": max_calls,
            "current_usage": 0,  # Placeholder for actual usage tracking
            "remaining": max_calls,
        }

    @classmethod
    def check_operation_limit(cls, user: User) -> tuple[bool, str]:
        """Check operation limit status."""
        is_valid, msg = cls.is_subscription_valid(user)
        if not is_valid:
            return False, msg

        subscription = cls.get_user_subscription(user)
        flags = cls._get_feature_flags(subscription.subscription_plan)

        if not flags:
            return False, "No feature flags configured for this plan"

        max_ops = flags.get_feature(FeatureDefinition.API_DAILY_LIMIT, default=0)
        if max_ops > 0:
            return True, f"Daily limit: {max_ops} operations"
        return False, "Operation limit not configured for this plan"

    # ==========================================================================
    # SUBSCRIPTION MANAGEMENT METHODS
    # ==========================================================================

    @classmethod
    def change_user_subscription_plan(
        cls, user: User, new_plan_id: int
    ) -> tuple[bool, str]:
        """Change user to a different subscription plan."""
        try:
            # Validate new plan exists
            new_plan = SubscriptionPlan.objects.get(
                subscription_plan_id=new_plan_id, is_active=1, is_deleted=0
            )

            # Get current subscription
            current_subscription = cls.get_user_subscription(user)

            # Don't allow changing to the same plan
            if (
                current_subscription.subscription_plan.subscription_plan_id
                == new_plan_id
            ):
                return False, "Already subscribed to this plan"

            # Update the subscription plan
            current_subscription.subscription_plan = new_plan
            current_subscription.updated_by = (
                user.user_id if hasattr(user, "user_id") else 1
            )
            current_subscription.updated_at = timezone.now()

            # Handle subscription duration based on plan type and billing frequency
            if new_plan.monthly_price > 0:
                # Paid plan - extend subscription based on billing frequency
                if current_subscription.billing_frequency == "Yearly":
                    current_subscription.end_date = timezone.now().date() + timedelta(
                        days=365
                    )
                else:
                    current_subscription.end_date = timezone.now().date() + timedelta(
                        days=30
                    )
                current_subscription.status = "Active"
            else:
                # Free plan - set trial period
                current_subscription.end_date = timezone.now().date() + timedelta(
                    days=30
                )
                current_subscription.status = "Active"

            current_subscription.save()

            logger.info(
                f"Changed subscription for user {user.user_id} to plan {new_plan.name}"
            )
            return True, f"Successfully changed to {new_plan.name}"

        except SubscriptionPlan.DoesNotExist:
            return False, "Subscription plan not found"
        except Exception as e:
            logger.error(
                f"Failed to change subscription for user {user.user_id}: {e!s}"
            )
            return False, f"Failed to change subscription: {e!s}"

    @classmethod
    def get_available_plans(cls) -> list:
        """Get all available subscription plans ordered by price."""
        try:
            plans = SubscriptionPlan.objects.filter(is_active=1, is_deleted=0).order_by(
                "monthly_price"
            )

            return [
                {
                    "plan_id": plan.subscription_plan_id,
                    "name": plan.name,
                    "description": plan.description,
                    "monthly_price": float(plan.monthly_price)
                    if plan.monthly_price
                    else 0,
                    "yearly_price": float(plan.yearly_price)
                    if plan.yearly_price
                    else 0,
                    "feature_details": plan.feature_details,
                }
                for plan in plans
            ]

        except Exception as e:
            logger.error(f"Error getting available plans: {e!s}")
            return []

    @classmethod
    def is_plan_upgrade(
        cls, user: User, new_plan_id: int
    ) -> tuple[bool, dict[str, Any]]:
        """Check if new plan is an upgrade, downgrade, or same level."""
        try:
            current_features = cls.get_subscription_features(user)
            new_plan = SubscriptionPlan.objects.get(
                subscription_plan_id=new_plan_id, is_active=1, is_deleted=0
            )

            current_price = current_features.get("monthly_price", 0)
            new_price = float(new_plan.monthly_price) if new_plan.monthly_price else 0

            if new_price > current_price:
                change_type = "upgrade"
            elif new_price < current_price:
                change_type = "downgrade"
            else:
                change_type = "same_level"

            return True, {
                "change_type": change_type,
                "current_plan": current_features.get("plan_name"),
                "new_plan": new_plan.name,
                "current_price": current_price,
                "new_price": new_price,
                "price_difference": new_price - current_price,
            }

        except SubscriptionPlan.DoesNotExist:
            return False, {"error": "New plan not found"}
        except Exception as e:
            logger.error(f"Error checking plan upgrade for user {user.user_id}: {e!s}")
            return False, {"error": str(e)}

    @classmethod
    def get_or_create_subscription(cls, user: User) -> Subscription:
        """Get or create subscription for user - alias for get_user_subscription."""
        return cls.get_user_subscription(user)

    @classmethod
    def extend_subscription(cls, user: User, days: int) -> tuple[bool, str]:
        """Extend user's current subscription by specified days."""
        try:
            subscription = cls.get_user_subscription(user)

            # Extend the end date
            subscription.end_date = subscription.end_date + timedelta(days=days)
            subscription.updated_by = user.user_id if hasattr(user, "user_id") else 1
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.info(f"Extended subscription for user {user.user_id} by {days} days")
            return (
                True,
                f"Subscription extended by {days} days until {subscription.end_date}",
            )

        except Exception as e:
            logger.error(
                f"Failed to extend subscription for user {user.user_id}: {e!s}"
            )
            return False, f"Failed to extend subscription: {e!s}"

    @classmethod
    def cancel_subscription(cls, user: User) -> tuple[bool, str]:
        """Cancel user's subscription (mark as inactive)."""
        try:
            subscription = cls.get_user_subscription(user)

            # Mark subscription as cancelled
            subscription.status = SubscriptionStatus.CANCELLED.value
            subscription.auto_renew = 0
            subscription.updated_by = user.user_id if hasattr(user, "user_id") else 1
            subscription.updated_at = timezone.now()
            subscription.save()

            logger.info(f"Cancelled subscription for user {user.user_id}")
            return True, "Subscription cancelled successfully"

        except Exception as e:
            logger.error(
                f"Failed to cancel subscription for user {user.user_id}: {e!s}"
            )
            return False, f"Failed to cancel subscription: {e!s}"

    @classmethod
    def renew_subscription(cls, subscription_id: int) -> dict[str, Any]:
        """
        Renew an expiring subscription.

        Extends the subscription end_date by the appropriate billing cycle
        and creates a payment record via PaymentService.

        Args:
            subscription_id: ID of the subscription to renew

        Returns:
            Dict with success status and details
        """
        try:
            subscription = Subscription.objects.select_related(
                "subscription_plan", "user"
            ).get(
                subscription_id=subscription_id,
                is_deleted=0,
            )

            if not subscription.auto_renew:
                return {
                    "success": False,
                    "message": "Auto-renew is disabled for this subscription.",
                }

            plan = subscription.subscription_plan
            if not plan:
                return {
                    "success": False,
                    "message": "No plan associated with subscription.",
                }

            # Determine billing period and amount
            if subscription.billing_frequency == "Yearly" and plan.yearly_price:
                days = 365
                amount = plan.yearly_price
            else:
                days = 30
                amount = plan.monthly_price

            # Extend subscription
            subscription.end_date = subscription.end_date + timedelta(days=days)
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.is_active = 1
            subscription.updated_at = timezone.now()
            subscription.save()

            # Create renewal payment record
            from myapp.models import Payment
            from myapp.models.choices import PaymentStatus

            Payment.objects.create(
                subscription=subscription,
                amount=amount,
                payment_date=timezone.now().date(),
                payment_method="auto_renewal",
                reference_number=f"renewal_{subscription_id}_{timezone.now().strftime('%Y%m%d')}",
                status=PaymentStatus.COMPLETED.value,
                payment_response="Auto-renewal payment",
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=subscription.user_id or 0,
            )

            logger.info(
                f"Subscription {subscription_id} renewed for {days} days, amount={amount}"
            )
            return {
                "success": True,
                "subscription_id": subscription_id,
                "new_end_date": str(subscription.end_date),
                "amount": float(amount),
            }

        except Subscription.DoesNotExist:
            return {"success": False, "message": "Subscription not found."}
        except Exception as e:
            logger.error(f"Error renewing subscription {subscription_id}: {e}")
            return {"success": False, "message": str(e)}

    @classmethod
    def get_subscription_stats(cls, user: User) -> dict[str, Any]:
        """Get comprehensive subscription statistics."""
        try:
            features = cls.get_subscription_features(user)
            api_check = cls.get_api_limit(user)
            operation_check = cls.check_operation_limit(user)

            return {
                "subscription": features,
                "api_limits": api_check if len(api_check) > 1 else {},
                "operation_limits": operation_check if len(operation_check) > 1 else {},
                "features_available": {
                    "automation": cls.can_use_automation(user)[0],
                },
            }

        except Exception as e:
            logger.error(
                f"Error getting subscription stats for user {user.user_id}: {e!s}"
            )
            return {"error": str(e)}
