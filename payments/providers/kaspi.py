"""
Kaspi.kz платёжный провайдер.
Скелет — реализуйте когда получите API-ключи от Kaspi Business.
Документация: https://kaspi.kz/business/api (уточните у менеджера)

Для активации:
  1. Заполните KASPI_MERCHANT_ID, KASPI_SECRET_KEY в .env
  2. Задайте PAYMENT_PROVIDER = 'kaspi' в settings.py
"""
import hashlib
import hmac
import logging
import requests
from decimal import Decimal
from typing import Optional

from django.conf import settings

from .base import BasePaymentProvider, PaymentResult, PaymentStatus

logger = logging.getLogger(__name__)


class KaspiPaymentProvider(BasePaymentProvider):
    """
    Kaspi QR / Kaspi Pay.

    Типичный флоу:
    1. initiate() → получаем QR-ссылку (qr_url) → показываем клиенту
    2. Клиент сканирует QR и платит в приложении Kaspi
    3. Kaspi шлёт webhook на /api/payments/webhook/kaspi/
    4. webhook view вызывает PaymentService.handle_webhook()
    5. PaymentSession → PAID → Booking/Lobby обновляется
    """

    BASE_URL = "https://pay.kaspi.kz/api/v1"   # TODO: уточнить у Kaspi

    def __init__(self):
        self.merchant_id: str = getattr(settings, 'KASPI_MERCHANT_ID', '')
        self.secret_key: str = getattr(settings, 'KASPI_SECRET_KEY', '')
        if not self.merchant_id or not self.secret_key:
            logger.warning("KASPI_MERCHANT_ID / KASPI_SECRET_KEY не заданы в settings!")

    def _sign(self, data: str) -> str:
        """HMAC-SHA256 подпись запроса."""
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()

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
        # TODO: реализовать согласно документации Kaspi
        # Примерная структура запроса:
        payload = {
            "merchant_id": self.merchant_id,
            "order_id": order_id,
            "amount": int(amount * 100),  # в тиынах
            "currency": currency,
            "description": description,
            "return_url": return_url or "",
            "phone": user_phone or "",
        }
        # payload["sign"] = self._sign(f"{order_id}{amount}{self.merchant_id}")
        # try:
        #     resp = requests.post(f"{self.BASE_URL}/create", json=payload, timeout=10)
        #     data = resp.json()
        #     return PaymentResult(
        #         success=data.get("status") == "ok",
        #         provider_transaction_id=data.get("transaction_id"),
        #         payment_url=data.get("qr_url"),
        #         raw_response=data,
        #     )
        # except requests.RequestException as e:
        #     return PaymentResult(success=False, error=str(e))
        raise NotImplementedError(
            "Kaspi провайдер не реализован. "
            "Используйте PAYMENT_PROVIDER='stub' для разработки."
        )

    def check_status(self, provider_transaction_id: str) -> PaymentStatus:
        raise NotImplementedError("Kaspi check_status не реализован.")

    def refund(self, provider_transaction_id: str, amount: Decimal) -> PaymentResult:
        raise NotImplementedError("Kaspi refund не реализован.")
