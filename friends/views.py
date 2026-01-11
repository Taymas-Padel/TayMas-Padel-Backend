from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from .models import FriendRequest
from .serializers import FriendRequestSerializer, UserShortSerializer
from django.contrib.auth import get_user_model
from .serializers import FriendRequestActionSerializer # Импортируем
from drf_yasg.utils import swagger_auto_schema
User = get_user_model()

class SendFriendRequestView(generics.CreateAPIView):
    """Отправить заявку в друзья"""
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

class IncomingRequestsView(generics.ListAPIView):
    """Список входящих заявок (кто хочет меня добавить)"""
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(to_user=self.request.user, status='PENDING')

class ManageRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    # Это подскажет Swagger'у, какое поле рисовать
    @swagger_auto_schema(request_body=FriendRequestActionSerializer) 
    def post(self, request, pk):
        action = request.data.get('action') # 'accept' или 'reject'
        
        try:
            friend_request = FriendRequest.objects.get(id=pk, to_user=request.user, status='PENDING')
        except FriendRequest.DoesNotExist:
            return Response({"error": "Заявка не найдена"}, status=404)

        if action == 'accept':
            friend_request.status = 'ACCEPTED'
            friend_request.save()
            return Response({"message": "Теперь вы друзья!"})
        
        elif action == 'reject':
            friend_request.status = 'REJECTED'
            friend_request.save()
            return Response({"message": "Заявка отклонена"})
        
        return Response({"error": "Неверное действие"}, status=400)

class MyFriendsListView(generics.ListAPIView):
    """
    Самое главное: Список моих друзей.
    Возвращает список User-объектов.
    """
    serializer_class = UserShortSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Ищем все записи, где статус ACCEPTED и юзер участвует с любой стороны
        
        # 1. Те, кого добавил Я
        sent_accepted = FriendRequest.objects.filter(from_user=user, status='ACCEPTED').values_list('to_user_id', flat=True)
        
        # 2. Те, кто добавил МЕНЯ
        received_accepted = FriendRequest.objects.filter(to_user=user, status='ACCEPTED').values_list('from_user_id', flat=True)
        
        # Объединяем ID всех друзей
        all_friend_ids = list(sent_accepted) + list(received_accepted)
        
        return User.objects.filter(id__in=all_friend_ids)