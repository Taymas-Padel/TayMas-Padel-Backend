from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import Match
from .serializers import MatchSerializer, LeaderboardEntrySerializer
from users.permissions import IsCoach, IsAdminRole

User = get_user_model()


class MatchCreateView(generics.CreateAPIView):
    """POST /api/gamification/matches/create/ — создать матч. Только тренер или ADMIN."""
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsCoach]

    def perform_create(self, serializer):
        match = serializer.save(judge=self.request.user)
        self._update_ratings(match)

    def _update_ratings(self, match):
        if match.is_rated:
            return

        RATING_CHANGE = 25

        if match.winner_team == 'A':
            winners = match.team_a.all()
            losers = match.team_b.all()
        elif match.winner_team == 'B':
            winners = match.team_b.all()
            losers = match.team_a.all()
        else:
            # Ничья — рейтинг не меняем
            match.is_rated = True
            match.save(update_fields=['is_rated'])
            return

        elo_changes = {}
        with transaction.atomic():
            for player in winners:
                player.rating_elo += RATING_CHANGE
                player.save(update_fields=['rating_elo'])
                elo_changes[str(player.id)] = +RATING_CHANGE
            for player in losers:
                old = player.rating_elo
                player.rating_elo = max(0, old - RATING_CHANGE)
                player.save(update_fields=['rating_elo'])
                elo_changes[str(player.id)] = -(old - player.rating_elo)
            match.is_rated = True
            match.elo_changes = elo_changes
            match.save(update_fields=['is_rated', 'elo_changes'])


class MatchListView(generics.ListAPIView):
    """GET /api/gamification/matches/ — история матчей (мои или все)."""
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        show_all = self.request.query_params.get('all')
        if show_all and user.role in ['ADMIN', 'RECEPTIONIST', 'COACH_PADEL', 'COACH_FITNESS']:
            return Match.objects.all().order_by('-date')
        return Match.objects.filter(
            Q(team_a=user) | Q(team_b=user)
        ).distinct().order_by('-date')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx


class LeaderboardView(generics.ListAPIView):
    """GET /api/gamification/leaderboard/ — топ игроков по ELO рейтингу."""
    serializer_class = LeaderboardEntrySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        limit = min(int(self.request.query_params.get('limit', 50)), 100)
        return User.objects.filter(
            role__in=['CLIENT', 'COACH_PADEL']
        ).order_by('-rating_elo')[:limit]
