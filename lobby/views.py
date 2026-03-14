from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Lobby, LobbyParticipant, LobbyParticipantExtra, LobbyTimeProposal
from .serializers import (
    LobbySerializer,
    LobbyPatchSerializer,
    LobbyParticipantExtraSerializer,
    LobbyTimeProposalSerializer,
)


# ---------------------------------------------------------------------------
# 1. Список / Создание лобби
# ---------------------------------------------------------------------------

class LobbyListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/lobby/?status=OPEN&format=DOUBLE&elo=1200&has_coach=true&coach=<id>
         Фильтры: status, format, elo, has_coach (true/false), coach (id тренера).
    POST /api/lobby/ — создать лобби (без корта и времени).
         Тело: title, game_format, elo_min, elo_max, comment, coach (опц.)
    """
    serializer_class = LobbySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Lobby.objects.exclude(status='CLOSED').order_by('-created_at')
        status_f = self.request.query_params.get('status')
        format_f = self.request.query_params.get('format')
        elo_f = self.request.query_params.get('elo')
        has_coach_f = self.request.query_params.get('has_coach')
        coach_id_f = self.request.query_params.get('coach')

        if status_f:
            qs = qs.filter(status=status_f.upper())
        if format_f:
            qs = qs.filter(game_format=format_f.upper())
        if elo_f:
            try:
                elo = int(elo_f)
                qs = qs.filter(elo_min__lte=elo, elo_max__gte=elo)
            except ValueError:
                pass
        elif self.request.user.is_authenticated:
            elo = self.request.user.rating_elo
            qs = qs.filter(elo_min__lte=elo, elo_max__gte=elo)
        if has_coach_f is not None and has_coach_f != '':
            from django.db.models import Q
            if str(has_coach_f).lower() in ('true', '1', 'yes'):
                qs = qs.filter(Q(coach__isnull=False) | Q(wants_coach=True))
            elif str(has_coach_f).lower() in ('false', '0', 'no'):
                qs = qs.filter(coach__isnull=True, wants_coach=False)
        if coach_id_f:
            try:
                qs = qs.filter(coach_id=int(coach_id_f))
            except ValueError:
                pass
        return qs

    def create(self, request, *args, **kwargs):
        # Только title, game_format, elo_min/max, comment — корт и время НЕ нужны
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Если elo_min/elo_max не переданы — ставим ±200 от ELO пользователя
        elo_min = serializer.validated_data.get('elo_min', None)
        elo_max = serializer.validated_data.get('elo_max', None)
        if elo_min is None:
            elo_min = max(0, request.user.rating_elo - 200)
        if elo_max is None:
            elo_max = request.user.rating_elo + 200

        wants_coach = serializer.validated_data.get('wants_coach', False)
        lobby = serializer.save(creator=request.user, elo_min=elo_min, elo_max=elo_max, wants_coach=wants_coach)
        # Создатель — первый участник, команда A
        LobbyParticipant.objects.create(lobby=lobby, user=request.user, team='A')
        lobby.update_status()
        return Response(LobbySerializer(lobby, context={'request': request}).data, status=201)


# ---------------------------------------------------------------------------
# 2. Детали
# ---------------------------------------------------------------------------

class LobbyDetailView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/lobby/<id>/ — детали лобби.
    PATCH /api/lobby/<id>/ — обновить тренера или комментарий (только создатель, пока статус не BOOKED/PAID).
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = Lobby.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return LobbyPatchSerializer
        return LobbySerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def patch(self, request, *args, **kwargs):
        lobby = self.get_object()
        if lobby.creator != request.user:
            return Response({"detail": "Только создатель лобби может изменить настройки."}, status=403)
        if lobby.status in ['BOOKED', 'PAID']:
            return Response(
                {"detail": "После создания брони нельзя менять тренера или комментарий."},
                status=400,
            )
        return super().patch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# 3. Вступить в лобби (проверка по ELO)
# ---------------------------------------------------------------------------

class LobbyJoinView(APIView):
    """POST /api/lobby/<id>/join/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        lobby = get_object_or_404(Lobby, pk=pk)

        if lobby.status in ['NEGOTIATING', 'READY', 'BOOKED', 'PAID', 'CLOSED']:
            return Response({"detail": "Лобби уже заполнено или закрыто."}, status=400)
        if lobby.current_players_count() >= lobby.max_players():
            return Response({"detail": "Лобби заполнено."}, status=400)
        if LobbyParticipant.objects.filter(lobby=lobby, user=request.user).exists():
            return Response({"detail": "Вы уже в этом лобби."}, status=400)

        # Проверка ELO
        user_elo = request.user.rating_elo
        if not (lobby.elo_min <= user_elo <= lobby.elo_max):
            return Response({
                "detail": f"Ваш ELO ({user_elo}) не входит в диапазон лобби ({lobby.elo_min}–{lobby.elo_max})."
            }, status=400)

        LobbyParticipant.objects.create(lobby=lobby, user=request.user)
        lobby.update_status()
        lobby.refresh_from_db()

        msg = "Вы вступили в лобби."
        if lobby.status == 'NEGOTIATING':
            msg += " Все собрались! Любой участник может предложить время и корт."
            # Уведомляем всех участников что лобби заполнено
            try:
                from notifications.models import send_notification
                for p in lobby.participants.select_related('user').all():
                    send_notification(
                        user=p.user,
                        notification_type='LOBBY',
                        title=f'🎾 Лобби «{lobby.title}» заполнено!',
                        body='Все игроки собрались. Предложите удобное время и корт для игры.',
                        data={'lobby_id': lobby.id, 'lobby_title': lobby.title},
                    )
            except Exception:
                pass  # уведомления не критичны

        return Response({
            "status": msg,
            "lobby_status": lobby.status,
            "players_count": lobby.current_players_count(),
            "max_players": lobby.max_players(),
        })


