from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Max
from django.contrib.auth import get_user_model

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from friends.models import FriendRequest

User = get_user_model()


def _are_friends(user_a, user_b):
    return FriendRequest.objects.filter(
        Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a),
        status='ACCEPTED',
    ).exists()


# ─── Список диалогов ─────────────────────────────────────────────────
class ConversationListView(generics.ListAPIView):
    """
    GET /api/chat/conversations/
    Все диалоги текущего пользователя, отсортированные по последнему сообщению (newest first).
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects
            .filter(Q(user1=user) | Q(user2=user))
            .annotate(last_msg_time=Max('messages__created_at'))
            .order_by('-last_msg_time')
            .select_related('user1', 'user2')
        )


# ─── Начать / получить диалог с другом ───────────────────────────────
class StartConversationView(APIView):
    """
    POST /api/chat/conversations/start/
    Body: { "user_id": 123 }
    Создаёт (или возвращает существующий) диалог с указанным другом.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id обязателен.'}, status=400)

        companion = get_object_or_404(User, pk=user_id)
        if companion == request.user:
            return Response({'detail': 'Нельзя начать диалог с самим собой.'}, status=400)

        if not _are_friends(request.user, companion):
            return Response({'detail': 'Можно переписываться только с друзьями.'}, status=403)

        conv = Conversation.get_or_create_for_users(request.user, companion)
        data = ConversationSerializer(conv, context={'request': request}).data
        return Response(data, status=status.HTTP_200_OK)


# ─── Сообщения в диалоге ─────────────────────────────────────────────
class MessageListView(generics.ListAPIView):
    """
    GET /api/chat/conversations/<conv_id>/messages/
    Query-параметры для быстрого polling:
      ?after=<message_id>   — только сообщения новее (id > after)
      ?limit=50             — количество (по умолчанию 50, макс 200)
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        conv = get_object_or_404(
            Conversation.objects.filter(Q(user1=user) | Q(user2=user)),
            pk=self.kwargs['conv_id'],
        )
        qs = conv.messages.select_related('sender')

        after = self.request.query_params.get('after')
        if after:
            qs = qs.filter(id__gt=int(after))

        limit = min(int(self.request.query_params.get('limit', 50)), 200)
        return qs.order_by('created_at')[:limit]


# ─── Отправить сообщение ─────────────────────────────────────────────
class SendMessageView(APIView):
    """
    POST /api/chat/conversations/<conv_id>/messages/
    Body: { "text": "Привет!" }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conv_id):
        user = request.user
        conv = get_object_or_404(
            Conversation.objects.filter(Q(user1=user) | Q(user2=user)),
            pk=conv_id,
        )
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'detail': 'Текст сообщения не может быть пустым.'}, status=400)
        if len(text) > 4000:
            return Response({'detail': 'Максимальная длина — 4000 символов.'}, status=400)

        msg = Message.objects.create(conversation=conv, sender=user, text=text)
        conv.save(update_fields=['updated_at'])

        data = MessageSerializer(msg).data
        return Response(data, status=status.HTTP_201_CREATED)


# ─── Пометить прочитанными ───────────────────────────────────────────
class MarkReadView(APIView):
    """
    POST /api/chat/conversations/<conv_id>/read/
    Помечает все непрочитанные сообщения собеседника в этом диалоге как прочитанные.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conv_id):
        user = request.user
        conv = get_object_or_404(
            Conversation.objects.filter(Q(user1=user) | Q(user2=user)),
            pk=conv_id,
        )
        updated = conv.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
        return Response({'marked_read': updated})


# ─── Общий счётчик непрочитанных ─────────────────────────────────────
class UnreadCountView(APIView):
    """
    GET /api/chat/unread-count/
    Возвращает общее количество непрочитанных сообщений по всем диалогам.
    Полезно для бейджа на иконке чата.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        count = Message.objects.filter(
            conversation__in=Conversation.objects.filter(Q(user1=user) | Q(user2=user)),
            is_read=False,
        ).exclude(sender=user).count()
        return Response({'unread_count': count})
