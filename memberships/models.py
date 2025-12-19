from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class MembershipType(models.Model):
    """Товар в магазине: Пакет 10 часов"""
    name = models.CharField(max_length=100, verbose_name="Название")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    total_hours = models.DecimalField(max_digits=6, decimal_places=1, verbose_name="Кол-во часов") # 10.0, 20.0
    days_valid = models.PositiveIntegerField(verbose_name="Срок действия (дней)", default=30)
    is_active = models.BooleanField(default=True, verbose_name="В продаже")

    def __str__(self):
        return f"{self.name} ({self.total_hours}ч) - {self.price}₸"

class UserMembership(models.Model):
    """Купленный пакет конкретного юзера"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    membership_type = models.ForeignKey(MembershipType, on_delete=models.PROTECT)
    
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    
    # Самое важное поле: Баланс часов. Decimal, чтобы списывать 1.5 часа.
    hours_remaining = models.DecimalField(max_digits=6, decimal_places=1, verbose_name="Остаток часов")
    
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Если часов не осталось - деактивируем
        if self.hours_remaining <= 0:
            self.is_active = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} | Осталось: {self.hours_remaining}ч"