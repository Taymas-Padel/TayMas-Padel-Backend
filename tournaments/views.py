from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from users.permissions import IsAdminRole, IsReceptionist
from finance.models import Transaction
from .models import Tournament, TournamentTeam, TournamentMatch
from .serializers import (
    TournamentListSerializer,
    TournamentDetailSerializer,
    TournamentCreateSerializer,
    TournamentStatusSerializer,
    TournamentTeamDetailSerializer,
    TournamentTeamBriefSerializer,
    RegisterTeamSerializer,
    UpdateTeamStatusSerializer,
    ConfirmPaymentSerializer,
    TournamentMatchSerializer,
    UpdateMatchSerializer,
    BracketSerializer,
)
from .utils import generate_bracket, set_match_result, validate_match_schedule


# ────────────────────────────────────────────────────────────
# 1. TOURNAMENTS LIST / CREATE
# ────────────────────────────────────────────────────────────

class TournamentListView(generics.ListAPIView):
    """
    GET /api/tournaments/
    Список турниров.
    Фильтры: ?status=REGISTRATION&format=DOUBLES
    """
    serializer_class = TournamentListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Tournament.objects.all()
        s = self.request.query_params.get('status')
        if s:
            qs = qs.filter(status=s.upper())
        fmt = self.request.query_params.get('format')
        if fmt:
            qs = qs.filter(format=fmt.upper())
        return qs


class TournamentCreateView(generics.CreateAPIView):
    """POST /api/tournaments/manage/ — создать турнир (ADMIN)."""
    serializer_class = TournamentCreateSerializer
    permission_classes = [IsAdminRole]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TournamentManageListView(generics.ListAPIView):
    """GET /api/tournaments/manage/ — все турниры (ADMIN/RECEPTIONIST)."""
    serializer_class = TournamentListSerializer
    permission_classes = [IsReceptionist]

    def get_queryset(self):
        qs = Tournament.objects.all()
        s = self.request.query_params.get('status')
        if s:
            qs = qs.filter(status=s.upper())
        return qs


# ────────────────────────────────────────────────────────────
# 2. TOURNAMENT DETAIL / UPDATE
# ────────────────────────────────────────────────────────────

class TournamentDetailView(generics.RetrieveAPIView):
    """GET /api/tournaments/<id>/"""
    queryset = Tournament.objects.all()
    serializer_class = TournamentDetailSerializer
    permission_classes = [permissions.AllowAny]


class TournamentUpdateView(generics.UpdateAPIView):
    """PATCH /api/tournaments/manage/<id>/"""
    queryset = Tournament.objects.all()
    serializer_class = TournamentCreateSerializer
    permission_classes = [IsAdminRole]
    http_method_names = ['patch']

    def update(self, request, *args, **kwargs):
        tournament = self.get_object()
        if tournament.status not in [Tournament.Status.DRAFT]:
            # Allow updating description/prize_info even in REGISTRATION
            allowed_fields = {'description', 'prize_info', 'registration_deadline', 'name'}
            invalid = set(request.data.keys()) - allowed_fields
            if invalid and tournament.status != Tournament.Status.DRAFT:
                return Response(
                    {'detail': f'В статусе "{tournament.get_status_display()}" нельзя изменять: {", ".join(invalid)}.'},
                    status=400,
                )
        return super().update(request, *args, **kwargs)


# ────────────────────────────────────────────────────────────
# 3. STATUS CHANGE
# ────────────────────────────────────────────────────────────

class TournamentStatusView(APIView):
    """
    POST /api/tournaments/manage/<id>/status/
    Body: { "status": "REGISTRATION" }
    """
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        serializer = TournamentStatusSerializer(
            data=request.data, context={'tournament': tournament}
        )
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        tournament.status = new_status
        tournament.save(update_fields=['status', 'updated_at'])
        return Response({
            'id': tournament.id,
            'status': tournament.status,
            'status_display': tournament.get_status_display(),
        })


# ────────────────────────────────────────────────────────────
# 4. TEAMS
# ────────────────────────────────────────────────────────────

