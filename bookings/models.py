from django.db import models
from django.conf import settings
from courts.models import Court
from django.utils.translation import gettext_lazy as _

class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Ожидает подтверждения')
        CONFIRMED = 'CONFIRMED', _('Подтверждено')
        CANCELED = 'CANCELED', _('Отменено')
        COMPLETED = 'COMPLETED', _('Завершено')

    # Связи
    court = models.ForeignKey(
        Court, 
        on_delete=models.CASCADE, 
        related_name='bookings',
        verbose_name=_("Корт")
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='bookings',
        verbose_name=_("Клиент")
    )
    # Опционально: Тренер
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coach_bookings',
        limit_choices_to={'role__in': ['COACH_PADEL', 'COACH_FITNESS']},
        verbose_name=_("Тренер")
    )

    # Время
    start_time = models.DateTimeField(verbose_name=_("Начало"))
    end_time = models.DateTimeField(verbose_name=_("Конец"))

    # Финансы
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name=_("Итоговая стоимость")
    )
    is_paid = models.BooleanField(default=False, verbose_name=_("Оплачено"))
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.CONFIRMED,
        verbose_name=_("Статус")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Бронирование")
        verbose_name_plural = _("Бронирования")
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.court.name} | {self.start_time.strftime('%d.%m %H:%M')} | {self.client}"

    @property
    def duration_minutes(self):
        """Считает длительность в минутах"""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)