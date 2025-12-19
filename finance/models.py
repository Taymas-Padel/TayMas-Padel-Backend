from django.db import models
from django.contrib.auth import get_user_model
# from bookings.models import Booking (удалим этот импорт, используем строку, чтобы избежать кругового импорта)

User = get_user_model()

class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Оплата бронирования'
        REFUND = 'REFUND', 'Возврат средств'
        SALARY = 'SALARY', 'Выплата зарплаты'
        OTHER = 'OTHER', 'Прочее'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', verbose_name="Пользователь")
    
    # Используем строковую ссылку 'bookings.Booking', чтобы не было ошибки Circular Import
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name="Связанная бронь")
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ИТОГО")
    
    # --- НОВЫЕ ПОЛЯ ДЛЯ ДЕТАЛИЗАЦИИ ---
    amount_court = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="За корт")
    amount_coach = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="За тренера")
    amount_services = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="За инвентарь")
    # ----------------------------------

    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, default=TransactionType.PAYMENT, verbose_name="Тип операции")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время")
    description = models.TextField(blank=True, verbose_name="Описание (для людей)")

    def __str__(self):
        return f"{self.amount} ₸ | {self.user.username}"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Финансы (Транзакции)"
        ordering = ['-created_at']