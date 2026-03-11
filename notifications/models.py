from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Notification(models.Model):
    class Type(models.TextChoices):
        BOOKING = 'BOOKING', 'Бронирование'
        MEMBERSHIP = 'MEMBERSHIP', 'Абонемент'
        FRIEND = 'FRIEND', 'Друзья'
        MATCH = 'MATCH', 'Матч / ELO'
        LOBBY = 'LOBBY', 'Лобби'
        PROMO = 'PROMO', 'Акция'
        NEWS = 'NEWS', 'Новость'
        PAYMENT = 'PAYMENT', 'Оплата'
        MESSAGE = 'MESSAGE', 'Сообщение'
        SYSTEM = 'SYSTEM', 'Система'

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Получатель"
    )
    notification_type = models.CharField(
        max_length=15, choices=Type.choices, default=Type.SYSTEM, verbose_name="Тип"
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    body = models.TextField(blank=True, verbose_name="Текст")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    data = models.JSONField(default=dict, blank=True, verbose_name="Данные (доп.)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.title}"


def send_notification(user, notification_type, title, body='', data=None):
    """Helper: создать in-app уведомление для пользователя."""
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data or {},
    )
