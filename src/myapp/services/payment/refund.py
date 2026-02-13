import logging
from decimal import Decimal
from typing import Any

from django.utils import timezone

from myapp.models import Payment
from myapp.models.choices import PaymentStatus
from myapp.payment_strategies.factory import get_payment_manager

logger = logging.getLogger(__name__)


class RefundService:
    """
    Service to handle refund requests and processing.
    """

    @staticmethod
    def process_refund(
        payment_id: int,
        amount: Decimal | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Process a refund for a specific payment.

        Args:
            payment_id: ID of the Payment record.
            amount: Amount to refund (None for full refund).
            reason: Reason for the refund.

        Returns:
            Dict containing the result of the refund operation.
        """
        try:
            payment = Payment.objects.get(payment_id=payment_id)

            if payment.status != PaymentStatus.COMPLETED.value:
                return {
                    "success": False,
                    "message": "Payment is not in completed status.",
                }

            manager = get_payment_manager()
            result = manager.refund_payment(
                transaction_id=payment.reference_number,
                amount=amount,
                reason=reason,
                provider=payment.payment_method,
            )

            if result.success:
                # Update payment status
                if not amount or amount == payment.amount:
                    payment.status = PaymentStatus.REFUNDED.value
                else:
                    payment.status = PaymentStatus.PARTIALLY_REFUNDED.value
                payment.updated_at = timezone.now()
                payment.save()

                logger.info(
                    f"Refund processed for payment {payment_id}: {result.transaction_id}"
                )
                return {"success": True, "refund_id": result.transaction_id}
            else:
                logger.error(
                    f"Refund failed for payment {payment_id}: {result.message}"
                )
                return {"success": False, "message": result.message}

        except Payment.DoesNotExist:
            return {"success": False, "message": "Payment not found."}
        except Exception as e:
            logger.exception(f"Error processing refund for payment {payment_id}")
            return {"success": False, "message": str(e)}