# ---------------------------------------------------------------------------
# 4. Покинуть лобби
# ---------------------------------------------------------------------------

class LobbyLeaveView(APIView):
    """POST /api/lobby/<id>/leave/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        lobby = get_object_or_404(Lobby, pk=pk)

        if lobby.status in ['BOOKED', 'PAID']:
            return Response({"detail": "Бронь уже создана. Обратитесь к создателю."}, status=400)

        deleted, _ = LobbyParticipant.objects.filter(lobby=lobby, user=request.user).delete()
        if not deleted:
            return Response({"detail": "Вы не в этом лобби."}, status=400)

        if lobby.creator == request.user:
            lobby.status = 'CLOSED'
            lobby.save(update_fields=['status'])
            return Response({"status": "Лобби закрыто, так как создатель вышел."})

        lobby.update_status()
        return Response({"status": "Вы покинули лобби.", "lobby_status": lobby.status})


# ---------------------------------------------------------------------------
# 5. Предложить время и корт
# ---------------------------------------------------------------------------

class LobbyProposeTimeView(APIView):
    """
    GET  /api/lobby/<id>/proposals/     — список всех предложений
    POST /api/lobby/<id>/proposals/     — предложить корт + время
         Тело: { court, scheduled_time, duration_minutes }
    """
    permission_classes = [permissions.IsAuthenticated]

    def _check_participant(self, lobby, user):
        return (
            lobby.participants.filter(user=user).exists()
            or lobby.creator == user
        )

    def get(self, request, pk):
        lobby = get_object_or_404(Lobby, pk=pk)
        if not self._check_participant(lobby, request.user):
            return Response({"detail": "Только участники лобби."}, status=403)
        proposals = lobby.proposals.select_related('court', 'proposed_by').prefetch_related('votes')
        ser = LobbyTimeProposalSerializer(proposals, many=True, context={'request': request})
        return Response(ser.data)

    def post(self, request, pk):
        from bookings.models import Booking
        from courts.models import Court

        lobby = get_object_or_404(Lobby, pk=pk)

        if not self._check_participant(lobby, request.user):
            return Response({"detail": "Только участники лобби могут предлагать время."}, status=403)
        if lobby.status != 'NEGOTIATING':
            return Response({
                "detail": "Предлагать время можно только когда все игроки собрались (статус «Согласование»)."
            }, status=400)

        court_id = request.data.get('court')
        scheduled_time_str = request.data.get('scheduled_time')
        duration_minutes = int(request.data.get('duration_minutes', 90))

        if not court_id:
            return Response({"court": ["Выберите корт."]}, status=400)
        if not scheduled_time_str:
            return Response({"scheduled_time": ["Укажите время."]}, status=400)

        try:
            court = Court.objects.get(pk=court_id)
        except Court.DoesNotExist:
            return Response({"court": ["Корт не найден."]}, status=400)

        # Корт должен соответствовать формату лобби: 1×1 — только ONE_VS_ONE, 2×2 — только TWO_VS_TWO
        if lobby.game_format == 'SINGLE' and court.play_format != Court.PlayFormat.ONE_VS_ONE:
            return Response({
                "court": ["Для лобби 1×1 выберите корт с форматом 1×1 (один на один)."]
            }, status=400)
        if lobby.game_format == 'DOUBLE' and court.play_format != Court.PlayFormat.TWO_VS_TWO:
            return Response({
                "court": ["Для лобби 2×2 выберите корт с форматом 2×2 (двое на двое)."]
            }, status=400)

        # Парсим время
        from django.utils.dateparse import parse_datetime
        scheduled_time = parse_datetime(scheduled_time_str)
        if not scheduled_time:
            return Response({"scheduled_time": ["Неверный формат. Используйте ISO 8601."]}, status=400)

        if scheduled_time < timezone.now():
            return Response({"scheduled_time": ["Нельзя предложить прошедшее время."]}, status=400)

        end_time = scheduled_time + timedelta(minutes=duration_minutes)

        # Проверяем занятость корта
        if Booking.objects.filter(
            court=court,
            status__in=['CONFIRMED', 'PENDING'],
            start_time__lt=end_time,
            end_time__gt=scheduled_time,
        ).exists():
            return Response({
                "scheduled_time": [f"Корт «{court.name}» уже занят в это время."]
            }, status=400)

        proposal = LobbyTimeProposal.objects.create(
            lobby=lobby,
            proposed_by=request.user,
            court=court,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
        )
        # Автоматически — предлагающий голосует «за»
        proposal.votes.add(request.user)

        return Response(
            LobbyTimeProposalSerializer(proposal, context={'request': request}).data,
            status=201
        )


# ---------------------------------------------------------------------------
# 6. Проголосовать за предложение
# ---------------------------------------------------------------------------

class LobbyVoteProposalView(APIView):
    """POST /api/lobby/<id>/proposals/<proposal_id>/vote/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, proposal_id):
        lobby = get_object_or_404(Lobby, pk=pk)
        proposal = get_object_or_404(LobbyTimeProposal, pk=proposal_id, lobby=lobby)

        if not lobby.participants.filter(user=request.user).exists() and lobby.creator != request.user:
            return Response({"detail": "Только участники лобби."}, status=403)
        if lobby.status != 'NEGOTIATING':
            return Response({"detail": "Голосование доступно только когда все игроки собрались."}, status=400)
        if proposal.is_accepted:
            return Response({"detail": "Это предложение уже принято."}, status=400)

        if proposal.votes.filter(pk=request.user.pk).exists():
            proposal.votes.remove(request.user)
            voted = False
        else:
            proposal.votes.add(request.user)
            voted = True

        votes_now = proposal.votes.count()
        max_p = lobby.max_players()

        # Автопринятие — если все проголосовали «за»
        auto_accepted = False
        if voted and votes_now >= max_p:
            with db_transaction.atomic():
                proposal.is_accepted = True
                proposal.save(update_fields=['is_accepted'])
                lobby.court = proposal.court
                lobby.scheduled_time = proposal.scheduled_time
                lobby.duration_minutes = proposal.duration_minutes
                lobby.status = 'READY'
                lobby.save(update_fields=['court', 'scheduled_time', 'duration_minutes', 'status'])
            auto_accepted = True
            # Уведомляем всех: время согласовано
            try:
                from notifications.models import send_notification
                dt_str = proposal.scheduled_time.strftime('%d.%m %H:%M')
                for p in lobby.participants.select_related('user').all():
                    send_notification(
                        user=p.user,
                        notification_type='LOBBY',
                        title=f'✅ Время согласовано в «{lobby.title}»!',
                        body=f'{proposal.court.name} · {dt_str} · {proposal.duration_minutes} мин. Создатель назначит команды.',
                        data={'lobby_id': lobby.id},
                    )
            except Exception:
                pass

        return Response({
            "voted": voted,
            "votes_count": votes_now,
            "max_players": max_p,
            "auto_accepted": auto_accepted,
            "lobby_status": lobby.status,
        })


