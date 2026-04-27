import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from .models import Conversation, Message

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer для realtime чата.
    
    URL: ws://host/ws/chat/<conversation_id>/?token=<jwt>
    
    События:
    - message.new: отправить сообщение
    - message.read: отметить сообщения прочитанными
    - typing.start: начать печатать
    - typing.stop: прекратить печатать
    """

    async def connect(self):
        """Подключение к WebSocket с аутентификацией JWT."""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = None

        # 1. Проверяем JWT токен из query params
        try:
            token = self._get_token_from_scope()
            if not token:
                await self.close(code=4001)
                return

            self.user = await self._authenticate_token(token)
            if not self.user:
                await self.close(code=4001)
                return
        except Exception as e:
            logger.error(f"Auth error: {e}")
            await self.close(code=4001)
            return

        # 2. Проверяем права доступа (юзер участник диалога?)
        is_member = await self._check_conversation_membership(self.conversation_id, self.user)
        if not is_member:
            logger.warning(f"User {self.user.id} tried to access conversation {self.conversation_id}")
            await self.close(code=4003)  # Forbidden
            return

        # 3. Присоединяемся к группе (Redis)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info(f"User {self.user.id} connected to chat {self.conversation_id}")

    async def disconnect(self, close_code):
        """Отключение от WebSocket."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if self.user:
            logger.info(f"User {self.user.id} disconnected from chat {self.conversation_id}, code={close_code}")

    async def receive_json(self, content, **kwargs):
        """Получение JSON от клиента."""
        try:
            event_type = content.get('type')

            if event_type == 'message.new':
                await self._handle_message_new(content)
            elif event_type == 'message.read':
                await self._handle_message_read(content)
            elif event_type == 'typing.start':
                await self._handle_typing_start(content)
            elif event_type == 'typing.stop':
                await self._handle_typing_stop(content)
            else:
                logger.warning(f"Unknown event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_json({'type': 'error', 'error': str(e)}, close=False)

    # ─── Обработчики событий ───────────────────────────────────────

    async def _handle_message_new(self, content):
        """Обработка события message.new — новое сообщение."""
        text = (content.get('text') or '').strip()
        
        if not text:
            await self.send_json({'type': 'error', 'error': 'Текст пуст'})
            return
        
        if len(text) > 4000:
            await self.send_json({'type': 'error', 'error': 'Текст слишком длинный (макс 4000)'})
            return

        # Сохранить сообщение в БД (sync_to_async)
        try:
            msg = await self._save_message(self.conversation_id, self.user, text)
            
            # Разослать всем в комнате
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message',
                    'message_id': msg.id,
                    'conversation_id': msg.conversation_id,
                    'sender_id': msg.sender_id,
                    'text': msg.text,
                    'created_at': msg.created_at.isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            await self.send_json({'type': 'error', 'error': 'Ошибка сохранения'})

    async def _handle_message_read(self, content):
        """Обработка события message.read — отметить прочитанными."""
        try:
            # Отметить сообщения собеседника как прочитанные
            count = await self._mark_messages_read(self.conversation_id, self.user)
            
            # Разослать событие
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message_read',
                    'conversation_id': self.conversation_id,
                    'read_by_id': self.user.id,
                    'marked_count': count,
                }
            )
        except Exception as e:
            logger.error(f"Error marking read: {e}")

    async def _handle_typing_start(self, content):
        """Обработка события typing.start — начало печати."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.typing_start',
                'conversation_id': self.conversation_id,
                'user_id': self.user.id,
                'user_name': f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username,
            }
        )

    async def _handle_typing_stop(self, content):
        """Обработка события typing.stop — конец печати."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.typing_stop',
                'conversation_id': self.conversation_id,
                'user_id': self.user.id,
            }
        )

    # ─── Получатели событий (type.handler) ──────────────────────────

    async def chat_message(self, event):
        """Получатель события chat.message."""
        await self.send_json({
            'type': 'message.new',
            'message_id': event['message_id'],
            'conversation_id': event['conversation_id'],
            'sender_id': event['sender_id'],
            'text': event['text'],
            'created_at': event['created_at'],
        })

    async def chat_message_read(self, event):
        """Получатель события chat.message_read."""
        await self.send_json({
            'type': 'message.read',
            'conversation_id': event['conversation_id'],
            'read_by_id': event['read_by_id'],
            'marked_count': event['marked_count'],
        })

    async def chat_typing_start(self, event):
        """Получатель события chat.typing_start."""
        await self.send_json({
            'type': 'typing.start',
            'conversation_id': event['conversation_id'],
            'user_id': event['user_id'],
            'user_name': event['user_name'],
        })

    async def chat_typing_stop(self, event):
        """Получатель события chat.typing_stop."""
        await self.send_json({
            'type': 'typing.stop',
            'conversation_id': event['conversation_id'],
            'user_id': event['user_id'],
        })

    # ─── Вспомогательные методы (sync_to_async) ─────────────────────

    def _get_token_from_scope(self):
        """Получить JWT токен из query params."""
        query_string = self.scope.get('query_string', b'').decode()
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                if key == 'token':
                    return value
        return None

    @database_sync_to_async
    def _authenticate_token(self, token):
        """Аутентифицировать пользователя по JWT токену."""
        try:
            auth = JWTAuthentication()
            validated_token = auth.get_validated_token(token)
            user = auth.get_user(validated_token)
            return user if user and user.is_active else None
        except InvalidToken:
            return None

    @database_sync_to_async
    def _check_conversation_membership(self, conversation_id, user):
        """Проверить участие пользователя в диалоге."""
        return Conversation.objects.filter(
            Q(user1=user) | Q(user2=user),
            pk=conversation_id
        ).exists()

    @database_sync_to_async
    def _save_message(self, conversation_id, user, text):
        """Сохранить сообщение в БД."""
        conversation = Conversation.objects.get(pk=conversation_id)
        msg = Message.objects.create(
            conversation=conversation,
            sender=user,
            text=text
        )
        conversation.save(update_fields=['updated_at'])
        return msg

    @database_sync_to_async
    def _mark_messages_read(self, conversation_id, user):
        """Отметить сообщения собеседника как прочитанные."""
        count = Message.objects.filter(
            conversation_id=conversation_id,
            is_read=False
        ).exclude(sender=user).update(is_read=True)
        return count