from django.db import models
from django.conf import settings


class Lead(models.Model):

    class Stage(models.TextChoices):
        NEW = 'NEW', 'Новые обращения'
        IN_PROGRESS = 'IN_PROGRESS', 'В работе'
        NEGOTIATION = 'NEGOTIATION', 'Переговоры'
        SOLD = 'SOLD', 'Успешная продажа'
        LOST = 'LOST', 'Закрыто / потеря'

    class Source(models.TextChoices):
        PHONE_CALL = 'PHONE_CALL', 'Звонок'
        INSTAGRAM = 'INSTAGRAM', 'Instagram'
        WEBSITE = 'WEBSITE', 'Сайт'
        WALK_IN = 'WALK_IN', 'Пришёл сам'
        REFERRAL = 'REFERRAL', 'Рекомендация'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        OTHER = 'OTHER', 'Другое'

    name = models.CharField(max_length=150, verbose_name="Имя")
    phone = models.CharField(max_length=30, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.OTHER,
        verbose_name="Источник"
    )

    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.NEW,
        verbose_name="Стадия"
    )

    notes = models.TextField(blank=True, verbose_name="Заметки")

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        limit_choices_to={'role__in': ['ADMIN', 'RECEPTIONIST', 'SALES_MANAGER']},
        verbose_name="Назначен менеджеру"
    )

    last_contact = models.DateTimeField(null=True, blank=True, verbose_name="Последний контакт")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Лид"
        verbose_name_plural = "Лиды"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone}) — {self.get_stage_display()}"


class LeadComment(models.Model):
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Лид"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lead_comments',
        verbose_name="Автор"
    )
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "Комментарий к лиду"
        verbose_name_plural = "Комментарии к лидам"
        ordering = ['created_at']

    def __str__(self):
        return f"Комментарий к лиду #{self.lead_id} от {self.author}"


class LeadTask(models.Model):
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Лид"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_tasks',
        verbose_name="Исполнитель"
    )
    title = models.CharField(max_length=255, verbose_name="Задача")
    due_datetime = models.DateTimeField(verbose_name="Срок выполнения")
    is_done = models.BooleanField(default=False, verbose_name="Выполнена")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Задача по лиду"
        verbose_name_plural = "Задачи по лидам"
        ordering = ['due_datetime']

    def __str__(self):
        status = "✓" if self.is_done else "○"
        return f"{status} {self.title} (лид #{self.lead_id})"