# ---------------------------------------------------------------------------
# 7. Создатель принимает предложение → фиксирует корт/время
# ---------------------------------------------------------------------------

class LobbyAcceptProposalView(APIView):
    """POST /api/lobby/<id>/proposals/<proposal_id>/accept/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, proposal_id):
        lobby = get_object_or_404(Lobby, pk=pk)
        proposal = get_object_or_404(LobbyTimeProposal, pk=proposal_id, lobby=lobby)

        if lobby.creator != request.user:
            return Response({"detail": "Только создатель лобби может принять предложение."}, status=403)
        if lobby.status != 'NEGOTIATING':
            return Response({
                "detail": "Принять предложение можно только при статусе «Согласование» (когда все собрались)."
            }, status=400)
        if proposal.is_accepted:
            return Response({"detail": "Предложение уже принято."}, status=400)

        with db_transaction.atomic():
            proposal.is_accepted = True
            proposal.save(update_fields=['is_accepted'])
            lobby.court = proposal.court
            lobby.scheduled_time = proposal.scheduled_time
            lobby.duration_minutes = proposal.duration_minutes
            lobby.status = 'READY'
            lobby.save(update_fields=['court', 'scheduled_time', 'duration_minutes', 'status'])

        # Уведомляем всех
        try:
            from notifications.models import send_notification
            dt_str = proposal.scheduled_time.strftime('%d.%m %H:%M')
            for p in lobby.participants.select_related('user').all():
                send_notification(
                    user=p.user,
                    notification_type='LOBBY',
                    title=f'✅ Время согласовано в «{lobby.title}»!',
                    body=f'{proposal.court.name} · {dt_str} · {proposal.duration_minutes} мин. Создатель назначит команды.',
                    data={'lobby_id': lobby.id},
                )
        except Exception:
            pass

        return Response({
            "status": "✅ Предложение принято! Назначьте команды и создайте бронь.",
            "court": proposal.court.name,
            "scheduled_time": proposal.scheduled_time,
            "duration_minutes": proposal.duration_minutes,
            "lobby_status": lobby.status,
        })


# ---------------------------------------------------------------------------
# 8. Назначить команды
# ---------------------------------------------------------------------------

class LobbyAssignTeamsView(APIView):
    """
    POST /api/lobby/<id>/assign-teams/
    { "teams": { "user_id": "A" | "B", ... } }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        lobby = get_object_or_404(Lobby, pk=pk)
        if lobby.creator != request.user:
            return Response({"detail": "Только создатель может назначать команды."}, status=403)
        if lobby.status not in ['READY', 'NEGOTIATING', 'WAITING']:
            return Response({"detail": f"Статус «{lobby.get_status_display()}» не позволяет назначить команды."}, status=400)

        teams_data = request.data.get('teams', {})
        if not teams_data:
            return Response({"detail": "Передайте 'teams': {user_id: 'A'/'B'}."}, status=400)

        participants = {str(p.user_id): p for p in lobby.participants.all()}
        team_a, team_b = [], []

        for uid_str, team in teams_data.items():
            if uid_str not in participants:
                return Response({"detail": f"Пользователь {uid_str} не в лобби."}, status=400)
            if team not in ['A', 'B']:
                return Response({"detail": "Команда должна быть 'A' или 'B'."}, status=400)
            (team_a if team == 'A' else team_b).append(uid_str)

        max_per_team = 1 if lobby.game_format == 'SINGLE' else 2
        if len(team_a) != max_per_team or len(team_b) != max_per_team:
            return Response({
                "detail": f"Нужно по {max_per_team} игрока в каждой команде. "
                          f"A={len(team_a)}, B={len(team_b)}."
            }, status=400)

        with db_transaction.atomic():
            for uid_str, team in teams_data.items():
                p = participants[uid_str]
                p.team = team
                p.save(update_fields=['team'])

        return Response({"status": "Команды назначены.", "team_a": team_a, "team_b": team_b})


