from django.db import models


class Service(models.Model):
    class ServiceGroup(models.TextChoices):
        PADEL = 'PADEL', 'Падел / Корты'
        GYM = 'GYM', 'Фитнес / Зал'
        RECOVERY = 'RECOVERY', 'Recovery / Массаж'
        SPORT_BAR = 'SPORT_BAR', 'Спорт-бар'
        OTHER = 'OTHER', 'Другое'

    class Category(models.TextChoices):
        INVENTORY = 'INVENTORY', 'Инвентарь / Аренда'
        SERVICE = 'SERVICE', 'Услуга'
        FOOD = 'FOOD', 'Еда'
        DRINK = 'DRINK', 'Напиток'
        EVENT = 'EVENT', 'Турнир / Мероприятие'

    name = models.CharField(max_length=100, verbose_name="Название (Ракетка, Вода)")
    description = models.TextField(blank=True, verbose_name="Описание", help_text="Опционально. Пояснение для клиента.")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")

    group = models.CharField(
        max_length=20,
        choices=ServiceGroup.choices,
        default=ServiceGroup.OTHER,
        verbose_name="Группа (где используется)",
        help_text="Например: Падел, Фитнес/зал, Recovery, Спорт-бар.",
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.INVENTORY,
        verbose_name="Категория",
        help_text="Инвентарь, услуга, еда, напиток, турнир и т.п.",
    )

    is_active = models.BooleanField(default=True, verbose_name="Доступно для выбора")

    def __str__(self):
        return f"{self.name} ({self.price} ₸)"

    class Meta:
        verbose_name = "Услуга / Инвентарь"
        verbose_name_plural = "Инвентарь"