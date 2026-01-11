from django.db import models
from django.contrib.auth import get_user_model
from courts.models import Court
from django.utils.translation import gettext_lazy as _
from inventory.models import Service

User = get_user_model()

class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', _('Подтверждено')
        PENDING = 'PENDING', _('Ожидает оплаты')
        CANCELED = 'CANCELED', _('Отменено')
        COMPLETED = 'COMPLETED', _('Завершено')

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='bookings',
        verbose_name=_("Клиент")
    )
    # 🔥 ДОБАВЛЯЕМ ВОТ ЭТО ПОЛЕ
    participants = models.ManyToManyField(
        User,
        related_name='participated_bookings',
        blank=True,
        verbose_name=_("Участники (Друзья)")
    )
    # ---------------------------
    
    # --- НОВОЕ ПОЛЕ: ТРЕНЕР ---
    coach = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # Если тренер уволится, бронь останется (просто без тренера)
        null=True,
        blank=True,
        related_name='coach_bookings',
        verbose_name=_("Тренер")
    )
    # --------------------------
    price = models.DecimalField(
            max_digits=10, 
            decimal_places=2, 
            default=0.00,
            verbose_name="Итоговая цена"
        )
    court = models.ForeignKey(
        Court, 
        on_delete=models.CASCADE, 
        related_name='bookings',
        verbose_name=_("Корт")
    )

    start_time = models.DateTimeField(verbose_name=_("Начало аренды"))
    end_time = models.DateTimeField(verbose_name=_("Конец аренды"))

    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        verbose_name=_("Статус")
    )
    is_paid = models.BooleanField(
        default=False, 
        verbose_name=_("Оплачено")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Бронирование")
        verbose_name_plural = _("Бронирования")
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.court.name} | {self.start_time.strftime('%d.%m %H:%M')} | {self.user.username}"

    @property
    def duration_hours(self):
        diff = self.end_time - self.start_time
        return diff.total_seconds() / 3600
    
class BookingService(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='services', verbose_name="Бронь")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="Услуга")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент покупки")

    def __str__(self):
        return f"{self.service.name} x {self.quantity}"