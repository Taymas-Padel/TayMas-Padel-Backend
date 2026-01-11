from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class FriendRequest(models.Model):
    """
    Заявка в друзья.
    Если status='ACCEPTED', значит пользователи - друзья.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Ожидает'
        ACCEPTED = 'ACCEPTED', 'Принято'
        REJECTED = 'REJECTED', 'Отклонено'

    from_user = models.ForeignKey(User, related_name='sent_friend_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_friend_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user') # Нельзя отправить 2 заявки одному человеку
        verbose_name = "Заявка в друзья"
        verbose_name_plural = "Заявки в друзья"

    def clean(self):
        # Защита: нельзя добавить самого себя
        if self.from_user == self.to_user:
            raise ValidationError("Нельзя добавить самого себя в друзья.")

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"