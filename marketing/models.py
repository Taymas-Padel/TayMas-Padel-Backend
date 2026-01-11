from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Promotion(models.Model):
    DISCOUNT_TYPES = [
        ('PERCENT', 'Процент (%)'),
        ('FIXED', 'Фиксированная сумма (₸)'),
    ]

    # Витрина
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    image_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на картинку")
    priority = models.IntegerField(default=0, verbose_name="Приоритет показа")

    # Логика скидки
    promo_code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Промокод (если есть)")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='PERCENT')
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, 
        verbose_name="Величина скидки",
        validators=[MinValueValidator(0)]
    )

    # Сроки
    start_date = models.DateTimeField(verbose_name="Начало")
    end_date = models.DateTimeField(verbose_name="Конец")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        ordering = ['-priority', '-start_date']
        verbose_name = "Акция"
        verbose_name_plural = "Маркетинг (Акции)"

    def __str__(self):
        return f"{self.title} ({self.promo_code or 'Без кода'})"