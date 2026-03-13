from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from courts.models import Court

User = get_user_model()


class Tournament(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Черновик')
        REGISTRATION = 'REGISTRATION', _('Открыта регистрация')
        IN_PROGRESS = 'IN_PROGRESS', _('Идёт турнир')
        COMPLETED = 'COMPLETED', _('Завершён')
        CANCELED = 'CANCELED', _('Отменён')

    class Format(models.TextChoices):
        SINGLES = 'SINGLES', _('Одиночный')
        DOUBLES = 'DOUBLES', _('Парный падел')

    name = models.CharField(max_length=200, verbose_name=_('Название'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    start_date = models.DateTimeField(verbose_name=_('Дата начала'))
    end_date = models.DateTimeField(verbose_name=_('Дата окончания'))
    registration_deadline = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Дедлайн регистрации'),
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
        verbose_name=_('Статус'),
    )
    format = models.CharField(
        max_length=20, choices=Format.choices, default=Format.DOUBLES,
        verbose_name=_('Формат'),
    )
    is_paid = models.BooleanField(default=False, verbose_name=_('Платный'))
    entry_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Взнос (₸)'),
    )
    max_teams = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_('Макс. команд'),
        help_text=_('Оставьте пустым — без ограничений'),
    )
    prize_info = models.TextField(blank=True, verbose_name=_('Призовой фонд / условия'))
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_tournaments', verbose_name=_('Создал'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Турнир')
        verbose_name_plural = _('Турниры')
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'

    @property
    def teams_count(self):
        return self.teams.exclude(status=TournamentTeam.Status.WITHDRAWN).count()

    @property
    def paid_teams_count(self):
        return self.teams.filter(status=TournamentTeam.Status.PAID).count()

    # Status transition helpers
    ALLOWED_TRANSITIONS = {
        'DRAFT':        ['REGISTRATION', 'CANCELED'],
        'REGISTRATION': ['IN_PROGRESS', 'CANCELED'],
        'IN_PROGRESS':  ['COMPLETED', 'CANCELED'],
        'COMPLETED':    [],
        'CANCELED':     [],
    }

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, [])


class TournamentTeam(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'PENDING',   _('Заявка')
        CONFIRMED = 'CONFIRMED', _('Подтверждён')
        PAID      = 'PAID',      _('Оплачен')
        WITHDRAWN = 'WITHDRAWN', _('Снят')
        REFUNDED  = 'REFUNDED',  _('Возврат')

    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE,
        related_name='teams', verbose_name=_('Турнир'),
    )
    player1 = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='tournament_teams_p1', verbose_name=_('Игрок 1'),
    )
    player2 = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tournament_teams_p2', verbose_name=_('Игрок 2 (пара)'),
    )
    team_name = models.CharField(
        max_length=100, blank=True, verbose_name=_('Название команды'),
        help_text=_('Если пусто — генерируется из имён игроков'),
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        verbose_name=_('Статус'),
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    confirmed_at  = models.DateTimeField(null=True, blank=True)
    paid_at       = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='confirmed_tournament_payments',
        verbose_name=_('Оплату принял'),
    )
    payment_method = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('CASH', 'Наличные'), ('KASPI', 'Kaspi'), ('CARD', 'Карта'), ('OTHER', 'Другое'),
        ],
        verbose_name=_('Способ оплаты'),
    )
    seed = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_('Сид (посев)'),
        help_text=_('1 = топ-сид. Влияет на жеребьёвку сетки'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Примечания'))

    class Meta:
        verbose_name = _('Команда')
        verbose_name_plural = _('Команды')
        ordering = ['seed', 'registered_at']
        unique_together = [('tournament', 'player1')]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.team_name:
            return self.team_name
        p1 = _player_short(self.player1)
        if self.player2:
            return f'{p1} / {_player_short(self.player2)}'
        return p1


def _player_short(user):
    if not user:
        return '—'
    full = f'{user.first_name} {user.last_name}'.strip()
    return full or user.username


class TournamentMatch(models.Model):
    class Status(models.TextChoices):
        SCHEDULED   = 'SCHEDULED',   _('Запланирован')
        IN_PROGRESS = 'IN_PROGRESS', _('Идёт')
        COMPLETED   = 'COMPLETED',   _('Завершён')
        POSTPONED   = 'POSTPONED',   _('Перенесён')
        WALKOVER    = 'WALKOVER',    _('Технический выигрыш')

    tournament   = models.ForeignKey(
        Tournament, on_delete=models.CASCADE,
        related_name='matches', verbose_name=_('Турнир'),
    )
    round_number = models.PositiveIntegerField(verbose_name=_('Раунд'))
    match_number = models.PositiveIntegerField(verbose_name=_('Номер матча в раунде'))
    team1 = models.ForeignKey(
        TournamentTeam, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='matches_as_team1', verbose_name=_('Команда 1'),
    )
    team2 = models.ForeignKey(
        TournamentTeam, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='matches_as_team2', verbose_name=_('Команда 2'),
    )
    winner = models.ForeignKey(
        TournamentTeam, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='won_matches', verbose_name=_('Победитель'),
    )
    court = models.ForeignKey(
        Court, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Корт'),
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Время матча'))
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED,
        verbose_name=_('Статус'),
    )
    score_team1 = models.CharField(max_length=50, blank=True, verbose_name=_('Счёт команды 1'))
    score_team2 = models.CharField(max_length=50, blank=True, verbose_name=_('Счёт команды 2'))
    next_match = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='source_matches', verbose_name=_('Следующий матч'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Примечания'))

    class Meta:
        verbose_name = _('Матч')
        verbose_name_plural = _('Матчи')
        ordering = ['round_number', 'match_number']
        unique_together = [('tournament', 'round_number', 'match_number')]

    def __str__(self):
        t1 = self.team1.display_name if self.team1 else 'TBD'
        t2 = self.team2.display_name if self.team2 else 'TBD'
        return f'Раунд {self.round_number}, матч {self.match_number}: {t1} vs {t2}'
