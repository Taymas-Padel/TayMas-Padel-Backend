from django.db import models
from django.utils.translation import gettext_lazy as _

class Court(models.Model):
    class CourtType(models.TextChoices):
        INDOOR = 'INDOOR', _('Indoor (Крытый)')
        OUTDOOR = 'OUTDOOR', _('Outdoor (Открытый)')
        PANORAMIC = 'PANORAMIC', _('Panoramic (Панорамный)')

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

    description = models.TextField(
        blank=True, 
        verbose_name=_("Описание")
    )
    
    price_per_hour = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=8000.00,  # Поставил реалистичную цену по умолчанию
        verbose_name=_("Цена за час")
    )

    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("Активен")
    )

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
        return f"{self.name} ({self.get_court_type_display()})"