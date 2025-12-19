from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Match
from .serializers import MatchSerializer
from django.db import transaction

class MatchCreateView(generics.CreateAPIView):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    # Только авторизованные (в идеале - только тренеры)
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # 1. Сохраняем матч. Судья - текущий пользователь.
        match = serializer.save(judge=self.request.user)
        
        # 2. Запускаем пересчет рейтинга
        self.update_ratings(match)

    def update_ratings(self, match):
        """
        Простая логика ELO:
        Победитель +25
        Проигравший -25
        """
        if match.is_rated:
            return

        RATING_CHANGE = 25

        # Определяем списки победителей и проигравших
        if match.winner_team == 'A':
            winners = match.team_a.all()
            losers = match.team_b.all()
        elif match.winner_team == 'B':
            winners = match.team_b.all()
            losers = match.team_a.all()
        else:
            # Если ничья - рейтинг не меняем (или можно сделать другую логику)
            return

        # Используем транзакцию, чтобы всё сохранилось одновременно
        with transaction.atomic():
            # Начисляем победителям
            for player in winners:
                player.rating_elo += RATING_CHANGE
                player.save()
            
            # Отнимаем у проигравших
            for player in losers:
                # Рейтинг не может упасть ниже 0 (опционально)
                player.rating_elo = max(0, player.rating_elo - RATING_CHANGE)
                player.save()

            # Ставим отметку, что рейтинг начислен
            match.is_rated = True
            match.save()