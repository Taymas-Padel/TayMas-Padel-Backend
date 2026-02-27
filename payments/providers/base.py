"""
Базовый интерфейс платёжного провайдера.
Все провайдеры должны наследоваться отсюда и реализовывать методы.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class PaymentResult:
    """Результат инициализации платежа."""
    success: bool
    # В stub-режиме: None. В реальном: внешний ID транзакции провайдера
    provider_transaction_id: Optional[str] = None
    # URL для редиректа клиента (Kaspi, CloudPayments и т.д.)
    # В stub-режиме: None (оплата прошла сразу)
    payment_url: Optional[str] = None
    # Сообщение об ошибке (если success=False)
    error: Optional[str] = None
    # Сырой ответ провайдера (для логирования)
    raw_response: Optional[dict] = field(default_factory=dict)


@dataclass
class PaymentStatus:
    """Статус платежа при проверке через провайдера."""
    provider_transaction_id: str
    paid: bool
    amount: Decimal
    raw_response: Optional[dict] = field(default_factory=dict)


class BasePaymentProvider(ABC):
    """
    Абстрактный базовый класс платёжного провайдера.

    Для подключения нового провайдера:
    1. Создай файл payments/providers/my_provider.py
    2. Наследуй BasePaymentProvider
    3. Реализуй все @abstractmethod методы
    4. Задай PAYMENT_PROVIDER = 'my_provider' в settings.py
    """

    @abstractmethod
    def initiate(
        self,
        amount: Decimal,
        currency: str,
        order_id: str,
        description: str,
        user_phone: Optional[str] = None,
        user_email: Optional[str] = None,
        return_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> PaymentResult:
        """
        Инициировать платёж.

        :param amount:      Сумма в тенге (или другой валюте)
        :param currency:    ISO-код валюты, напр. 'KZT'
        :param order_id:    Уникальный ID в нашей системе (PaymentSession.id или UUID)
        :param description: Описание платежа (видит клиент)
        :param user_phone:  Телефон клиента (опционально, для Kaspi)
        :param user_email:  Email (для чека)
        :param return_url:  URL редиректа после оплаты
        :param metadata:    Доп. данные (booking_id, lobby_id и т.д.)
        :return:            PaymentResult
        """

    @abstractmethod
    def check_status(self, provider_transaction_id: str) -> PaymentStatus:
        """
        Проверить статус платежа у провайдера.
        Используется когда провайдер не присылает webhook.
        """

    @abstractmethod
    def refund(self, provider_transaction_id: str, amount: Decimal) -> PaymentResult:
        """
        Вернуть средства клиенту (частично или полностью).
        """
