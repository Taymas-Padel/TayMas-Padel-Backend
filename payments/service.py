"""
PaymentService — единственная точка входа для оплаты.

Использование из любого view:

    from payments.service import PaymentService
    from decimal import Decimal

    result = PaymentService.charge(
        user=request.user,
        amount=Decimal('2500.00'),
        description='Бронь корта #12',
        payment_method='KASPI',
        booking=booking_instance,     # опционально
        lobby=lobby_instance,         # опционально
        user_membership=mem_instance, # опционально
    )

    if result.success:
        # платёж подтверждён (stub) или ссылка для QR (реальный)
        if result.payment_url:
            # перенаправить клиента на result.payment_url
            pass
    else:
        # result.error — текст ошибки

Для переключения провайдера — меняем только PAYMENT_PROVIDER в settings.py.
Вся бизнес-логика views остаётся без изменений.
"""
import logging
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import PaymentSession
from .providers.base import BasePaymentProvider, PaymentResult

logger = logging.getLogger(__name__)


def _get_provider() -> BasePaymentProvider:
    """
    Выбирает провайдер по настройке PAYMENT_PROVIDER в settings.py.
    По умолчанию — stub (для разработки).

    Чтобы подключить Kaspi:
      PAYMENT_PROVIDER = 'kaspi'
      KASPI_MERCHANT_ID = 'ваш_ID'
      KASPI_SECRET_KEY  = 'ваш_ключ'
    """
    provider_name = getattr(settings, 'PAYMENT_PROVIDER', 'stub').lower()

    if provider_name == 'stub':
        from .providers.stub import StubPaymentProvider
        return StubPaymentProvider()
    elif provider_name == 'kaspi':
        from .providers.kaspi import KaspiPaymentProvider
        return KaspiPaymentProvider()
    else:
        raise ValueError(
            f"Неизвестный PAYMENT_PROVIDER='{provider_name}'. "
            f"Доступные: 'stub', 'kaspi'."
        )


class PaymentService:
    """
    Сервис оплаты. Все методы статические — вызываем без инстанцирования.
    """

    @staticmethod
    def charge(
        user,
        amount: Decimal,
        description: str,
        payment_method: str = 'KASPI',
        # Привязки (заполни нужное):
        booking=None,
        lobby=None,
        user_membership=None,
        # Дополнительно:
        transaction_type: str = 'BOOKING',
        amount_court: Decimal = Decimal('0'),
        amount_services: Decimal = Decimal('0'),
        amount_coach: Decimal = Decimal('0'),
        amount_discount: Decimal = Decimal('0'),
        currency: str = 'KZT',
        return_url: Optional[str] = None,
    ) -> PaymentResult:
        """
        Инициировать платёж.

        В stub-режиме: сразу создаёт Transaction и обновляет статусы.
        В реальном режиме: создаёт PaymentSession, возвращает payment_url,
            финальное подтверждение приходит через webhook.

        :return: PaymentResult(success, payment_url, error)
        """
        provider = _get_provider()
        provider_name = getattr(settings, 'PAYMENT_PROVIDER', 'stub').lower()

        # 1. Создаём PaymentSession
        session = PaymentSession.objects.create(
            user=user,
            amount=amount,
            currency=currency,
            description=description,
            provider=provider_name,
            status=PaymentSession.Status.PENDING,
            booking=booking,
            lobby=lobby,
            user_membership=user_membership,
        )

        # 2. Вызываем провайдера
        result = provider.initiate(
            amount=amount,
            currency=currency,
            order_id=str(session.id),
            description=description,
            user_phone=getattr(user, 'phone_number', None),
            return_url=return_url,
            metadata={
                'booking_id': booking.id if booking else None,
                'lobby_id': lobby.id if lobby else None,
                'membership_id': user_membership.id if user_membership else None,
                'user_id': user.id,
            },
        )

        if result.success:
            session.provider_transaction_id = result.provider_transaction_id or ''
            session.payment_url = result.payment_url or ''
            session.raw_response = result.raw_response or {}

            # В stub-режиме (или при мгновенном подтверждении) сразу финализируем
            if not result.payment_url:
                PaymentService._finalize_session(
                    session=session,
                    payment_method=payment_method,
                    transaction_type=transaction_type,
                    amount_court=amount_court,
                    amount_services=amount_services,
                    amount_coach=amount_coach,
                    amount_discount=amount_discount,
                )
            else:
                session.status = PaymentSession.Status.PENDING
                session.save()
        else:
            session.status = PaymentSession.Status.FAILED
            session.raw_response = result.raw_response or {}
            session.save()
            logger.error(f"[PaymentService] Ошибка платежа: {result.error}")

        return result

    @staticmethod
    def _finalize_session(
        session: PaymentSession,
        payment_method: str,
        transaction_type: str,
        amount_court: Decimal,
        amount_services: Decimal,
        amount_coach: Decimal,
        amount_discount: Decimal,
    ):
        """
        Вызывается когда провайдер подтвердил оплату.
        Создаёт finance.Transaction, обновляет PaymentSession.
        Вызывается из:
        - charge() при stub (мгновенно)
        - handle_webhook() при реальном провайдере
        """
        from finance.models import Transaction

        with db_transaction.atomic():
            tx = Transaction.objects.create(
                user=session.user,
                booking=session.booking,
                user_membership=session.user_membership,
                amount=session.amount,
                amount_court=amount_court,
                amount_coach=amount_coach,
                amount_services=amount_services,
                amount_discount=amount_discount,
                transaction_type=transaction_type,
                payment_method=payment_method,
                description=session.description,
            )
            session.transaction = tx
            session.status = PaymentSession.Status.SUCCESS
            session.save(update_fields=['transaction', 'status', 'provider_transaction_id',
                                        'payment_url', 'raw_response', 'updated_at'])

    @staticmethod
    def handle_webhook(provider_name: str, raw_data: dict) -> bool:
        """
        Обработать webhook от провайдера.
        Вызывается из payments/views.py при POST на /api/payments/webhook/<provider>/

        Провайдер прислал подтверждение — находим PaymentSession и финализируем.

        :return: True если успешно обработан
        """
        logger.info(f"[Webhook] {provider_name}: {raw_data}")

        # TODO: для каждого провайдера парсить raw_data по-своему
        # Пример для Kaspi:
        # order_id = raw_data.get('order_id')
        # tx_id = raw_data.get('transaction_id')
        # status = raw_data.get('status')
        # if status != 'paid': return False

        # try:
        #     session = PaymentSession.objects.get(id=order_id, status='PENDING')
        #     session.provider_transaction_id = tx_id
        #     PaymentService._finalize_session(session, payment_method='KASPI', ...)
        #     return True
        # except PaymentSession.DoesNotExist:
        #     return False

        logger.warning(f"[Webhook] handle_webhook не реализован для '{provider_name}'")
        return False

    @staticmethod
    def refund(session_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """
        Вернуть средства по ID платёжной сессии.
        """
        from .models import PaymentSession as PS

        try:
            session = PS.objects.get(id=session_id)
        except PS.DoesNotExist:
            return PaymentResult(success=False, error="PaymentSession не найдена")

        if session.status != PS.Status.SUCCESS:
            return PaymentResult(success=False, error="Платёж не в статусе SUCCESS")

        provider = _get_provider()
        refund_amount = amount or session.amount
        result = provider.refund(session.provider_transaction_id, refund_amount)

        if result.success:
            session.status = PS.Status.REFUNDED
            session.save(update_fields=['status', 'updated_at'])

        return result
