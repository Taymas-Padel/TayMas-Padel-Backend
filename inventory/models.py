from django.db import models

class Service(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название (Ракетка, Вода)")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    is_active = models.BooleanField(default=True, verbose_name="Доступно для выбора")

    def __str__(self):
        return f"{self.name} ({self.price} ₸)"

    class Meta:
        verbose_name = "Услуга / Инвентарь"
        verbose_name_plural = "Инвентарь"