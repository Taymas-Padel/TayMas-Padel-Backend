from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import FriendRequest
from .serializers import (
    FriendRequestSerializer,
    UserShortSerializer,
    FriendRequestActionSerializer,
)
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q

User = get_user_model()


# 1. Отправить заявку
class SendFriendRequestView(generics.CreateAPIView):
    """POST /api/friends/send/ — отправить заявку"""
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


# 2. Входящие заявки
class IncomingRequestsView(generics.ListAPIView):
    """GET /api/friends/requests/ — кто хочет добавить меня"""
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(
            to_user=self.request.user, status='PENDING'
        ).select_related('from_user', 'to_user')


# 3. Исходящие заявки (НОВОЕ)
class OutgoingRequestsView(generics.ListAPIView):
    """GET /api/friends/requests/outgoing/ — кому я отправил"""
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(
            from_user=self.request.user, status='PENDING'
        ).select_related('from_user', 'to_user')


# 4. Принять / Отклонить
class RespondToRequestView(APIView):
    """POST /api/friends/respond/"""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(request_body=FriendRequestActionSerializer)
    def post(self, request):
        serializer = FriendRequestActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        request_id = serializer.validated_data['request_id']
        action = serializer.validated_data['action']

        try:
            fr = FriendRequest.objects.get(
                id=request_id, to_user=request.user, status='PENDING'
            )
        except FriendRequest.DoesNotExist:
            return Response({"error": "Заявка не найдена"}, status=404)

        if action == 'accept':
            fr.status = 'ACCEPTED'
            fr.save()
            return Response({"message": "Теперь вы друзья!"})
        elif action == 'reject':
            fr.status = 'REJECTED'
            fr.save()
            return Response({"message": "Заявка отклонена"})

        return Response({"error": "Неверное действие"}, status=400)


# 5. Отменить свою заявку (НОВОЕ)
class CancelFriendRequestView(APIView):
    """POST /api/friends/cancel/ — отозвать заявку"""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT, required=['request_id'],
        properties={'request_id': openapi.Schema(type=openapi.TYPE_INTEGER)}
    ))
    def post(self, request):
        request_id = request.data.get('request_id')
        if not request_id:
            return Response({"error": "Укажите request_id"}, status=400)
        try:
            fr = FriendRequest.objects.get(
                id=request_id, from_user=request.user, status='PENDING'
            )
        except FriendRequest.DoesNotExist:
            return Response({"error": "Заявка не найдена"}, status=404)
        fr.delete()
        return Response({"message": "Заявка отменена"})


# 6. Удалить из друзей (НОВОЕ)
class RemoveFriendView(APIView):
    """POST /api/friends/remove/ — удалить из друзей"""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT, required=['user_id'],
        properties={'user_id': openapi.Schema(type=openapi.TYPE_INTEGER)}
    ))
    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "Укажите user_id"}, status=400)

        me = request.user
        fr = FriendRequest.objects.filter(
            from_user=me, to_user_id=user_id, status='ACCEPTED'
        ).first() or FriendRequest.objects.filter(
            from_user_id=user_id, to_user=me, status='ACCEPTED'
        ).first()

        if not fr:
            return Response({"error": "Вы не друзья"}, status=404)
        fr.delete()
        return Response({"message": "Удалён из друзей"})


# 7. Список друзей
class FriendListView(generics.ListAPIView):
    """GET /api/friends/ — мои друзья"""
    serializer_class = UserShortSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        me = self.request.user
        sent = FriendRequest.objects.filter(
            from_user=me, status='ACCEPTED'
        ).values_list('to_user_id', flat=True)
        received = FriendRequest.objects.filter(
            to_user=me, status='ACCEPTED'
        ).values_list('from_user_id', flat=True)
        return User.objects.filter(id__in=list(sent) + list(received))


# 8. Лента активности друзей
class FriendActivityFeedView(APIView):
    """
    GET /api/friends/feed/?limit=20
    Хронологическая лента активности друзей:
    - завершённые матчи друзей
    - получение ELO изменений
    Каждый элемент: { type, user_id, user_name, description, date, data }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from gamification.models import Match
        from bookings.models import Booking

        me = request.user
        limit = int(request.query_params.get('limit', 20))

        sent = FriendRequest.objects.filter(
            from_user=me, status='ACCEPTED'
        ).values_list('to_user_id', flat=True)
        received = FriendRequest.objects.filter(
            to_user=me, status='ACCEPTED'
        ).values_list('from_user_id', flat=True)
        friend_ids = list(set(list(sent) + list(received)))

        if not friend_ids:
            return Response([])

        feed = []

        # Матчи друзей (последние 30 дней)
        from django.utils import timezone
        from datetime import timedelta
        since = timezone.now() - timedelta(days=30)

        matches = Match.objects.filter(
            Q(team_a__in=friend_ids) | Q(team_b__in=friend_ids),
            date__gte=since,
        ).distinct().order_by('-date')[:30]

        friends_map = {u.id: u for u in User.objects.filter(id__in=friend_ids)}

        for m in matches:
            # Какие друзья участвовали
            a_ids = set(m.team_a.values_list('id', flat=True))
            b_ids = set(m.team_b.values_list('id', flat=True))
            involved = [friends_map[uid] for uid in friend_ids if uid in a_ids | b_ids]
            for player in involved:
                elo_change = m.elo_changes.get(str(player.id))
                elo_txt = f" ELO: {'+' if elo_change and elo_change > 0 else ''}{elo_change}" if elo_change is not None else ""
                winner_side = 'A' if player.id in a_ids else 'B'
                won = m.winner_team == winner_side
                feed.append({
                    "type": "MATCH",
                    "user_id": player.id,
                    "user_name": f"{player.first_name} {player.last_name}".strip() or player.username,
                    "description": f"{'🏆 Победил' if won else '❌ Проиграл'} матч {m.score or ''}{elo_txt}",
                    "date": m.date.isoformat(),
                    "data": {"match_id": m.id, "score": m.score, "won": won, "elo_change": elo_change},
                })

        # Сортируем по дате
        feed.sort(key=lambda x: x['date'], reverse=True)
        return Response(feed[:limit])