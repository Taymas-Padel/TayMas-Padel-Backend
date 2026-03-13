"""
Утилиты для генерации турнирной сетки Single Elimination.
"""
import math
from .models import TournamentTeam, TournamentMatch


def _next_power_of_two(n):
    p = 1
    while p < n:
        p *= 2
    return p


def get_round_name(round_number, total_rounds):
    """Возвращает читаемое название раунда."""
    rounds_from_end = total_rounds - round_number
    names = {0: 'Финал', 1: 'Полуфинал', 2: '1/4 финала', 3: '1/8 финала', 4: '1/16 финала'}
    return names.get(rounds_from_end, f'Раунд {round_number}')


def generate_bracket(tournament):
    """
    Генерирует сетку Single Elimination для турнира.
    Берёт команды со статусом CONFIRMED или PAID, упорядоченных по seed.
    Возвращает список созданных матчей.
    """
    teams = list(
        tournament.teams.filter(
            status__in=[TournamentTeam.Status.CONFIRMED, TournamentTeam.Status.PAID]
        ).order_by('seed', 'registered_at')
    )

    n = len(teams)
    if n < 2:
        raise ValueError('Нужно минимум 2 подтверждённые команды для генерации сетки.')

    bracket_size = _next_power_of_two(n)
    total_rounds = int(math.log2(bracket_size))

    # Удалить все старые матчи
    tournament.matches.all().delete()

    # Создать все матч-слоты
    matches = {}
    for r in range(1, total_rounds + 1):
        slots = bracket_size // (2 ** r)
        for pos in range(1, slots + 1):
            m = TournamentMatch.objects.create(
                tournament=tournament,
                round_number=r,
                match_number=pos,
                status=TournamentMatch.Status.SCHEDULED,
            )
            matches[(r, pos)] = m

    # Связать next_match (winner переходит в следующий матч)
    for r in range(1, total_rounds):
        slots = bracket_size // (2 ** r)
        for pos in range(1, slots + 1):
            next_pos = math.ceil(pos / 2)
            matches[(r, pos)].next_match = matches[(r + 1, next_pos)]
            matches[(r, pos)].save(update_fields=['next_match'])

    # Посеять команды в Раунд 1
    padded = teams + [None] * (bracket_size - n)  # None = bye
    round1_slots = bracket_size // 2

    for pos in range(1, round1_slots + 1):
        m = matches[(1, pos)]
        t1 = padded[(pos - 1) * 2]
        t2 = padded[(pos - 1) * 2 + 1]
        m.team1 = t1
        m.team2 = t2

        # Авто-проход при bye
        if t1 and not t2:
            m.winner = t1
            m.status = TournamentMatch.Status.WALKOVER
        elif t2 and not t1:
            m.winner = t2
            m.status = TournamentMatch.Status.WALKOVER

        m.save()

        if m.winner:
            _advance_winner(m)

    return list(matches.values())


def _advance_winner(match):
    """Продвигает победителя в следующий матч сетки."""
    if not match.winner or not match.next_match:
        return
    nm = match.next_match
    # Нечётный номер → team1, чётный → team2
    if match.match_number % 2 == 1:
        nm.team1 = match.winner
    else:
        nm.team2 = match.winner
    nm.save(update_fields=['team1', 'team2'])


def set_match_result(match, winner_team, score_team1='', score_team2=''):
    """
    Фиксирует результат матча и продвигает победителя по сетке.
    """
    if match.status == TournamentMatch.Status.COMPLETED:
        raise ValueError('Матч уже завершён.')
    if winner_team not in (match.team1, match.team2):
        raise ValueError('Победитель должен быть одной из команд матча.')

    match.winner = winner_team
    match.score_team1 = score_team1
    match.score_team2 = score_team2
    match.status = TournamentMatch.Status.COMPLETED
    match.save()

    _advance_winner(match)
    return match


def validate_match_schedule(match, court, scheduled_at, duration_minutes=90, exclude_match_id=None):
    """
    Проверяет конфликты при назначении матча на корт и время.
    Возвращает список строк с ошибками (пустой список = ОК).
    """
    from datetime import timedelta
    errors = []

    if not court or not scheduled_at:
        return errors

    end_dt = scheduled_at + timedelta(minutes=duration_minutes)

    # 1. Конфликт корта
    court_qs = TournamentMatch.objects.filter(
        court=court,
        scheduled_at__lt=end_dt,
        scheduled_at__isnull=False,
    ).exclude(
        scheduled_at__lt=scheduled_at - timedelta(minutes=duration_minutes)
    ).exclude(status='CANCELED')

    if exclude_match_id:
        court_qs = court_qs.exclude(pk=exclude_match_id)

    # Фильтр пересечений вручную (простой overlap)
    conflicts = [
        m for m in court_qs
        if m.scheduled_at < end_dt and
           (m.scheduled_at + timedelta(minutes=duration_minutes)) > scheduled_at
    ]
    if conflicts:
        errors.append(f'Корт «{court.name}» уже занят в это время (матч #{conflicts[0].id}).')

    # 2. Конфликт команд
    for team in [match.team1, match.team2]:
        if not team:
            continue
        team_qs = TournamentMatch.objects.filter(
            tournament=match.tournament,
            scheduled_at__isnull=False,
        ).filter(
            models.Q(team1=team) | models.Q(team2=team)
        ).exclude(status__in=['COMPLETED', 'WALKOVER', 'CANCELED'])
        if exclude_match_id:
            team_qs = team_qs.exclude(pk=exclude_match_id)

        for m in team_qs:
            m_end = m.scheduled_at + timedelta(minutes=duration_minutes)
            if m.scheduled_at < end_dt and m_end > scheduled_at:
                errors.append(
                    f'Команда «{team.display_name}» уже играет в это время (матч #{m.id}).'
                )
                break

    return errors


from django.db import models
