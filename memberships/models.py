from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class MembershipType(models.Model):
    """Вид абонемента (Товар)"""
    
    # 👇 1. ТИПЫ УСЛУГ (Чтобы разделять Падел и Качалку)
    SERVICE_CHOICES = [
        ('PADEL', 'Падел (Часы)'),
        ('GYM_UNLIMITED', 'Фитнес (Безлимит)'),
        ('GYM_PACK', 'Фитнес (Пакет посещений)'),
    ]

    name = models.CharField(max_length=100, verbose_name="Название")
    
    # 👇 Добавили тип услуги
    service_type = models.CharField(
        max_length=20, 
        choices=SERVICE_CHOICES, 
        default='PADEL', 
        verbose_name="Тип услуги"
    )
    
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    days_valid = models.PositiveIntegerField(verbose_name="Срок действия (дней)", default=30)
    
    # --- ЛИМИТЫ ---
    total_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0, verbose_name="Часы (для Падела)")
    
    # 👇 Добавили посещения для зала
    total_visits = models.PositiveIntegerField(default=0, verbose_name="Посещения (для Gym Pack)")

    # --- ЛОЯЛЬНОСТЬ ---
    # 👇 Добавили скидку, которую дает этот абонемент на другие услуги
    discount_on_court = models.IntegerField(default=0, verbose_name="Скидка на Падел (%)")

    is_active = models.BooleanField(default=True, verbose_name="В продаже")

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"


class UserMembership(models.Model):
    """Купленный пакет конкретного юзера"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    membership_type = models.ForeignKey(MembershipType, on_delete=models.PROTECT)
    
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    
    # --- БАЛАНСЫ ---
    hours_remaining = models.DecimalField(max_digits=6, decimal_places=1, default=0, verbose_name="Остаток часов")
    
    # 👇 Добавили остаток посещений
    visits_remaining = models.PositiveIntegerField(default=0, verbose_name="Остаток посещений")
    
    # --- СТАТУСЫ ---
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False, verbose_name="Заморожен")
    freeze_start_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата начала заморозки")
    
    def __str__(self):
        status = "❄️ ЗАМОРОЖЕН" if self.is_frozen else "Активен"
        return f"{self.user.username} | {self.membership_type.name} | {status}"
    
    def save(self, *args, **kwargs):
        # Логика деактивации:
        # Если это ПАДЕЛ и часы кончились -> отключаем
        if self.membership_type.service_type == 'PADEL' and self.hours_remaining <= 0:
            self.is_active = False
            
        # Если это ПАКЕТ ЗАЛА и входы кончились -> отключаем
        elif self.membership_type.service_type == 'GYM_PACK' and self.visits_remaining <= 0:
            self.is_active = False
            
        # Для БЕЗЛИМИТА (GYM_UNLIMITED) отключение только по дате (внешняя задача или проверка при входе)
            
        super().save(*args, **kwargs)