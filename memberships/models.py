from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import time as dt_time
from decimal import Decimal

User = get_user_model()


class MembershipType(models.Model):
    """
    Тип абонемента (товар в каталоге).
    Сотрудники создают через админку / API — система сама обрабатывает логику.
    """

    SERVICE_CHOICES = [
        ('PADEL_HOURS', 'Падел — Пакет часов'),
        ('TRAINING_HOURS', 'Тренировки с тренером — Пакет часов'),
        ('GYM', 'Фитнес — Безлимит'),
        ('VIP', 'VIP — Комбо пакет'),
    ]

    COURT_TYPE_CHOICES = [
        ('', 'Любой корт'),
        ('INDOOR', 'Indoor'),
        ('OUTDOOR', 'Outdoor'),
        ('PANORAMIC', 'Panoramic'),
        ('SQUASH', 'Squash'),
        ('PING_PONG', 'Ping-pong'),
    ]

    name = models.CharField(max_length=150, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание / Комментарий")

    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_CHOICES,
        default='PADEL_HOURS',
        verbose_name="Тип услуги",
    )

    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена (₸)")
    days_valid = models.PositiveIntegerField(default=30, verbose_name="Срок действия (дней)")

    # --- ЛИМИТЫ ---
    total_hours = models.DecimalField(
        max_digits=6, decimal_places=1, default=0,
        verbose_name="Часы в пакете",
        help_text="Для PADEL_HOURS и TRAINING_HOURS",
    )
    total_visits = models.PositiveIntegerField(
        default=0,
        verbose_name="Посещения (для фитнес-пакетов)",
    )

    # --- ПРИОРИТЕТНОЕ ВРЕМЯ ---
    priority_time_start = models.TimeField(
        null=True, blank=True,
        verbose_name="Приоритетное время — начало",
        help_text="Время без доплаты, напр. 06:00",
    )
    priority_time_end = models.TimeField(
        null=True, blank=True,
        verbose_name="Приоритетное время — конец",
        help_text="Время без доплаты, напр. 15:00",
    )
    prime_time_surcharge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="Доплата за прайм-тайм (₸/час)",
        help_text="Если бронь вне приоритетного окна — доплата за каждый час",
    )

    # --- УЧАСТНИКИ ---
    min_participants = models.PositiveIntegerField(
        default=1, verbose_name="Мин. участников",
    )
    max_participants = models.PositiveIntegerField(
        default=4, verbose_name="Макс. участников",
    )

    # --- ТРЕНЕР ---
    includes_coach = models.BooleanField(
        default=False,
        verbose_name="Включает тренера",
        help_text="Если да — стоимость тренера покрывается пакетом",
    )

    # --- ОГРАНИЧЕНИЕ ПО ТИПУ КОРТА ---
    court_type_restriction = models.CharField(
        max_length=20,
        choices=COURT_TYPE_CHOICES,
        blank=True,
        default='',
        verbose_name="Ограничение по типу корта",
        help_text="Пусто = любой корт",
    )

    # --- ЛОЯЛЬНОСТЬ ---
    discount_on_court = models.IntegerField(
        default=0,
        verbose_name="Скидка на аренду корта (%)",
        help_text="Скидка которую даёт этот абонемент на обычную аренду",
    )

    # --- ЛИМИТ КОЛИЧЕСТВА ЭКЗЕМПЛЯРОВ ---
    max_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Макс. количество проданных экземпляров",
        help_text="Если пусто или 0 — без лимита по количеству.",
    )

    is_active = models.BooleanField(default=True, verbose_name="В продаже")

    class Meta:
        verbose_name = "Тип абонемента"
        verbose_name_plural = "Типы абонементов"
        ordering = ['service_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"

    @property
    def issued_count(self):
        """
        Общее количество выданных абонементов этого типа (все статусы).
        Используется для расчёта остатка при ограниченном тираже (VIP и т.п.).
        """
        return self.usermembership_set.count()

    @property
    def remaining_quantity(self):
        """
        Сколько экземпляров ещё можно продать.
        None означает отсутствие лимита.
        """
        if not self.max_quantity or self.max_quantity <= 0:
            return None
        remaining = self.max_quantity - self.issued_count
        return max(remaining, 0)

    # ------------------------------------------------------------------
    #  Бизнес-логика: рассчёт доплаты за прайм-тайм
    # ------------------------------------------------------------------
    def calc_prime_surcharge(self, booking_start, booking_end):
        """
        Возвращает (surcharge_total, prime_hours) —
        сколько денег и сколько часов попадают в прайм-тайм.
        """
        if not self.priority_time_start or not self.priority_time_end:
            return Decimal('0'), Decimal('0')
        if self.prime_time_surcharge <= 0:
            return Decimal('0'), Decimal('0')

        start_local = timezone.localtime(booking_start)
        end_local = timezone.localtime(booking_end)

        prio_start = self.priority_time_start
        prio_end = self.priority_time_end

        booking_start_t = start_local.time()
        booking_end_t = end_local.time()

        total_minutes = (booking_end - booking_start).total_seconds() / 60

        if booking_start_t >= prio_start and booking_end_t <= prio_end:
            return Decimal('0'), Decimal('0')

        if booking_start_t >= prio_start and booking_start_t < prio_end and booking_end_t > prio_end:
            prime_start = start_local.replace(
                hour=prio_end.hour, minute=prio_end.minute, second=0, microsecond=0,
            )
            prime_minutes = (end_local - prime_start).total_seconds() / 60
        elif booking_start_t >= prio_end or booking_start_t < prio_start:
            prime_minutes = total_minutes
        else:
            prime_minutes = total_minutes

        prime_hours = Decimal(str(prime_minutes)) / Decimal('60')
        surcharge = prime_hours * self.prime_time_surcharge
        return surcharge.quantize(Decimal('1')), prime_hours


class UserMembership(models.Model):
    """Купленный абонемент конкретного пользователя"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    membership_type = models.ForeignKey(MembershipType, on_delete=models.PROTECT)

    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    # --- БАЛАНСЫ ---
    hours_remaining = models.DecimalField(
        max_digits=6, decimal_places=1, default=0,
        verbose_name="Остаток часов",
    )
    visits_remaining = models.PositiveIntegerField(
        default=0, verbose_name="Остаток посещений",
    )

    # --- СТАТУСЫ ---
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False, verbose_name="Заморожен")
    freeze_start_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата начала заморозки",
    )

    class Meta:
        verbose_name = "Абонемент пользователя"
        verbose_name_plural = "Абонементы пользователей"
        ordering = ['-start_date']

    def __str__(self):
        status = "ЗАМОРОЖЕН" if self.is_frozen else ("Активен" if self.is_active else "Неактивен")
        return f"{self.user.username} | {self.membership_type.name} | {status}"

    def save(self, *args, **kwargs):
        stype = self.membership_type.service_type

        if stype in ('PADEL_HOURS', 'TRAINING_HOURS') and self.hours_remaining <= 0:
            self.is_active = False

        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    #  Удобные проверки
    # ------------------------------------------------------------------
    @property
    def is_usable(self):
        """Можно ли сейчас использовать этот абонемент"""
        if not self.is_active or self.is_frozen:
            return False
        if self.end_date and self.end_date < timezone.now():
            return False
        return True

    def can_cover_booking(self, hours_needed, court=None, participant_count=1):
        """Проверяет, может ли абонемент покрыть бронь"""
        if not self.is_usable:
            return False
        if self.hours_remaining < hours_needed:
            return False

        mt = self.membership_type
        if mt.court_type_restriction and court:
            if court.court_type != mt.court_type_restriction:
                return False

        if participant_count < mt.min_participants or participant_count > mt.max_participants:
            return False

        return True