class TournamentTeamsView(APIView):
    """
    GET  /api/tournaments/<id>/teams/   — список команд (любой аутентифицированный)
    POST /api/tournaments/<id>/teams/   — зарегистрироваться (аутентифицированный)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        teams = tournament.teams.select_related(
            'player1', 'player2', 'paid_by'
        ).order_by('seed', 'registered_at')
        return Response(TournamentTeamDetailSerializer(teams, many=True).data)

    def post(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        if tournament.status != Tournament.Status.REGISTRATION:
            return Response(
                {'detail': 'Регистрация на этот турнир закрыта.'},
                status=400,
            )
        serializer = RegisterTeamSerializer(
            data=request.data, context={'tournament': tournament}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from django.contrib.auth import get_user_model
        User = get_user_model()
        p1 = get_object_or_404(User, pk=data['player1_id'])
        p2 = User.objects.filter(pk=data.get('player2_id')).first() if data.get('player2_id') else None

        team = TournamentTeam.objects.create(
            tournament=tournament,
            player1=p1,
            player2=p2,
            team_name=data.get('team_name', ''),
        )
        return Response(TournamentTeamDetailSerializer(team).data, status=201)


class TournamentTeamDetailView(APIView):
    """
    GET   /api/tournaments/<tid>/teams/<team_id>/
    PATCH /api/tournaments/<tid>/teams/<team_id>/  — обновить статус (RECEPTIONIST)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsReceptionist()]

    def _get_team(self, tid, team_id):
        return get_object_or_404(TournamentTeam, pk=team_id, tournament_id=tid)

    def get(self, request, tid, team_id):
        team = self._get_team(tid, team_id)
        return Response(TournamentTeamDetailSerializer(team).data)

    def patch(self, request, tid, team_id):
        team = self._get_team(tid, team_id)
        serializer = UpdateTeamStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        now = timezone.now()
        if new_status == TournamentTeam.Status.CONFIRMED and team.status == TournamentTeam.Status.PENDING:
            team.confirmed_at = now
        if notes:
            team.notes = notes
        team.status = new_status
        team.save()
        return Response(TournamentTeamDetailSerializer(team).data)


class ConfirmTeamPaymentView(APIView):
    """
    POST /api/tournaments/<tid>/teams/<team_id>/confirm-payment/
    Body: { "payment_method": "CASH" }
    """
    permission_classes = [IsReceptionist]

    def post(self, request, tid, team_id):
        team = get_object_or_404(TournamentTeam, pk=team_id, tournament_id=tid)
        tournament = team.tournament

        if not tournament.is_paid:
            return Response({'detail': 'Турнир бесплатный, оплата не требуется.'}, status=400)
        if team.status == TournamentTeam.Status.PAID:
            return Response({'detail': 'Оплата уже подтверждена.'}, status=400)
        if team.status == TournamentTeam.Status.WITHDRAWN:
            return Response({'detail': 'Нельзя подтвердить оплату снятой команды.'}, status=400)

        serializer = ConfirmPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team.status = TournamentTeam.Status.PAID
        team.paid_at = timezone.now()
        team.paid_by = request.user
        team.payment_method = serializer.validated_data['payment_method']
        team.save()

        Transaction.objects.create(
            user=team.player1,
            amount=tournament.entry_fee,
            transaction_type=Transaction.TransactionType.TOURNAMENT_FEE,
            payment_method=team.payment_method,
            tournament_team=team,
            description=f"Взнос за турнир «{tournament.name}» — команда {team.display_name}",
        )

        return Response(TournamentTeamDetailSerializer(team).data)


class RefundTeamPaymentView(APIView):
    """
    POST /api/tournaments/<tid>/teams/<team_id>/refund/
    Отметить возврат взноса.
    """
    permission_classes = [IsReceptionist]

    def post(self, request, tid, team_id):
        team = get_object_or_404(TournamentTeam, pk=team_id, tournament_id=tid)
        if team.status not in [TournamentTeam.Status.PAID, TournamentTeam.Status.WITHDRAWN]:
            return Response({'detail': 'Возврат возможен только для оплаченных или снятых команд.'}, status=400)
        team.status = TournamentTeam.Status.REFUNDED
        team.save(update_fields=['status'])
        return Response({'detail': 'Возврат отмечен.', 'team_id': team.id})


# ────────────────────────────────────────────────────────────
# 5. BRACKET
# ────────────────────────────────────────────────────────────

class TournamentBracketView(APIView):
    """GET /api/tournaments/<id>/bracket/"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        return Response(BracketSerializer().to_representation(tournament))


class GenerateBracketView(APIView):
    """
    POST /api/tournaments/manage/<id>/generate-bracket/
    Генерирует (или перегенерирует) сетку. Только ADMIN.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        if tournament.status not in [Tournament.Status.REGISTRATION, Tournament.Status.IN_PROGRESS]:
            return Response(
                {'detail': 'Сетку можно генерировать только когда открыта регистрация или турнир идёт.'},
                status=400,
            )
        try:
            matches = generate_bracket(tournament)
        except ValueError as e:
            return Response({'detail': str(e)}, status=400)

        return Response({
            'detail': f'Сетка сгенерирована: {len(matches)} матчей.',
            'bracket': BracketSerializer().to_representation(tournament),
        })


# ────────────────────────────────────────────────────────────
# 6. MATCHES
# ────────────────────────────────────────────────────────────

