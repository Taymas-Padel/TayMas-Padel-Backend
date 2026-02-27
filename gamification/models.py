from django.db import models
from django.contrib.auth import get_user_model
from courts.models import Court

User = get_user_model()

class Match(models.Model):
    class MatchType(models.TextChoices):
        SINGLE = 'SINGLE', '1 на 1'
        DOUBLE = 'DOUBLE', '2 на 2'

    # Кто играл (Команда А и Команда Б)
    # Используем ManyToMany, так как игроков может быть несколько
    team_a = models.ManyToManyField(User, related_name='matches_as_team_a', verbose_name="Команда А")
    team_b = models.ManyToManyField(User, related_name='matches_as_team_b', verbose_name="Команда Б")

    # Счет (Например: "6:4, 6:3")
    score = models.CharField(max_length=50, verbose_name="Счет матча")

    # Кто победил? (A или B)
    winner_team = models.CharField(
        max_length=10, 
        choices=[('A', 'Команда А'), ('B', 'Команда Б'), ('DRAW', 'Ничья')],
        verbose_name="Победитель"
    )

    # Тренер, который подтвердил матч и рейтинг
    judge = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='judged_matches',
        verbose_name="Судья/Тренер"
    )

    court = models.ForeignKey(Court, on_delete=models.SET_NULL, null=True, verbose_name="Корт")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата игры")

    # Флаг: Рейтинг уже обновлен? (чтобы не начислить дважды)
    is_rated = models.BooleanField(default=False, verbose_name="Рейтинг начислен")

    # ELO-дельта: {"player_id": delta} — сколько получил/потерял каждый игрок
    elo_changes = models.JSONField(default=dict, blank=True, verbose_name="Изменения ELO")

    def __str__(self):
        return f"Матч {self.date.strftime('%d.%m')} | {self.score}"

    class Meta:
        verbose_name = "Матч"
        verbose_name_plural = "Матчи"