# ---------------------------------------------------------------------------
# 9. Создать бронь
# ---------------------------------------------------------------------------

class LobbyBookView(APIView):
    """
    POST /api/lobby/<id>/book/
    Доступно только когда status=READY (время согласовано, команды назначены).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from bookings.models import Booking
        from memberships.models import UserMembership

        lobby = get_object_or_404(Lobby, pk=pk)

        if lobby.creator != request.user:
            return Response({"detail": "Только создатель лобби может создать бронь."}, status=403)
        if lobby.status == 'BOOKED':
            return Response({"detail": "Бронь уже создана.", "booking_id": lobby.booking_id}, status=400)
        if lobby.status in ['PAID', 'CLOSED']:
            return Response({"detail": f"Статус «{lobby.get_status_display()}» не позволяет создать бронь."}, status=400)
        if lobby.status not in ['READY']:
            return Response({
                "detail": "Сначала согласуйте время/корт через предложения, затем примите одно из них."
            }, status=400)
        if not lobby.court or not lobby.scheduled_time:
            return Response({"detail": "Корт и время ещё не согласованы."}, status=400)

        participants = list(lobby.participants.select_related('user').all())

        if any(p.team is None for p in participants):
            return Response({
                "detail": "Сначала назначьте команды всем участникам через /assign-teams/."
            }, status=400)

        court = lobby.court
        start_time = lobby.scheduled_time
        end_time = start_time + timedelta(minutes=lobby.duration_minutes)
        hours = Decimal(str((end_time - start_time).total_seconds() / 3600))

        # Проверка: корт свободен?
        if Booking.objects.filter(
            court=court,
            status__in=['CONFIRMED', 'PENDING'],
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists():
            return Response({
                "detail": "Корт уже занят в это время. Вернитесь к согласованию — выберите другое время."
            }, status=400)

        if start_time < timezone.now():
            return Response({"detail": "Нельзя создать бронь на прошедшее время."}, status=400)

        # Расчёт стоимости корта и тренера, доли каждого
        court_price_per_hour = Decimal(str(court.price_per_hour))
        court_total = court_price_per_hour * hours
        coach_total = Decimal('0')
        if lobby.coach and getattr(lobby.coach, 'price_per_hour', None) is not None:
            coach_total = Decimal(str(lobby.coach.price_per_hour)) * hours
        total_booking = court_total + coach_total
        n = len(participants)
        base_share = (total_booking / n).quantize(Decimal('0.01')) if n else total_booking
        coach_share_per_player = (coach_total / n).quantize(Decimal('0.01')) if n and coach_total else Decimal('0')

        membership_summary = {}
        participant_shares = {}

        for p in participants:
            membership = UserMembership.objects.filter(
                user=p.user,
                is_active=True,
                is_frozen=False,
                end_date__gte=timezone.now(),
                hours_remaining__gte=hours,
                membership_type__service_type__in=['PADEL_HOURS', 'TRAINING_HOURS'],
            ).order_by('end_date').first()

            if membership:
                # Абонемент покрывает корт; доля тренера остаётся
                participant_shares[p.user_id] = {
                    'court_share': coach_share_per_player,
                    'membership_used': True,
                }
                membership_summary[p.user_id] = membership
            else:
                participant_shares[p.user_id] = {
                    'court_share': base_share,
                    'membership_used': False,
                }

        with db_transaction.atomic():
            # Списываем часы абонемента
            for uid, data in participant_shares.items():
                if data['membership_used']:
                    m = membership_summary[uid]
                    m.hours_remaining -= hours
                    if m.hours_remaining <= 0:
                        m.is_active = False
                    m.save(update_fields=['hours_remaining', 'is_active'])

            booking = Booking.objects.create(
                court=court,
                user=request.user,
                start_time=start_time,
                end_time=end_time,
                price=total_booking,
                status='PENDING',
                is_paid=False,
                coach=lobby.coach,
            )

            # Добавляем ВСЕХ участников (включая создателя) для наглядности
            for p in participants:
                booking.participants.add(p.user)

            for p in participants:
                data = participant_shares[p.user_id]
                p.court_share = data['court_share']
                p.membership_used = data['membership_used']
                p.share_amount = data['court_share']
                if data['membership_used']:
                    p.is_paid = True
                    p.paid_at = timezone.now()
                p.save(update_fields=['court_share', 'membership_used', 'share_amount', 'is_paid', 'paid_at'])

            all_by_membership = all(v['membership_used'] for v in participant_shares.values())
            if all_by_membership:
                booking.is_paid = True
                booking.status = 'CONFIRMED'
                booking.save(update_fields=['is_paid', 'status'])
                lobby.status = 'PAID'
            else:
                lobby.status = 'BOOKED'

            lobby.booking = booking
            lobby.save(update_fields=['booking', 'status'])

        result = {
            "status": "✅ Бронь создана!",
            "booking_id": booking.id,
            "booking_status": booking.status,
            "court_total": str(court_total),
            "coach_total": str(coach_total),
            "total": str(total_booking),
            "base_court_share": str(base_share),
            "players": [],
            "note": "Каждый участник добавляет личные услуги (/my-extras/) и оплачивает свою долю (/pay-share/).",
        }
        for p in participants:
            d = participant_shares[p.user_id]
            name = f"{p.user.first_name} {p.user.last_name}".strip() or p.user.username
            result["players"].append({
                "user_id": p.user_id,
                "user_name": name,
                "team": p.team,
                "court_share": str(d['court_share']),
                "membership_used": d['membership_used'],
                "is_paid": d['membership_used'],
            })

        return Response(result)


# ---------------------------------------------------------------------------
# 10. Добавить личные услуги/инвентарь
# ---------------------------------------------------------------------------

class LobbyMyExtrasView(APIView):
    """
    GET    /api/lobby/<id>/my-extras/
    POST   /api/lobby/<id>/my-extras/
    DELETE /api/lobby/<id>/my-extras/<extra_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_participant(self, lobby, user):
        return lobby.participants.filter(user=user).first()

    def get(self, request, pk):
        lobby = get_object_or_404(Lobby, pk=pk)
        p = self._get_participant(lobby, request.user)
        if not p:
            return Response({"detail": "Вы не участник этого лобби."}, status=403)

        extras = p.extras.select_related('service').all()
        data = [
            {
                "id": e.id,
                "service_id": e.service_id,
                "service_name": e.service.name,
                "quantity": e.quantity,
                "price_at_moment": str(e.price_at_moment),
                "subtotal": str(e.subtotal()),
            }
            for e in extras
        ]
        return Response({
            "court_share": str(p.court_share),
            "membership_used": p.membership_used,
            "extras": data,
            "extras_total": str(p.extras_total()),
            "total_to_pay": str(p.court_share + p.extras_total()),
            "is_paid": p.is_paid,
        })

    def post(self, request, pk):
        from inventory.models import Service

        lobby = get_object_or_404(Lobby, pk=pk)

        if lobby.status not in ['BOOKED']:
            return Response({
                "detail": "Добавлять услуги можно только после создания брони (статус BOOKED)."
            }, status=400)

        p = self._get_participant(lobby, request.user)
        if not p:
            return Response({"detail": "Вы не участник этого лобби."}, status=403)
        if p.is_paid:
            return Response({"detail": "Вы уже оплатили — нельзя изменить состав услуг."}, status=400)

        services_data = request.data.get('services', [])
        if not services_data:
            return Response({"detail": "Передайте список услуг: [{service_id, quantity}]."}, status=400)

        added = []
        with db_transaction.atomic():
            for item in services_data:
                sid = item.get('service_id') or item.get('service')
                qty = int(item.get('quantity', 1))
                if not sid:
                    return Response({"detail": "Укажите service_id."}, status=400)
                try:
                    svc = Service.objects.get(id=sid, is_active=True)
                except Service.DoesNotExist:
                    return Response({"detail": f"Услуга ID={sid} не найдена или неактивна."}, status=400)

                extra, created = LobbyParticipantExtra.objects.get_or_create(
                    participant=p, service=svc,
                    defaults={'quantity': qty, 'price_at_moment': svc.price}
                )
                if not created:
                    extra.quantity += qty
                    extra.price_at_moment = svc.price
                    extra.save()

                added.append({
                    "service_id": svc.id,
                    "service_name": svc.name,
                    "quantity": extra.quantity,
                    "subtotal": str(Decimal(str(svc.price)) * extra.quantity),
                })

            p.recalculate_share()

        return Response({
            "status": "Услуги добавлены.",
            "added": added,
            "extras_total": str(p.extras_total()),
            "court_share": str(p.court_share),
            "total_to_pay": str(p.share_amount),
        })

    def delete(self, request, pk, extra_id=None):
        lobby = get_object_or_404(Lobby, pk=pk)
        p = self._get_participant(lobby, request.user)
        if not p:
            return Response({"detail": "Вы не участник этого лобби."}, status=403)
        if p.is_paid:
            return Response({"detail": "Вы уже оплатили."}, status=400)
        if extra_id is None:
            return Response({"detail": "Укажите ID услуги."}, status=400)

        deleted, _ = LobbyParticipantExtra.objects.filter(id=extra_id, participant=p).delete()
        if not deleted:
            return Response({"detail": "Услуга не найдена."}, status=404)

        p.recalculate_share()
        return Response({"status": "Услуга удалена.", "total_to_pay": str(p.share_amount)})


