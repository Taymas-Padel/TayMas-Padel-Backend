import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class PaymentSession(models.Model):
    """
    Одна попытка оплаты.
    Создаётся при вызове PaymentService.charge().
    Хранит состояние платежа, привязку к заказу и ответ провайдера.

    При переходе на реального провайдера:
    - status меняется webhook'ом или polling'ом
    - provider_transaction_id сохраняется для сверки
    """

    class Status(models.TextChoices):
        PENDING  = 'PENDING',  _('Ожидает оплаты')
        SUCCESS  = 'SUCCESS',  _('Оплачено')
        FAILED   = 'FAILED',   _('Ошибка')
        REFUNDED = 'REFUNDED', _('Возврат')
        CANCELED = 'CANCELED', _('Отменено')

    class Provider(models.TextChoices):
        STUB  = 'stub',  'Stub (разработка)'
        KASPI = 'kaspi', 'Kaspi QR'
        CARD  = 'card',  'Банковская карта'
        CASH  = 'cash',  'Наличные (касса)'

    # Уникальный ID сессии — передаётся провайдеру как order_id
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='payment_sessions', verbose_name=_("Пользователь")
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Сумма"))
    currency = models.CharField(max_length=3, default='KZT')
    description = models.TextField(blank=True, verbose_name=_("Описание"))

    provider = models.CharField(
        max_length=20, choices=Provider.choices, default=Provider.STUB,
        verbose_name=_("Провайдер")
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING,
        verbose_name=_("Статус")
    )

    # ID транзакции в системе провайдера (после оплаты)
    provider_transaction_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("ID транзакции провайдера")
    )
    # URL для QR / оплаты (если провайдер требует редиректа)
    payment_url = models.URLField(blank=True, verbose_name=_("URL оплаты"))

    # Привязки к объектам (одна из них заполнена)
    booking = models.ForeignKey(
        'bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_sessions', verbose_name=_("Бронь")
    )
    user_membership = models.ForeignKey(
        'memberships.UserMembership', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_sessions', verbose_name=_("Абонемент")
    )
    lobby = models.ForeignKey(
        'lobby.Lobby', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_sessions', verbose_name=_("Лобби")
    )

    # Сырой ответ провайдера — для отладки и сверки
    raw_response = models.JSONField(default=dict, blank=True, verbose_name=_("Ответ провайдера"))

    # Финансовая запись после подтверждения
    transaction = models.OneToOneField(
        'finance.Transaction', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_session', verbose_name=_("Транзакция")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Платёжная сессия")
        verbose_name_plural = _("Платёжные сессии")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.provider.upper()} | {self.amount} ₸ | {self.status} | {self.user}"
