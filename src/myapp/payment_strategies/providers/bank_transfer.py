# myapp/payment_strategies/providers/bank_transfer.py
"""
Bank transfer payment provider implementation.

This module implements a manual/offline payment provider for bank transfers,
wire transfers, and other offline payment methods.

This is useful for:
- Enterprise customers paying by invoice
- International wire transfers
- ACH payments
- Any manual payment reconciliation process
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.utils import timezone as django_timezone

from myapp.payment_strategies.base import (
    PaymentError,
    PaymentProvider,
    PaymentResult,
    PaymentStatus,
    RefundResult,
    SubscriptionResult,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


class BankTransferPaymentProvider(PaymentProvider):
    """
    Manual bank transfer payment provider.

    This provider handles offline payments that require manual reconciliation.
    Payments are marked as pending until an admin approves them.

    Configuration:
        - bank_name: Name of the bank for transfers
        - account_name: Account holder name
        - account_number: Bank account number
        - routing_number: Routing number (for US)
        - swift_code: SWIFT/BIC code (for international)
        - iban: IBAN (for European transfers)
        - instructions: Additional payment instructions
    """

    provider_name = "bank_transfer"
    display_name = "Bank Transfer"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

        # Get configuration from Django settings if not provided
        if not self.config:
            self.config = {
                "bank_name": getattr(
                    settings, "BANK_TRANSFER_BANK_NAME", "Example Bank"
                ),
                "account_name": getattr(
                    settings, "BANK_TRANSFER_ACCOUNT_NAME", "Company Name"
                ),
                "account_number": getattr(settings, "BANK_TRANSFER_ACCOUNT_NUMBER", ""),
                "routing_number": getattr(settings, "BANK_TRANSFER_ROUTING_NUMBER", ""),
                "swift_code": getattr(settings, "BANK_TRANSFER_SWIFT_CODE", ""),
                "iban": getattr(settings, "BANK_TRANSFER_IBAN", ""),
                "instructions": getattr(settings, "BANK_TRANSFER_INSTRUCTIONS", ""),
            }

    def is_configured(self) -> bool:
        """
        Bank transfer is always available as a fallback payment method.
        Returns True if at least bank name is configured.
        """
        return bool(self.config.get("bank_name"))

    def create_payment_intent(
        self,
        amount: Decimal | float,
        currency: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        customer_email: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Create a manual payment record for bank transfer.

        Returns payment instructions that the customer should follow.

        Args:
            amount: Payment amount
            currency: Currency code
            description: Payment description
            metadata: Additional metadata
            customer_email: Customer email
            **kwargs: Additional parameters

        Returns:
            PaymentResult with transaction details and payment instructions
        """
        try:
            # Generate a unique transaction ID
            transaction_id = f"bt_{uuid.uuid4().hex[:24].upper()}"

            # Build payment instructions
            instructions = self._build_payment_instructions(
                amount=amount,
                currency=currency,
                description=description,
                transaction_id=transaction_id,
                customer_email=customer_email,
            )

            return PaymentResult(
                success=True,
                transaction_id=transaction_id,
                provider_transaction_id=transaction_id,
                amount=Decimal(str(amount)),
                currency=currency.upper(),
                status=PaymentStatus.PENDING,
                message="Bank transfer payment initiated",
                provider=self.provider_name,
                provider_data={
                    "instructions": instructions,
                    "requires_manual_approval": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Bank transfer payment creation failed: {e}")
            return PaymentResult(
                success=False,
                message="Failed to create payment record",
                error=PaymentError(
                    message=str(e),
                    code="PAYMENT_CREATION_FAILED",
                    provider=self.provider_name,
                ),
            )

    def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str | None = None,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        For bank transfers, payment confirmation is done manually by admin.

        This method is not applicable and returns an error.

        Returns:
            PaymentResult indicating manual confirmation is required
        """
        return PaymentResult(
            success=False,
            message="Bank transfer payments require manual confirmation",
            error=PaymentError(
                message="Use admin API to confirm bank transfer payments",
                code="MANUAL_CONFIRMATION_REQUIRED",
                provider=self.provider_name,
            ),
        )

    def get_payment_status(
        self,
        transaction_id: str,
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Get the status of a bank transfer payment.

        Since this provider doesn't store state, this method
        looks up the payment from the database.

        Args:
            transaction_id: Transaction ID
            **kwargs: Additional parameters

        Returns:
            PaymentResult with current status
        """
        try:
            from myapp.models import Payment

            payment = Payment.objects.filter(
                reference_number=transaction_id, is_deleted=0
            ).first()

            if not payment:
                return PaymentResult(
                    success=False,
                    message="Payment not found",
                    error=PaymentError(
                        message=f"Payment {transaction_id} not found",
                        code="PAYMENT_NOT_FOUND",
                        provider=self.provider_name,
                    ),
                )

            status_map = {
                PaymentStatus.COMPLETED.value: PaymentStatus.COMPLETED,
                PaymentStatus.PENDING.value: PaymentStatus.PENDING,
                PaymentStatus.FAILED.value: PaymentStatus.FAILED,
                PaymentStatus.CANCELLED.value: PaymentStatus.CANCELLED,
                PaymentStatus.REFUNDED.value: PaymentStatus.REFUNDED,
            }

            return PaymentResult(
                success=True,
                transaction_id=transaction_id,
                provider_transaction_id=payment.payment_id,
                amount=Decimal(str(payment.amount)) if payment.amount else None,
                currency="USD",  # Default for bank transfers
                status=status_map.get(payment.status, PaymentStatus.PENDING),
                message=f"Payment status: {payment.status}",
                provider=self.provider_name,
            )

        except Exception as e:
            logger.error(f"Bank transfer status check failed: {e}")
            return PaymentResult(
                success=False,
                message="Failed to get payment status",
                error=PaymentError(
                    message=str(e),
                    code="STATUS_CHECK_FAILED",
                    provider=self.provider_name,
                ),
            )

    def create_subscription(
        self,
        plan_id: str,
        customer_email: str | None = None,
        metadata: dict[str, Any] | None = None,
        trial_days: int = 0,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Create a subscription for bank transfer payment.

        The subscription is created but marked as pending until
        the first payment is confirmed manually.

        Args:
            plan_id: Internal plan ID
            customer_email: Customer email
            metadata: Additional metadata
            trial_days: Trial period days
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult with subscription details
        """
        try:
            from myapp.models import Subscription, SubscriptionPlan, User

            # Get the internal plan
            plan = SubscriptionPlan.objects.get(
                subscription_plan_id=int(plan_id), is_active=1, is_deleted=0
            )

            # Get user from email
            user = User.objects.get(email=customer_email) if customer_email else None

            # Create pending subscription
            subscription = Subscription.objects.create(
                user=user,
                subscription_plan=plan,
                billing_frequency="Yearly" if plan.yearly_price else "Monthly",
                start_date=django_timezone.now().date(),
                end_date=django_timezone.now().date() + timedelta(days=365),
                auto_renew=1,
                status=PaymentStatus.PENDING.value,
                is_active=0,
                is_deleted=0,
                created_at=django_timezone.now(),
                created_by=user.user_id if user else 1,
            )

            return SubscriptionResult(
                success=True,
                subscription_id=subscription.subscription_id,
                provider_subscription_id=f"bt_sub_{subscription.subscription_id}",
                status=PaymentStatus.PENDING.value,
                plan_id=int(plan_id),
                message="Subscription created pending payment confirmation",
                provider=self.provider_name,
                provider_data={
                    "instructions": self._build_payment_instructions(
                        amount=plan.yearly_price or plan.monthly_price or 0,
                        currency="USD",
                        description=f"Subscription: {plan.name}",
                        customer_email=customer_email,
                    ),
                    "requires_manual_approval": True,
                },
            )

        except Exception as e:
            logger.error(f"Bank transfer subscription creation failed: {e}")
            return SubscriptionResult(
                success=False,
                message="Failed to create subscription",
                error=PaymentError(
                    message=str(e),
                    code="SUBSCRIPTION_CREATION_FAILED",
                    provider=self.provider_name,
                ),
            )

    def cancel_subscription(
        self,
        provider_subscription_id: str,
        cancel_at_period_end: bool = True,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Cancel a bank transfer subscription.

        Args:
            provider_subscription_id: Subscription ID (bt_sub_xxx format)
            cancel_at_period_end: If True, cancel at period end
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult with cancellation details
        """
        try:
            from myapp.models import Subscription

            # Extract numeric subscription ID
            sub_id = provider_subscription_id.replace("bt_sub_", "")
            subscription = Subscription.objects.get(
                subscription_id=int(sub_id), is_deleted=0
            )

            subscription.status = "Cancelled"
            subscription.auto_renew = 0
            subscription.updated_at = django_timezone.now()
            subscription.save()

            return SubscriptionResult(
                success=True,
                subscription_id=subscription.subscription_id,
                provider_subscription_id=provider_subscription_id,
                status="Cancelled",
                message="Bank transfer subscription cancelled",
                provider=self.provider_name,
            )

        except Subscription.DoesNotExist:
            return SubscriptionResult(
                success=False,
                message="Subscription not found",
                error=PaymentError(
                    message=f"Subscription {provider_subscription_id} not found",
                    code="SUBSCRIPTION_NOT_FOUND",
                    provider=self.provider_name,
                ),
            )
        except Exception as e:
            logger.error(f"Bank transfer subscription cancellation failed: {e}")
            return SubscriptionResult(
                success=False,
                message="Failed to cancel subscription",
                error=PaymentError(
                    message=str(e),
                    code="CANCELLATION_FAILED",
                    provider=self.provider_name,
                ),
            )

    def update_subscription(
        self,
        provider_subscription_id: str,
        plan_id: str | None = None,
        quantity: int | None = None,
        **kwargs: Any,
    ) -> SubscriptionResult:
        """
        Update a bank transfer subscription (plan, quantity, etc.).

        Args:
            provider_subscription_id: Subscription ID
            plan_id: New plan ID
            quantity: Not used for bank transfer
            **kwargs: Additional parameters

        Returns:
            SubscriptionResult with updated details
        """
        if not plan_id:
            return SubscriptionResult(
                success=False,
                message="Plan ID is required for subscription updates",
                error=PaymentError(
                    message="Plan changes require manual approval",
                    code="MANUAL_APPROVAL_REQUIRED",
                    provider=self.provider_name,
                ),
            )

        try:
            from myapp.models import Subscription, SubscriptionPlan

            # Extract numeric subscription ID
            sub_id = provider_subscription_id.replace("bt_sub_", "")
            subscription = Subscription.objects.get(
                subscription_id=int(sub_id), is_deleted=0
            )

            # Get new plan
            new_plan = SubscriptionPlan.objects.get(
                subscription_plan_id=int(plan_id), is_active=1, is_deleted=0
            )

            # Update subscription
            subscription.subscription_plan = new_plan
            subscription.updated_at = django_timezone.now()
            subscription.save()

            return SubscriptionResult(
                success=True,
                subscription_id=subscription.subscription_id,
                provider_subscription_id=provider_subscription_id,
                status=subscription.status,
                plan_id=int(plan_id),
                message="Subscription updated - pending payment confirmation",
                provider=self.provider_name,
                provider_data={
                    "requires_payment": True,
                    "new_plan": new_plan.name,
                },
            )

        except Subscription.DoesNotExist:
            return SubscriptionResult(
                success=False,
                message="Subscription not found",
                error=PaymentError(
                    message=f"Subscription {provider_subscription_id} not found",
                    code="SUBSCRIPTION_NOT_FOUND",
                    provider=self.provider_name,
                ),
            )
        except Exception as e:
            logger.error(f"Bank transfer subscription update failed: {e}")
            return SubscriptionResult(
                success=False,
                message="Failed to update subscription",
                error=PaymentError(
                    message=str(e),
                    code="UPDATE_FAILED",
                    provider=self.provider_name,
                ),
            )

    def refund_payment(
        self,
        transaction_id: str,
        amount: Decimal | float | None = None,
        reason: str = "",
        **kwargs: Any,
    ) -> RefundResult:
        """
        Process a refund for a bank transfer payment.

        Bank transfer refunds are manual processes. This method
        creates a refund record that requires admin processing.

        Args:
            transaction_id: Transaction ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            **kwargs: Additional parameters

        Returns:
            RefundResult with refund details
        """
        try:
            from myapp.models import Payment

            payment = Payment.objects.filter(
                reference_number=transaction_id, is_deleted=0
            ).first()

            if not payment:
                return RefundResult(
                    success=False,
                    message="Payment not found",
                    error=PaymentError(
                        message=f"Payment {transaction_id} not found",
                        code="PAYMENT_NOT_FOUND",
                        provider=self.provider_name,
                    ),
                )

            # Generate refund ID
            refund_id = f"bt_ref_{uuid.uuid4().hex[:20].upper()}"

            # Update payment status to refunded
            payment.status = PaymentStatus.REFUNDED.value
            payment.updated_at = django_timezone.now()
            payment.save()

            refund_amount = (
                Decimal(str(amount)) if amount else (payment.amount or Decimal("0"))
            )

            return RefundResult(
                success=True,
                refund_id=refund_id,
                provider_refund_id=refund_id,
                amount=refund_amount,
                currency="USD",
                status=PaymentStatus.COMPLETED.value,
                reason=reason,
                message="Refund processed - manual transfer required",
                provider=self.provider_name,
            )

        except Exception as e:
            logger.error(f"Bank transfer refund failed: {e}")
            return RefundResult(
                success=False,
                message="Failed to process refund",
                error=PaymentError(
                    message=str(e),
                    code="REFUND_FAILED",
                    provider=self.provider_name,
                ),
            )

    def parse_webhook(
        self,
        payload: bytes | str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> WebhookEvent:
        """
        Bank transfer doesn't support webhooks in the traditional sense.

        This method parses manual payment confirmation events sent by
        the admin system.

        Args:
            payload: Event payload
            headers: Not used
            **kwargs: Additional parameters

        Returns:
            WebhookEvent with parsed data
        """
        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")

            data = json.loads(payload) if payload else {}

            return WebhookEvent(
                event_id=data.get("event_id", f"manual_{uuid.uuid4().hex}"),
                event_type=data.get("event_type", "manual_payment.verified"),
                provider=self.provider_name,
                payload=data,
                received_at=datetime.now(timezone.utc),
            )

        except json.JSONDecodeError as e:
            raise PaymentError(
                message="Invalid JSON payload",
                code="INVALID_PAYLOAD",
                provider=self.provider_name,
                details={"original_error": str(e)},
            ) from e

    def _build_payment_instructions(
        self,
        amount: Decimal | float,
        currency: str,
        description: str | None = None,
        transaction_id: str = "",
        customer_email: str = "",
    ) -> dict[str, Any]:
        """Build payment instructions for bank transfer."""
        instructions = {
            "provider": self.provider_name,
            "bank_name": self.config.get("bank_name", ""),
            "account_name": self.config.get("account_name", ""),
            "account_number": self.config.get("account_number", ""),
            "routing_number": self.config.get("routing_number", ""),
            "swift_code": self.config.get("swift_code", ""),
            "iban": self.config.get("iban", ""),
            "amount": str(amount),
            "currency": currency.upper(),
            "reference": transaction_id or "Your unique reference",
        }

        # Add any custom instructions
        custom_instructions = self.config.get("instructions", "")
        if custom_instructions:
            instructions["custom_instructions"] = custom_instructions

        # Build formatted instruction text
        instruction_lines = [
            f"Please transfer {instructions['amount']} {instructions['currency']}",
            "to the following bank account:",
            "",
            f"Bank: {instructions['bank_name']}",
            f"Account Name: {instructions['account_name']}",
        ]

        if instructions["account_number"]:
            instruction_lines.append(
                f"Account Number: {instructions['account_number']}"
            )

        if instructions["routing_number"]:
            instruction_lines.append(
                f"Routing Number: {instructions['routing_number']}"
            )

        if instructions["swift_code"]:
            instruction_lines.append(f"SWIFT Code: {instructions['swift_code']}")

        if instructions["iban"]:
            instruction_lines.append(f"IBAN: {instructions['iban']}")

        instruction_lines.extend(
            [
                "",
                f"Reference: {instructions['reference']}",
            ]
        )

        if custom_instructions:
            instruction_lines.extend(
                ["", "Additional Instructions:", custom_instructions]
            )

        instructions["formatted"] = "\n".join(instruction_lines)

        return instructions

    def handle_manual_payment_confirmation(
        self,
        transaction_id: str,
        confirmed_by: int,
        notes: str = "",
        **kwargs: Any,
    ) -> PaymentResult:
        """
        Handle manual payment confirmation from admin.

        This is a provider-specific method that allows admins
        to confirm bank transfer payments.

        Args:
            transaction_id: Transaction ID to confirm
            confirmed_by: Admin user ID
            notes: Confirmation notes
            **kwargs: Additional parameters

        Returns:
            PaymentResult with confirmation status
        """
        try:
            from myapp.models import Payment

            payment = Payment.objects.filter(
                reference_number=transaction_id, is_deleted=0
            ).first()

            if not payment:
                return PaymentResult(
                    success=False,
                    message="Payment not found",
                    error=PaymentError(
                        message=f"Payment {transaction_id} not found",
                        code="PAYMENT_NOT_FOUND",
                        provider=self.provider_name,
                    ),
                )

            if payment.status == PaymentStatus.COMPLETED.value:
                return PaymentResult(
                    success=True,
                    transaction_id=transaction_id,
                    message="Payment already confirmed",
                    provider=self.provider_name,
                )

            # Confirm the payment
            payment.status = PaymentStatus.COMPLETED.value
            payment.payment_response = (
                f"Manually confirmed by admin {confirmed_by}. {notes}"
            )
            payment.updated_at = django_timezone.now()
            payment.updated_by = confirmed_by
            payment.save()

            return PaymentResult(
                success=True,
                transaction_id=transaction_id,
                provider_transaction_id=str(payment.payment_id),
                amount=Decimal(str(payment.amount)) if payment.amount else None,
                currency="USD",
                status=PaymentStatus.COMPLETED,
                message="Bank transfer payment confirmed",
                provider=self.provider_name,
            )

        except Exception as e:
            logger.error(f"Manual payment confirmation failed: {e}")
            return PaymentResult(
                success=False,
                message="Failed to confirm payment",
                error=PaymentError(
                    message=str(e),
                    code="CONFIRMATION_FAILED",
                    provider=self.provider_name,
                ),
            )
