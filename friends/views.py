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