import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Conversation, Message

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer для realtime чата (Контракт v1).
    
    URL: ws://host/ws/chat/<conversation_id>/?token=<jwt>
    """
    
    # Фиксируем версию протокола для этого консьюмера
    PROTOCOL_VERSION = 1

    async def connect(self):
        """Подключение к WebSocket."""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope.get('user')

        # 1. Проверяем, прошла ли аутентификация в Middleware
        if not self.user or not self.user.is_authenticated:
            logger.warning(
                f"Connection rejected (4001): Unauthenticated access attempt to conversation {self.conversation_id}."
            )
            await self.close(code=4001)
            return

        # 2. Проверяем права доступа (юзер участник диалога?)
        is_member = await self._check_conversation_membership(self.conversation_id, self.user)
        if not is_member:
            logger.warning(
                f"Connection rejected (4003): User {self.user.id} tried to access foreign conversation {self.conversation_id}."
            )
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
        if hasattr(self, 'user') and self.user and self.user.is_authenticated:
            logger.info(f"User {self.user.id} disconnected from chat {self.conversation_id}, code={close_code}")

    async def receive_json(self, content, **kwargs):
        """Получение JSON от клиента и строгая валидация v1."""
        try:
            # 1. Проверяем версию протокола
            version = content.get('v')
            if version != self.PROTOCOL_VERSION:
                await self._send_error("bad_format", f"Неподдерживаемая версия. Ожидается v={self.PROTOCOL_VERSION}")
                return

            # 2. Проверяем обязательные поля
            event_type = content.get('type')
            payload = content.get('payload')

            if not event_type or not isinstance(event_type, str):
                await self._send_error("bad_format", "Поле 'type' обязательно и должно быть строкой.")
                return
                
            if payload is None or not isinstance(payload, dict):
                await self._send_error("bad_format", "Поле 'payload' обязательно и должно быть объектом.")
                return

            # 3. Маршрутизация событий
            if event_type == 'message.send':
                await self._handle_message_send(payload)
            elif event_type == 'message.read':
                await self._handle_message_read(payload)
            elif event_type == 'typing.start':
                await self._handle_typing_start(payload)
            elif event_type == 'typing.stop':
                await self._handle_typing_stop(payload)
            else:
                await self._send_error("unknown_event", f"Неизвестный тип события: {event_type}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self._send_error("server_error", "Внутренняя ошибка сервера при обработке события")

    # ─── Единые методы для отправки (v1) ───────────────────────────

    async def _send_event(self, event_type: str, payload: dict):
        """Обертка для отправки любых сообщений в формате v1."""
        await self.send_json({
            "v": self.PROTOCOL_VERSION,
            "type": event_type,
            "payload": payload
        })

    async def _send_error(self, code: str, message: str):
        """Единый формат отправки ошибок (Acceptance Criteria)."""
        await self._send_event("error", {
            "code": code,
            "message": message
        })

    # ─── Обработчики событий (от клиента) ──────────────────────────

    async def _handle_message_send(self, payload):
        """Обработка события message.send (бывшее message.new)."""
        text = (payload.get('text') or '').strip()
        request_id = payload.get('request_id')  # Достаем ID от фронтенда
        
        if not text:
            await self._send_error("validation_error", "Текст сообщения пуст")
            return
        
        if len(text) > 4000:
            await self._send_error("validation_error", "Текст слишком длинный (макс 4000)")
            return

        try:
            msg = await self._save_message(self.conversation_id, self.user, text)
            
            # 1. Отправляем ACK (подтверждение) только отправителю
            if request_id:
                await self._send_event("ack", {
                    "request_id": request_id,
                    "message_id": msg.id,
                    "status": "ok"
                })

            # 2. Рассылаем message.new всем в комнате
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message_new',
                    'message_id': msg.id,
                    'sender_id': msg.sender_id,
                    'text': msg.text,
                    'created_at': msg.created_at.isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            await self._send_error("server_error", "Ошибка сохранения сообщения")

    async def _handle_message_read(self, payload):
        """Обработка события message.read."""
        try:
            count = await self._mark_messages_read(self.conversation_id, self.user)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message_read',
                    'read_by_id': self.user.id,
                    'marked_count': count,
                }
            )
        except Exception as e:
            logger.error(f"Error marking read: {e}")

    async def _handle_typing_start(self, payload):
        """Обработка события typing.start."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.typing_start',
                'user_id': self.user.id,
                'user_name': f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username,
            }
        )

    async def _handle_typing_stop(self, payload):
        """Обработка события typing.stop."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.typing_stop',
                'user_id': self.user.id,
            }
        )

    # ─── Получатели событий из Redis (type.handler) ─────────────────

    async def chat_message_new(self, event):
        """Получатель события chat.message_new из Redis."""
        await self._send_event("message.new", {
            "message_id": event['message_id'],
            "conversation_id": self.conversation_id,
            "sender_id": event['sender_id'],
            "text": event['text'],
            "created_at": event['created_at'],
        })

    async def chat_message_read(self, event):
        """Получатель события chat.message_read из Redis."""
        await self._send_event("message.read", {
            "conversation_id": self.conversation_id,
            "read_by_id": event['read_by_id'],
            "marked_count": event['marked_count'],
        })

    async def chat_typing_start(self, event):
        """Получатель события chat.typing_start из Redis."""
        await self._send_event("typing.start", {
            "conversation_id": self.conversation_id,
            "user_id": event['user_id'],
            "user_name": event['user_name'],
        })

    async def chat_typing_stop(self, event):
        """Получатель события chat.typing_stop из Redis."""
        await self._send_event("typing.stop", {
            "conversation_id": self.conversation_id,
            "user_id": event['user_id'],
        })

    # ─── Вспомогательные методы (БД) ────────────────────────────────

    @database_sync_to_async
    def _check_conversation_membership(self, conversation_id, user):
        return Conversation.objects.filter(
            Q(user1=user) | Q(user2=user),
            pk=conversation_id
        ).exists()

    @database_sync_to_async
    def _save_message(self, conversation_id, user, text):
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
        count = Message.objects.filter(
            conversation_id=conversation_id,
            is_read=False
        ).exclude(sender=user).update(is_read=True)
        return count