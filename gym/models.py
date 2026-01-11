from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class GymVisit(models.Model):
    """Журнал посещений (Турникет)"""
    CHECKIN_TYPES = [
        ('SUBSCRIPTION', 'По абонементу'),
        ('ONE_TIME', 'Разовый (Платный)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gym_visits', verbose_name="Клиент")
    entry_time = models.DateTimeField(auto_now_add=True, verbose_name="Время входа")
    checkin_type = models.CharField(max_length=20, choices=CHECKIN_TYPES, verbose_name="Тип входа")
    
    def __str__(self):
        return f"{self.user.username} - {self.entry_time.strftime('%d.%m %H:%M')}"

    class Meta:
        verbose_name = "Посещение зала"
        verbose_name_plural = "Посещения зала"


class PersonalTraining(models.Model):
    """Тренировка с тренером в зале (без аренды корта)"""
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gym_trainings_client', verbose_name="Клиент")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gym_trainings_coach', verbose_name="Тренер")
    
    # Можно просто дату/время
    start_time = models.DateTimeField(verbose_name="Время начала")
    
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    is_paid = models.BooleanField(default=False, verbose_name="Оплачено")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Тренер {self.coach} - Клиент {self.client}"

    class Meta:
        verbose_name = "Персональная тренировка (Gym)"
        verbose_name_plural = "Тренировки (Gym)"