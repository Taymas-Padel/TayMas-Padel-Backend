from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class Lobby(models.Model):
    class GameFormat(models.TextChoices):
        SINGLE = 'SINGLE', 'Одиночная (1×1, 2 игрока)'
        DOUBLE = 'DOUBLE', 'Парная (2×2, 4 игрока)'

    class Status(models.TextChoices):
        OPEN         = 'OPEN',         'Ищем игроков'
        WAITING      = 'WAITING',      'Частично заполнено'
        NEGOTIATING  = 'NEGOTIATING',  'Согласование времени/корта'
        READY        = 'READY',        'Время согласовано — ждём бронь'
        BOOKED       = 'BOOKED',       'Бронь создана — ждём оплату'
        PAID         = 'PAID',         'Все оплатили — бронь подтверждена'
        CLOSED       = 'CLOSED',       'Закрыто'

    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='created_lobbies', verbose_name="Создатель"
    )
    title = models.CharField(max_length=100, verbose_name="Название лобби")
    game_format = models.CharField(
        max_length=10, choices=GameFormat.choices, default=GameFormat.DOUBLE, verbose_name="Формат"
    )

    # ELO диапазон вместо ручного выбора уровня
    elo_min = models.PositiveIntegerField(default=0, verbose_name="ELO минимум")
    elo_max = models.PositiveIntegerField(default=9999, verbose_name="ELO максимум")

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.OPEN, verbose_name="Статус"
    )

    # Корт и время заполняются ПОСЛЕ согласования (через LobbyTimeProposal)
    court = models.ForeignKey(
        'courts.Court', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Корт (после согласования)"
    )
    scheduled_time = models.DateTimeField(null=True, blank=True, verbose_name="Время игры (после согласования)")

    # Тренер (опционально): при создании брони из лобби он попадёт в бронь и в расписание тренера
    coach = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lobbies_as_coach',
        verbose_name="Тренер",
        help_text="При создании брони из лобби тренер будет назначен в бронь и увидит её в расписании.",
    )
    duration_minutes = models.IntegerField(default=90, verbose_name="Длительность (мин)")

    booking = models.ForeignKey(
        'bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lobby', verbose_name="Созданная бронь"
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True)

    def max_players(self):
        return 2 if self.game_format == 'SINGLE' else 4

    def current_players_count(self):
        return self.participants.count()

    def update_status(self):
        count = self.current_players_count()
        max_p = self.max_players()
        if self.status in ['BOOKED', 'PAID', 'CLOSED', 'READY', 'NEGOTIATING']:
            return
        if count >= max_p:
            self.status = 'NEGOTIATING'
        elif count > 1:
            self.status = 'WAITING'
        else:
            self.status = 'OPEN'
        self.save(update_fields=['status'])

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

    class Meta:
        verbose_name = "Лобби"
        verbose_name_plural = "Лобби (поиск партнёров)"
        ordering = ['-created_at']


class LobbyTimeProposal(models.Model):
    """Предложение времени и корта — любой участник может предложить."""
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='proposals')
    proposed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lobby_proposals')
    court = models.ForeignKey('courts.Court', on_delete=models.CASCADE, verbose_name="Корт")
    scheduled_time = models.DateTimeField(verbose_name="Предлагаемое время")
    duration_minutes = models.IntegerField(default=90, verbose_name="Длительность (мин)")
    votes = models.ManyToManyField(User, related_name='voted_proposals', blank=True, verbose_name="Голоса «за»")
    is_accepted = models.BooleanField(default=False, verbose_name="Принято")
    created_at = models.DateTimeField(auto_now_add=True)

    def votes_count(self):
        return self.votes.count()

    class Meta:
        verbose_name = "Предложение времени"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lobby.title} → {self.court.name} {self.scheduled_time:%d.%m %H:%M}"


class LobbyParticipant(models.Model):
    class Team(models.TextChoices):
        A = 'A', 'Команда A'
        B = 'B', 'Команда B'

    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lobby_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    team = models.CharField(max_length=1, choices=Team.choices, null=True, blank=True)

    court_share = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    membership_used = models.BooleanField(default=False, verbose_name="Абонемент использован")
    share_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_paid = models.BooleanField(default=False, verbose_name="Оплачено")
    paid_at = models.DateTimeField(null=True, blank=True)

    def extras_total(self):
        total = Decimal('0')
        for e in self.extras.all():
            total += Decimal(str(e.price_at_moment)) * e.quantity
        return total

    def recalculate_share(self):
        self.share_amount = self.court_share + self.extras_total()
        self.save(update_fields=['share_amount'])

    class Meta:
        unique_together = ('lobby', 'user')
        verbose_name = "Участник лобби"

    def __str__(self):
        return f"{self.user} в {self.lobby}"


class LobbyParticipantExtra(models.Model):
    """Личные дополнительные услуги/инвентарь участника лобби."""
    participant = models.ForeignKey(
        LobbyParticipant, on_delete=models.CASCADE, related_name='extras'
    )
    service = models.ForeignKey(
        'inventory.Service', on_delete=models.CASCADE, verbose_name="Услуга/Инвентарь"
    )
    quantity = models.IntegerField(default=1)
    price_at_moment = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена на момент добавления"
    )

    def subtotal(self):
        return Decimal(str(self.price_at_moment)) * self.quantity

    class Meta:
        verbose_name = "Доп. услуга участника лобби"

    def __str__(self):
        return f"{self.participant.user} — {self.service.name} x{self.quantity}"
