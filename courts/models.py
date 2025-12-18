from django.db import models
from django.utils.translation import gettext_lazy as _

class Court(models.Model):
    """
    Модель падел-корта.
    """
    name = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name=_("Название/Номер корта")
    )
    
    # Тип покрытия (важно для игроков)
    description = models.TextField(
        blank=True, 
        verbose_name=_("Описание / Покрытие")
    )
    
    # Базовая цена за час (по умолчанию)
    price_per_hour = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name=_("Цена за час (базовая)")
    )

    # Работает корт или на ремонте
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("Активен")
    )

    # Фото корта (для мобильного приложения)
    image = models.ImageField(
        upload_to='courts/', 
        blank=True, 
        null=True,
        verbose_name=_("Фото корта")
    )

    class Meta:
        verbose_name = _("Корт")
        verbose_name_plural = _("Корты")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({int(self.price_per_hour)} ₸)"