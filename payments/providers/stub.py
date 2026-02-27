"""
Stub-провайдер для разработки и тестирования.
Мгновенно подтверждает любой платёж без реального списания.
Активируется при PAYMENT_PROVIDER = 'stub' (по умолчанию при DEBUG=True).
"""
import uuid
import logging
from decimal import Decimal
from typing import Optional

from .base import BasePaymentProvider, PaymentResult, PaymentStatus

logger = logging.getLogger(__name__)


class StubPaymentProvider(BasePaymentProvider):
    """
    ⚠️ ТОЛЬКО ДЛЯ РАЗРАБОТКИ — никаких реальных денег.
    Каждый вызов initiate() возвращает успех немедленно.
    Замените на реального провайдера в продакшне.
    """

    def initiate(
        self,
        amount: Decimal,
        currency: str = 'KZT',
        order_id: str = '',
        description: str = '',
        user_phone: Optional[str] = None,
        user_email: Optional[str] = None,
        return_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> PaymentResult:
        fake_id = f"STUB-{uuid.uuid4().hex[:12].upper()}"
        logger.info(
            f"[STUB PAYMENT] ✅ Успешно: {amount} {currency} | "
            f"order={order_id} | tx={fake_id} | '{description}'"
        )
        return PaymentResult(
            success=True,
            provider_transaction_id=fake_id,
            payment_url=None,   # нет редиректа — оплата мгновенная
            raw_response={
                "provider": "stub",
                "amount": str(amount),
                "currency": currency,
                "order_id": order_id,
                "transaction_id": fake_id,
            },
        )

    def check_status(self, provider_transaction_id: str) -> PaymentStatus:
        return PaymentStatus(
            provider_transaction_id=provider_transaction_id,
            paid=True,
            amount=Decimal('0'),
            raw_response={"provider": "stub", "status": "paid"},
        )

    def refund(self, provider_transaction_id: str, amount: Decimal) -> PaymentResult:
        logger.info(f"[STUB REFUND] {amount} KZT для tx={provider_transaction_id}")
        return PaymentResult(
            success=True,
            provider_transaction_id=f"REFUND-{provider_transaction_id}",
            raw_response={"provider": "stub", "refunded": str(amount)},
        )