class TournamentMatchesView(generics.ListAPIView):
    """
    GET /api/tournaments/<id>/matches/
    Фильтры: ?date=2026-04-01&court_id=1&status=SCHEDULED
    """
    serializer_class = TournamentMatchSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        tournament = get_object_or_404(Tournament, pk=self.kwargs['pk'])
        qs = tournament.matches.select_related('team1', 'team2', 'winner', 'court')

        date_str = self.request.query_params.get('date')
        if date_str:
            qs = qs.filter(scheduled_at__date=date_str)

        court_id = self.request.query_params.get('court_id')
        if court_id:
            qs = qs.filter(court_id=court_id)

        status_f = self.request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f.upper())

        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        tournament = get_object_or_404(Tournament, pk=self.kwargs['pk'])
        agg = tournament.matches.aggregate(
            m=__import__('django.db.models', fromlist=['Max']).Max('round_number')
        )
        ctx['total_rounds'] = agg['m'] or 1
        return ctx


class TournamentMatchDetailView(APIView):
    """
    GET   /api/tournaments/<tid>/matches/<match_id>/
    PATCH /api/tournaments/<tid>/matches/<match_id>/ — назначить время, корт, результат (RECEPTIONIST)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsReceptionist()]

    def _get_match(self, tid, match_id):
        return get_object_or_404(TournamentMatch, pk=match_id, tournament_id=tid)

    def get(self, request, tid, match_id):
        match = self._get_match(tid, match_id)
        return Response(TournamentMatchSerializer(match).data)

    def patch(self, request, tid, match_id):
        match = self._get_match(tid, match_id)
        serializer = UpdateMatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        court = data.get('court', match.court)
        scheduled_at = data.get('scheduled_at', match.scheduled_at)

        # Validate schedule conflicts
        if court or scheduled_at:
            errors = validate_match_schedule(
                match, court, scheduled_at, exclude_match_id=match.pk
            )
            if errors:
                return Response({'detail': errors[0]}, status=400)

        # Apply fields
        for field in ['scheduled_at', 'court', 'status', 'score_team1', 'score_team2', 'notes']:
            if field in data:
                setattr(match, field, data[field])

        # Set result
        if 'winner' in data and data['winner']:
            try:
                match = set_match_result(
                    match,
                    winner_team=data['winner'],
                    score_team1=data.get('score_team1', match.score_team1),
                    score_team2=data.get('score_team2', match.score_team2),
                )
            except ValueError as e:
                return Response({'detail': str(e)}, status=400)
        else:
            match.save()

        return Response(TournamentMatchSerializer(match).data)


# ────────────────────────────────────────────────────────────
# 7. MY MATCHES (mobile — player's own matches)
# ────────────────────────────────────────────────────────────

class MyTournamentMatchesView(APIView):
    """
    GET /api/tournaments/<id>/my-matches/
    Матчи текущего пользователя в этом турнире.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        user = request.user
        # Find teams the user belongs to
        user_teams = TournamentTeam.objects.filter(
            tournament=tournament,
        ).filter(Q(player1=user) | Q(player2=user))

        matches = TournamentMatch.objects.filter(
            tournament=tournament,
        ).filter(
            Q(team1__in=user_teams) | Q(team2__in=user_teams)
        ).select_related('team1', 'team2', 'winner', 'court').order_by('round_number', 'match_number')

        agg = tournament.matches.aggregate(
            m=__import__('django.db.models', fromlist=['Max']).Max('round_number')
        )
        total_rounds = agg['m'] or 1

        return Response(TournamentMatchSerializer(
            matches, many=True, context={'total_rounds': total_rounds, 'request': request}
        ).data)


# ────────────────────────────────────────────────────────────
# 8. TOURNAMENT REPORT (CRM)
# ────────────────────────────────────────────────────────────

class TournamentReportView(APIView):
    """GET /api/tournaments/manage/<id>/report/"""
    permission_classes = [IsReceptionist]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        teams = tournament.teams.select_related('player1', 'player2', 'paid_by')

        revenue = sum(
            tournament.entry_fee
            for t in teams if t.status == TournamentTeam.Status.PAID
        )

        # Find winner (team that won the final match)
        final_match = tournament.matches.filter(
            status=TournamentMatch.Status.COMPLETED
        ).order_by('-round_number').first()
        winner = None
        if final_match and final_match.winner:
            winner = TournamentTeamBriefSerializer(final_match.winner).data

        team_stats = []
        for t in teams:
            matches_played = TournamentMatch.objects.filter(
                tournament=tournament, status=TournamentMatch.Status.COMPLETED
            ).filter(Q(team1=t) | Q(team2=t)).count()
            team_stats.append({
                'team': TournamentTeamDetailSerializer(t).data,
                'matches_played': matches_played,
                'won': TournamentMatch.objects.filter(tournament=tournament, winner=t).count(),
            })

        return Response({
            'tournament': TournamentDetailSerializer(tournament).data,
            'total_teams': teams.count(),
            'paid_teams': teams.filter(status=TournamentTeam.Status.PAID).count(),
            'withdrawn_teams': teams.filter(status=TournamentTeam.Status.WITHDRAWN).count(),
            'revenue': float(revenue),
            'winner': winner,
            'teams': team_stats,
        })
