import logging

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Max, Count, OuterRef, Subquery
from django.contrib.auth import get_user_model

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from friends.models import FriendRequest
from notifications.models import send_notification

User = get_user_model()
logger = logging.getLogger(__name__)


def _are_friends(user_a, user_b):
    return FriendRequest.objects.filter(
        Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a),
        status='ACCEPTED',
    ).exists()


# ─── Список диалогов ─────────────────────────────────────────────────
class ConversationListView(generics.ListAPIView):
    """
    GET /api/chat/conversations/
    Все диалоги текущего пользователя, отсортированные по последнему сообщению.
    TAY-10: N+1 fix — last_message и unread_count вычисляются через аннотации (без доп. запросов).
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Subquery для полей последнего сообщения
        last_msg = Message.objects.filter(
            conversation=OuterRef('pk')
        ).order_by('-created_at')

        return (
            Conversation.objects
            .filter(Q(user1=user) | Q(user2=user))
            .select_related('user1', 'user2')
            .annotate(
                last_msg_time=Max('messages__created_at'),
                last_msg_id=Subquery(last_msg.values('id')[:1]),
                last_msg_text=Subquery(last_msg.values('text')[:1]),
                last_msg_sender_id=Subquery(last_msg.values('sender_id')[:1]),
                last_msg_created_at=Subquery(last_msg.values('created_at')[:1]),
                last_msg_is_read=Subquery(last_msg.values('is_read')[:1]),
                last_msg_status=Subquery(last_msg.values('status')[:1]),
                # Count с фильтром = O(1) запрос вместо N
                unread_count_annotated=Count(
                    'messages',
                    filter=Q(messages__is_read=False) & ~Q(messages__sender_id=user.id),
                    distinct=True,
                ),
            )
            .order_by('-last_msg_time')
        )


# ─── Начать / получить диалог с другом ───────────────────────────────
class StartConversationView(APIView):
    """
    POST /api/chat/conversations/start/
    Body: { "user_id": 123 }
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


# ─── История сообщений + отправка (на одном URL) ─────────────────────
class MessageListView(APIView):
    """
    GET  /api/chat/conversations/<conv_id>/messages/   — история (cursor pagination)
    POST /api/chat/conversations/<conv_id>/messages/   — отправить сообщение

    TAY-13 — GET cursor pagination:
      ?before_id=<id>  — сообщения СТАРШЕ этого ID (скролл вверх)
      ?after_id=<id>   — сообщения НОВЕЕ этого ID (resync)
      ?limit=50        — количество (макс 200)
      ?after=<id>      — legacy алиас для after_id

    TAY-9 — POST idempotency:
      client_message_id в теле — повторная отправка вернёт оригинал (200), не дубликат.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_conversation(self, user, conv_id):
        return get_object_or_404(
            Conversation.objects.filter(Q(user1=user) | Q(user2=user)),
            pk=conv_id,
        )

    def get(self, request, conv_id):
        conv = self._get_conversation(request.user, conv_id)
        qs = conv.messages.select_related('sender')

        before_id = request.query_params.get('before_id')
        after_id = request.query_params.get('after_id')
        after_legacy = request.query_params.get('after')

        if before_id and before_id.isdigit():
            qs = qs.filter(id__lt=int(before_id))
        if after_id and after_id.isdigit():
            qs = qs.filter(id__gt=int(after_id))
        elif after_legacy and after_legacy.isdigit():
            qs = qs.filter(id__gt=int(after_legacy))

        limit = min(int(request.query_params.get('limit', 50) or 50), 200)
        messages = qs.order_by('created_at')[:limit]
        return Response(MessageSerializer(messages, many=True).data)

    def post(self, request, conv_id):
        """
        POST /api/chat/conversations/<conv_id>/messages/
        Body: { "text": "Привет!", "client_message_id": "uuid" }
        """
        user = request.user
        conv = self._get_conversation(user, conv_id)

        text = (request.data.get('text') or '').strip()
        client_message_id = request.data.get('client_message_id') or None

        if not text:
            return Response({'detail': 'Текст сообщения не может быть пустым.'}, status=400)
        if len(text) > 4000:
            return Response({'detail': 'Максимальная длина — 4000 символов.'}, status=400)

        # TAY-9: Idempotency check
        if client_message_id:
            existing = Message.objects.filter(
                conversation=conv, sender=user, client_message_id=client_message_id,
            ).first()
            if existing:
                logger.info(
                    "chat.rest.idempotent_hit conv=%s sender=%s cmid=%s msg=%s",
                    conv.id, user.id, client_message_id, existing.id,
                )
                return Response(MessageSerializer(existing).data, status=status.HTTP_200_OK)

        msg = Message.objects.create(
            conversation=conv,
            sender=user,
            text=text,
            client_message_id=client_message_id,
            status=Message.Status.SENT,
        )
        conv.save(update_fields=['updated_at'])

        recipient = conv.user2 if conv.user1_id == user.id else conv.user1
        sender_name = f'{user.first_name} {user.last_name}'.strip() or user.phone_number or user.username
        preview = text[:80] + ('…' if len(text) > 80 else '')
        send_notification(
            user=recipient,
            notification_type='MESSAGE',
            title=f'Сообщение от {sender_name}',
            body=preview,
            data={'conversation_id': conv.id, 'message_id': msg.id, 'sender_id': user.id},
        )

        logger.info("chat.rest.message_sent conv=%s sender=%s msg=%s", conv.id, user.id, msg.id)
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class SendMessageView(MessageListView):
    """
    POST /conversations/<id>/send/ — алиас отправки (совместимость с app.html и старыми клиентами).
    История только через GET .../messages/.
    """

    def get(self, request, conv_id):
        return Response(
            {
                'detail': 'Для истории используйте GET /api/chat/conversations/<id>/messages/. '
                'Отправка: POST /messages/ или POST /send/.',
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# ─── Пометить прочитанными ───────────────────────────────────────────
class MarkReadView(APIView):
    """
    POST /api/chat/conversations/<conv_id>/read/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conv_id):
        user = request.user
        conv = get_object_or_404(
            Conversation.objects.filter(Q(user1=user) | Q(user2=user)),
            pk=conv_id,
        )
        updated = conv.messages.filter(
            is_read=False,
        ).exclude(sender=user).update(is_read=True, status=Message.Status.READ)
        return Response({'marked_read': updated})


# ─── Общий счётчик непрочитанных ─────────────────────────────────────
class UnreadCountView(APIView):
    """
    GET /api/chat/unread-count/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        count = Message.objects.filter(
            conversation__in=Conversation.objects.filter(Q(user1=user) | Q(user2=user)),
            is_read=False,
        ).exclude(sender=user).count()
        return Response({'unread_count': count})
