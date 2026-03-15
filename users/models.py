from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'ADMIN', _('Super Admin')
        RECEPTIONIST = 'RECEPTIONIST', _('Receptionist')
        SALES_MANAGER = 'SALES_MANAGER', _('Sales Manager')
        COACH_PADEL = 'COACH_PADEL', _('Padel Coach')
        COACH_FITNESS = 'COACH_FITNESS', _('Fitness Coach')
        CLIENT = 'CLIENT', _('Client')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name=_("Role")
    )
    price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Цена за час (для тренера, по умолчанию)"
    )
    # Тариф по числу игроков: 1–2 и 3–4 (по документации «Падел-тренировки с тренером»)
    coach_price_1_2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена тренера за час (1–2 игрока)"
    )
    coach_price_3_4 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена тренера за час (3–4 игрока)"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Номер телефона"
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    fcm_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="FCM Token (для пушей)"
    )
    rating_elo = models.IntegerField(default=1200, verbose_name=_("ELO Rating"))

    # Защита QR — блокировка при смене устройства
    last_device_id = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="ID последнего устройства"
    )
    is_qr_blocked = models.BooleanField(
        default=False,
        verbose_name="Блокировка QR (проверка личности)"
    )

    # Трекинг времени
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def get_coach_price_per_hour(self, participant_count):
        """
        Цена тренера за час в зависимости от числа игроков (1–2 или 3–4).
        Если заданы coach_price_1_2 / coach_price_3_4 — используем их, иначе price_per_hour.
        """
        if participant_count <= 2 and self.coach_price_1_2 is not None:
            return self.coach_price_1_2
        if participant_count >= 3 and self.coach_price_3_4 is not None:
            return self.coach_price_3_4
        return self.price_per_hour or 0

    # ---- Флаг: профиль заполнен? ----
    @property
    def is_profile_complete(self):
        """True если имя и фамилия заполнены"""
        return bool(self.first_name and self.last_name)

    # ---- Проверка: может ли входить через SMS? ----
    @property
    def can_login_via_sms(self):
        """Клиенты и тренеры входят через SMS, админы и ресепшн — нет"""
        return self.role in [
            self.Role.CLIENT,
            self.Role.COACH_PADEL,
            self.Role.COACH_FITNESS,
        ]

    # ---- Проверка: может ли входить в CRM по паролю? ----
    @property
    def can_login_to_crm(self):
        """Админы, ресепшн и менеджеры продаж входят в CRM"""
        return self.role in [
            self.Role.SUPER_ADMIN,
            self.Role.RECEPTIONIST,
            self.Role.SALES_MANAGER,
        ]

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.phone_number or self.username