# ---------------------------------------------------------------------------
# 11. Оплатить свою долю
# ---------------------------------------------------------------------------

class LobbyPayShareView(APIView):
    """POST /api/lobby/<id>/pay-share/  { "payment_method": "KASPI"|"CARD"|"CASH" }"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from bookings.models import BookingService
        from payments.service import PaymentService

        lobby = get_object_or_404(Lobby, pk=pk)

        if lobby.status not in ['BOOKED']:
            return Response({"detail": "Оплата доступна только при статусе BOOKED."}, status=400)
        if not lobby.booking:
            return Response({"detail": "Бронь не найдена."}, status=404)

        participant = lobby.participants.filter(user=request.user).first()
        if not participant:
            return Response({"detail": "Вы не участник этого лобби."}, status=403)
        if participant.is_paid:
            return Response({
                "detail": "Вы уже оплатили.",
                "share_amount": str(participant.share_amount),
            })

        payment_method = request.data.get('payment_method', 'KASPI').upper()

        participant.recalculate_share()
        total_to_pay = participant.share_amount or Decimal('0')

        court_name = lobby.court.name if lobby.court else 'корт'
        p_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        team_label = f" (Команда {participant.team})" if participant.team else ""
        dt_str = lobby.scheduled_time.strftime('%d.%m %H:%M') if lobby.scheduled_time else ''
        extras_total = participant.extras_total()

        with db_transaction.atomic():
            # Оплата доли корта через PaymentService
            if not participant.membership_used and participant.court_share > 0:
                result = PaymentService.charge(
                    user=request.user,
                    amount=participant.court_share,
                    description=(
                        f"[ЛОББИ #{lobby.id}] Доля корта — {p_name}{team_label} | "
                        f"{court_name} | {dt_str} | бронь #{lobby.booking_id}"
                    ),
                    payment_method=payment_method,
                    transaction_type='BOOKING',
                    amount_court=participant.court_share,
                    booking=lobby.booking,
                    lobby=lobby,
                )
                if not result.success:
                    return Response({"detail": f"Ошибка оплаты корта: {result.error}"}, status=400)

            # Оплата личных услуг
            if extras_total > 0:
                extras_names = ', '.join(
                    f"{e.service.name}×{e.quantity}"
                    for e in participant.extras.select_related('service').all()
                )
                result = PaymentService.charge(
                    user=request.user,
                    amount=extras_total,
                    description=(
                        f"[ЛОББИ #{lobby.id}] Личные услуги — {p_name}{team_label} | "
                        f"{extras_names} | {court_name} | {dt_str} | бронь #{lobby.booking_id}"
                    ),
                    payment_method=payment_method,
                    transaction_type='BOOKING',
                    amount_services=extras_total,
                    booking=lobby.booking,
                    lobby=lobby,
                )
                if not result.success:
                    return Response({"detail": f"Ошибка оплаты услуг: {result.error}"}, status=400)

                # Копируем услуги в BookingService для истории брони
                for extra in participant.extras.select_related('service').all():
                    BookingService.objects.get_or_create(
                        booking=lobby.booking,
                        service=extra.service,
                        defaults={'quantity': extra.quantity, 'price_at_moment': extra.price_at_moment},
                    )

            participant.is_paid = True
            participant.paid_at = timezone.now()
            participant.save(update_fields=['is_paid', 'paid_at'])

            total_count = lobby.participants.count()
            paid_count = lobby.participants.filter(is_paid=True).count()

            if paid_count >= total_count:
                booking = lobby.booking
                booking.is_paid = True
                booking.status = 'CONFIRMED'
                booking.save(update_fields=['is_paid', 'status'])
                lobby.status = 'PAID'
                lobby.save(update_fields=['status'])
                # Уведомляем всех — бронь подтверждена
                try:
                    from notifications.models import send_notification
                    dt_str = lobby.scheduled_time.strftime('%d.%m %H:%M') if lobby.scheduled_time else ''
                    for lp in lobby.participants.select_related('user').all():
                        send_notification(
                            user=lp.user,
                            notification_type='BOOKING',
                            title=f'🎉 Бронь подтверждена! Лобби «{lobby.title}»',
                            body=f'{court_name} · {dt_str}. Все оплатили. Приходите играть!',
                            data={'lobby_id': lobby.id, 'booking_id': lobby.booking_id},
                        )
                except Exception:
                    pass

        lobby.refresh_from_db()
        all_paid = lobby.status == 'PAID'

        return Response({
            "status": "✅ Ваша доля оплачена!",
            "court_share": str(participant.court_share),
            "membership_used": participant.membership_used,
            "extras_total": str(participant.extras_total()),
            "total_paid": str(total_to_pay),
            "payment_method": payment_method,
            "all_paid": all_paid,
            "booking_confirmed": all_paid,
            "paid_count": lobby.participants.filter(is_paid=True).count(),
            "total_count": total_count,
        })


# ---------------------------------------------------------------------------
# 12. Статус оплат
# ---------------------------------------------------------------------------

class LobbyPaymentStatusView(APIView):
    """GET /api/lobby/<id>/payment-status/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        lobby = get_object_or_404(Lobby, pk=pk)
        is_participant = lobby.participants.filter(user=request.user).exists()
        if not is_participant and lobby.creator != request.user:
            return Response({"detail": "Нет доступа."}, status=403)

        participants = lobby.participants.select_related('user').prefetch_related('extras__service').all()
        data = []
        for p in participants:
            p.recalculate_share()
            name = f"{p.user.first_name} {p.user.last_name}".strip() or p.user.username
            data.append({
                "user_id": p.user.id,
                "user_name": name,
                "team": p.team,
                "court_share": str(p.court_share),
                "membership_used": p.membership_used,
                "extras_total": str(p.extras_total()),
                "total_to_pay": str(p.share_amount or Decimal('0')),
                "extras": [
                    {"service_name": e.service.name, "quantity": e.quantity, "subtotal": str(e.subtotal())}
                    for e in p.extras.all()
                ],
                "is_paid": p.is_paid,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            })

        total = len(data)
        paid = sum(1 for d in data if d['is_paid'])

        return Response({
            "lobby_id": lobby.id,
            "lobby_status": lobby.status,
            "booking_id": lobby.booking_id,
            "court_total": str(lobby.booking.price) if lobby.booking else None,
            "paid_count": paid,
            "total_count": total,
            "all_paid": paid >= total,
            "participants": data,
        })


# ---------------------------------------------------------------------------
# 13. Мои лобби
# ---------------------------------------------------------------------------

class MyLobbiesView(generics.ListAPIView):
    """GET /api/lobby/my/"""
    serializer_class = LobbySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Lobby.objects.filter(
            participants__user=self.request.user
        ).exclude(status='CLOSED').order_by('-created_at')


# ---------------------------------------------------------------------------
# 14. Закрыть лобби
# ---------------------------------------------------------------------------

class LobbyCloseView(APIView):
    """POST /api/lobby/<id>/close/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        lobby = get_object_or_404(Lobby, pk=pk, creator=request.user)
        if lobby.status in ['BOOKED', 'PAID']:
            return Response({"detail": "Бронь уже создана. Отмените бронь отдельно."}, status=400)
        lobby.status = 'CLOSED'
        lobby.save(update_fields=['status'])
        return Response({"status": "Лобби закрыто."})
