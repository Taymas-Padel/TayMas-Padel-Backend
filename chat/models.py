from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Conversation(models.Model):
    """
    Диалог между двумя пользователями (1-на-1).
    user1.id всегда < user2.id — гарантирует уникальность пары.
    """
    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='conversations_as_user1',
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='conversations_as_user2',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Диалог')
        verbose_name_plural = _('Диалоги')
        unique_together = ('user1', 'user2')
        ordering = ['-updated_at']

    def __str__(self):
        return f'Диалог #{self.pk}: {self.user1} ↔ {self.user2}'

    @staticmethod
    def get_or_create_for_users(a: User, b: User) -> 'Conversation':
        """Найти или создать диалог, гарантируя user1.id < user2.id."""
        u1, u2 = (a, b) if a.id < b.id else (b, a)
        conv, _ = Conversation.objects.get_or_create(user1=u1, user2=u2)
        return conv


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages',
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages',
    )
    text = models.TextField(verbose_name=_('Текст сообщения'))
    is_read = models.BooleanField(default=False, verbose_name=_('Прочитано'))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Сообщение')
        verbose_name_plural = _('Сообщения')
        ordering = ['created_at']

    def __str__(self):
        preview = self.text[:40] + ('…' if len(self.text) > 40 else '')
        return f'{self.sender} → {preview}'
