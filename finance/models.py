from django.db import models
from django.conf import settings

class Transaction(models.Model):
    # 1. ТИПЫ ОПЕРАЦИЙ (Чтобы фильтровать в аналитике)
    class TransactionType(models.TextChoices):
        BOOKING_PAYMENT = 'BOOKING', 'Оплата бронирования'
        MEMBERSHIP_PURCHASE = 'MEMBERSHIP', 'Покупка абонемента'
        REFUND = 'REFUND', 'Возврат средств'
        SALARY = 'SALARY', 'Выплата зарплаты'
        OTHER = 'OTHER', 'Прочее'

    # 2. СПОСОБЫ ОПЛАТЫ (Важно для сверки кассы)
    class PaymentMethod(models.TextChoices):
        KASPI = 'KASPI', 'Kaspi / QR'
        CARD = 'CARD', 'Банковская карта'
        CASH = 'CASH', 'Наличные'
        BONUS = 'BONUS', 'Бонусы'
        UNKNOWN = 'UNKNOWN', 'Не указано'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='transactions', 
        verbose_name="Пользователь"
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ИТОГО")

    # --- СВЯЗИ (Заполняется только одно из двух) ---
    # Ссылка на бронь (если это оплата корта)
    booking = models.ForeignKey(
        'bookings.Booking', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions', 
        verbose_name="Связанная бронь"
    )
    
    # Ссылка на абонемент (если это покупка абонемента)
    user_membership = models.ForeignKey(
        'memberships.UserMembership', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions', 
        verbose_name="Купленный абонемент"
    )
    # ---------------------------------------------
    
    # Детализация (для аналитики броней)
    amount_court = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="За корт")
    amount_coach = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="За тренера")
    amount_services = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="За инвентарь")
    amount_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Сумма скидки")
    
    transaction_type = models.CharField(
        max_length=20, 
        choices=TransactionType.choices, 
        default=TransactionType.BOOKING_PAYMENT, 
        verbose_name="Тип операции"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.UNKNOWN,
        verbose_name="Способ оплаты"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.amount} ₸ ({self.user.username})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Финансы (Транзакции)"
        ordering = ['-created_at']