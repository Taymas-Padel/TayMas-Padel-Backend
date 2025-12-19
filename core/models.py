from django.db import models

class ClubSetting(models.Model):
    # Список разрешенных настроек
    SETTINGS_CHOICES = [
        ('OPEN_TIME', 'Время открытия (ЧЧ:ММ)'),
        ('CLOSE_TIME', 'Время закрытия (ЧЧ:ММ)'),
        ('CANCELLATION_HOURS', 'Политика отмены бронирования (часы)'),
    ]

    key = models.CharField(
        max_length=50, 
        choices=SETTINGS_CHOICES, # <--- Выпадающий список
        unique=True, 
        verbose_name="Настройка"
    )
    value = models.CharField(max_length=255, verbose_name="Значение")
    description = models.CharField(max_length=255, blank=True, verbose_name="Описание")

    def __str__(self):
        return f"{self.get_key_display()}: {self.value}"

    class Meta:
        verbose_name = "Настройка клуба"
        verbose_name_plural = "Настройки клуба (Core)"


# ... (твой код ClubSetting выше) ...

class ClosedDay(models.Model):
    date = models.DateField(unique=True, verbose_name="Дата закрытия")
    reason = models.CharField(max_length=255, blank=True, verbose_name="Причина (Например: Новый Год)")

    def __str__(self):
        return f"{self.date} — {self.reason}"

    class Meta:
        verbose_name = "Выходной / Спец. день"
        verbose_name_plural = "Выходные и Праздники (Core)"
        ordering = ['date']