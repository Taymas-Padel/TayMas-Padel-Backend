from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Court(models.Model):
    class CourtType(models.TextChoices):
        INDOOR = 'INDOOR', _('Indoor (Крытый)')
        OUTDOOR = 'OUTDOOR', _('Outdoor (Открытый)')
        PANORAMIC = 'PANORAMIC', _('Panoramic (Панорамный)')
        SQUASH = 'SQUASH', _('Squash')
        PING_PONG = 'PING_PONG', _('Ping-pong (Настольный теннис)')

    class PlayFormat(models.TextChoices):
        TWO_VS_TWO = 'TWO_VS_TWO', _('2x2 (Двое на двое)')
        ONE_VS_ONE = 'ONE_VS_ONE', _('1x1 (Один на один)')

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Название/Номер корта")
    )

    court_type = models.CharField(
        max_length=20,
        choices=CourtType.choices,
        default=CourtType.INDOOR,
        verbose_name=_("Тип корта")
    )

    play_format = models.CharField(
        max_length=20,
        choices=PlayFormat.choices,
        default=PlayFormat.TWO_VS_TWO,
        verbose_name=_("Формат игры"),
        help_text=_("2x2 — Panoramic корты (4 игрока), 1x1 — Single корт (2 игрока)")
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Описание")
    )

    price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10000.00,
        verbose_name=_("Цена за час (базовая / резерв)"),
        help_text=_("Используется как резерв, если не заданы ценовые слоты")
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Активен")
    )

    image = models.ImageField(upload_to='courts/', blank=True, null=True, verbose_name="Главное фото")

    class Meta:
        verbose_name = _("Корт")
        verbose_name_plural = _("Корты")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_court_type_display()}, {self.get_play_format_display()})"

    def get_price_for_slot(self, start_dt, end_dt):
        """
        Рассчитывает стоимость аренды корта с учётом временных ценовых слотов.
        Если слоты не заданы — использует базовую price_per_hour.
        """
        from django.utils.timezone import localtime
        from datetime import timedelta, time as dt_time

        slots = list(self.price_slots.all().order_by('start_time'))
        if not slots:
            hours = Decimal(str((end_dt - start_dt).total_seconds() / 3600))
            return Decimal(str(self.price_per_hour)) * hours

        total = Decimal('0')
        current = localtime(start_dt)
        end_local = localtime(end_dt)

        while current < end_local:
            curr_time = current.time()
            matched_slot = None

            for slot in slots:
                s_start = slot.start_time
                s_end = slot.end_time
                # time(0,0) для end означает полночь (24:00, конец суток)
                if s_end == dt_time(0, 0):
                    if curr_time >= s_start:
                        matched_slot = slot
                        break
                else:
                    if s_start <= curr_time < s_end:
                        matched_slot = slot
                        break

            if matched_slot:
                s_end = matched_slot.end_time
                if s_end == dt_time(0, 0):
                    # конец слота = полночь следующего дня
                    slot_end_dt = current.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)
                else:
                    slot_end_dt = current.replace(
                        hour=s_end.hour, minute=s_end.minute, second=0, microsecond=0
                    )
                    if slot_end_dt <= current:
                        slot_end_dt += timedelta(days=1)

                period_end = min(end_local, slot_end_dt)
                hours_in_slot = Decimal(str((period_end - current).total_seconds() / 3600))
                total += matched_slot.price_per_hour * hours_in_slot
                current = period_end
            else:
                # слот не найден — применяем базовую цену для остатка времени
                remaining_hours = Decimal(str((end_local - current).total_seconds() / 3600))
                total += Decimal(str(self.price_per_hour)) * remaining_hours
                break

        return total


class CourtPriceSlot(models.Model):
    """
    Ценовые слоты корта по времени суток.
    Пример: Panoramic 06:00-08:00 = 10 000 ₸/ч, 08:00-00:00 = 18 000 ₸/ч
    """
    court = models.ForeignKey(
        Court,
        on_delete=models.CASCADE,
        related_name='price_slots',
        verbose_name=_("Корт")
    )
    start_time = models.TimeField(
        verbose_name=_("Начало слота"),
        help_text=_("Например: 06:00")
    )
    end_time = models.TimeField(
        verbose_name=_("Конец слота"),
        help_text=_("Например: 08:00. Для полуночи (конец суток) укажите 00:00")
    )
    price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Цена за час в этом слоте")
    )

    class Meta:
        verbose_name = _("Ценовой слот корта")
        verbose_name_plural = _("Ценовые слоты кортов")
        ordering = ['court', 'start_time']

    def __str__(self):
        end_label = "00:00 (полночь)" if self.end_time.hour == 0 and self.end_time.minute == 0 else self.end_time.strftime('%H:%M')
        return f"{self.court.name}: {self.start_time.strftime('%H:%M')}–{end_label} = {self.price_per_hour}₸/ч"


class CourtImage(models.Model):
    court = models.ForeignKey(Court, related_name='gallery', on_delete=models.CASCADE, verbose_name="Корт")
    image = models.ImageField(upload_to='courts/gallery/', verbose_name="Фото")

    def __str__(self):
        return f"Фото для {self.court.name}"
