import logging
import time
from urllib.parse import parse_qs

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

    URL: ws://host/ws/chat/<conversation_id>/?token=<jwt>[&last_seen=<message_id>]

    Контракт входящих событий (от клиента):
      { "v": 1, "type": "message.send",  "payload": { "text": "...", "client_message_id": "uuid", "request_id": "uuid" } }
      { "v": 1, "type": "message.read",  "payload": {} }
      { "v": 1, "type": "typing.start",  "payload": {} }
      { "v": 1, "type": "typing.stop",   "payload": {} }

    Контракт исходящих событий (серверные push):
      message.new   — новое сообщение в диалоге
      message.read  — кто-то прочитал сообщения
      typing.start  — собеседник печатает
      typing.stop   — собеседник перестал печатать
      ack           — подтверждение отправки (только отправителю)
      error         — ошибка валидации / rate-limit
    """

    PROTOCOL_VERSION = 1

    # Лимиты: (кол-во запросов, окно в секундах)
    RATE_LIMITS = {
        'message.send': (20, 60),   # 20 сообщений за 60 с
        'message.read': (5, 10),    # 5 отметок за 10 с
        'typing.start': (5, 5),     # 5 событий за 5 с
        'typing.stop': (5, 5),
        'default': (20, 10),
    }

    # ─── Connection lifecycle ─────────────────────────────────────────

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            logger.warning("ws.connect.rejected.unauth conv=%s", self.conversation_id)
            await self.close(code=4001)
            return

        is_member = await self._check_conversation_membership(self.conversation_id, self.user)
        if not is_member:
            logger.warning(
                "ws.connect.rejected.forbidden user=%s conv=%s",
                self.user.id, self.conversation_id,
            )
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info("ws.connect.ok user=%s conv=%s channel=%s", self.user.id, self.conversation_id, self.channel_name)

        # TAY-14: Помечаем все неполученные сообщения как delivered
        await self._mark_delivered_on_connect(self.conversation_id, self.user)

        # TAY-15: Resync — отправляем пропущенные сообщения
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        last_seen_raw = params.get('last_seen', [None])[0]
        if last_seen_raw and last_seen_raw.isdigit():
            await self._resync(int(last_seen_raw))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        user_id = getattr(self.user, 'id', None) if hasattr(self, 'user') else None
        if user_id:
            logger.info(
                "ws.disconnect user=%s conv=%s code=%s",
                user_id, self.conversation_id, close_code,
            )

    # ─── Receive ─────────────────────────────────────────────────────

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        """Защита от огромных payload до десериализации JSON."""
        if text_data and len(text_data) > 10 * 1024:
            logger.warning(
                "ws.payload_too_large user=%s conv=%s size=%d",
                getattr(self.user, 'id', '?'), self.conversation_id, len(text_data),
            )
            await self.close(code=4009)
            return
        await super().receive(text_data=text_data, bytes_data=bytes_data, **kwargs)

    async def receive_json(self, content, **kwargs):
        try:
            if content.get('v') != self.PROTOCOL_VERSION:
                await self._send_error("bad_format", f"Ожидается v={self.PROTOCOL_VERSION}")
                return

            event_type = content.get('type')
            payload = content.get('payload')

            if not event_type or not isinstance(event_type, str) or len(event_type) > 50:
                await self._send_error("bad_format", "Поле 'type' обязательно (строка, макс 50).")
                return
            if payload is None or not isinstance(payload, dict):
                await self._send_error("bad_format", "Поле 'payload' обязательно (объект).")
                return

            # Fix: Redis-backed rate limiting (TAY-6 patch)
            if await self._check_rate_limit(event_type):
                logger.warning(
                    "ws.rate_limit user=%s conv=%s event=%s",
                    getattr(self.user, 'id', '?'), self.conversation_id, event_type,
                )
                await self._send_error("rate_limit_exceeded", "Слишком много запросов. Подождите.")
                return

            if event_type == 'message.send':
                await self._handle_message_send(payload)
            elif event_type == 'message.read':
                await self._handle_message_read(payload)
            elif event_type == 'typing.start':
                await self._handle_typing_start(payload)
            elif event_type == 'typing.stop':
                await self._handle_typing_stop(payload)
            else:
                await self._send_error("unknown_event", f"Неизвестное событие: {event_type}")

        except Exception as exc:
            logger.exception(
                "ws.error user=%s conv=%s", getattr(self.user, 'id', '?'), self.conversation_id,
            )
            await self._send_error("server_error", "Ошибка сервера.")

    # ─── Event helpers ────────────────────────────────────────────────

    async def _send_event(self, event_type: str, payload: dict):
        await self.send_json({"v": self.PROTOCOL_VERSION, "type": event_type, "payload": payload})

    async def _send_error(self, code: str, message: str):
        await self._send_event("error", {"code": code, "message": message})

    # ─── Handlers (client → server) ──────────────────────────────────

    async def _handle_message_send(self, payload):
        text = (payload.get('text') or '').strip()
        request_id = payload.get('request_id')
        client_message_id = payload.get('client_message_id') or None

        if not text:
            await self._send_error("validation_error", "Текст сообщения пуст")
            return
        if len(text) > 4000:
            await self._send_error("validation_error", "Текст слишком длинный (макс 4000)")
            return
        if request_id and (not isinstance(request_id, str) or len(request_id) > 100):
            await self._send_error("validation_error", "Некорректный request_id (строка, макс 100)")
            return

        try:
            msg, created = await self._save_message(
                self.conversation_id, self.user, text, client_message_id
            )

            # ACK только отправителю
            if request_id:
                await self._send_event("ack", {
                    "request_id": request_id,
                    "message_id": msg.id,
                    "status": "ok",
                    "is_duplicate": not created,
                })

            # Рассылаем всем в комнате только если сообщение новое
            if created:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message_new',
                        'message_id': msg.id,
                        'sender_id': msg.sender_id,
                        'text': msg.text,
                        'created_at': msg.created_at.isoformat(),
                        'status': msg.status,
                        'client_message_id': msg.client_message_id,
                    }
                )
                logger.info(
                    "ws.message_sent user=%s conv=%s msg=%s",
                    self.user.id, self.conversation_id, msg.id,
                )

        except Exception:
            logger.exception("ws.save_message.error user=%s conv=%s", self.user.id, self.conversation_id)
            await self._send_error("server_error", "Ошибка сохранения сообщения")

    async def _handle_message_read(self, payload):
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
            logger.info(
                "ws.message_read user=%s conv=%s count=%d",
                self.user.id, self.conversation_id, count,
            )
        except Exception:
            logger.exception("ws.mark_read.error user=%s", self.user.id)

    async def _handle_typing_start(self, payload):
        user_name = f"{self.user.first_name} {self.user.last_name}".strip() or str(self.user.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'chat.typing_start', 'user_id': self.user.id, 'user_name': user_name},
        )

    async def _handle_typing_stop(self, payload):
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'chat.typing_stop', 'user_id': self.user.id},
        )

    # ─── Redis group receivers (server → client) ──────────────────────

    async def chat_message_new(self, event):
        # TAY-14: помечаем как delivered, когда сообщение получает получатель
        if event['sender_id'] != self.user.id:
            await self._mark_single_delivered(event['message_id'])

        await self._send_event("message.new", {
            "message_id": event['message_id'],
            "conversation_id": int(self.conversation_id),
            "sender_id": event['sender_id'],
            "text": event['text'],
            "created_at": event['created_at'],
            "status": event.get('status', 'sent'),
            "client_message_id": event.get('client_message_id'),
        })

    async def chat_message_read(self, event):
        await self._send_event("message.read", {
            "conversation_id": int(self.conversation_id),
            "read_by_id": event['read_by_id'],
            "marked_count": event['marked_count'],
        })

    async def chat_typing_start(self, event):
        await self._send_event("typing.start", {
            "conversation_id": int(self.conversation_id),
            "user_id": event['user_id'],
            "user_name": event['user_name'],
        })

    async def chat_typing_stop(self, event):
        await self._send_event("typing.stop", {
            "conversation_id": int(self.conversation_id),
            "user_id": event['user_id'],
        })

    # ─── Rate limiting — Redis через Django cache ─────────────────────
    # Fix TAY-6: заменяем in-memory на cache-based (работает с несколькими воркерами)

    async def _check_rate_limit(self, event_type: str) -> bool:
        return await self._check_rate_limit_sync(event_type)

    @database_sync_to_async
    def _check_rate_limit_sync(self, event_type: str) -> bool:
        from django.core.cache import cache

        limit_count, limit_window = self.RATE_LIMITS.get(event_type, self.RATE_LIMITS['default'])
        now = time.time()
        key = f"ws_rl:{self.user.id}:{event_type}"

        records = cache.get(key) or []
        records = [ts for ts in records if now - ts < limit_window]

        if len(records) >= limit_count:
            cache.set(key, records, timeout=int(limit_window) + 1)
            return True

        records.append(now)
        cache.set(key, records, timeout=int(limit_window) + 1)
        return False

    # ─── DB helpers ───────────────────────────────────────────────────

    @database_sync_to_async
    def _check_conversation_membership(self, conversation_id, user):
        return Conversation.objects.filter(
            Q(user1=user) | Q(user2=user), pk=conversation_id
        ).exists()

    @database_sync_to_async
    def _save_message(self, conversation_id, user, text, client_message_id=None):
        """TAY-9: Идемпотентное сохранение. Возвращает (message, created)."""
        from django.db import transaction

        conversation = Conversation.objects.get(pk=conversation_id)

        if client_message_id:
            existing = Message.objects.filter(
                conversation=conversation,
                sender=user,
                client_message_id=client_message_id,
            ).first()
            if existing:
                return existing, False

        with transaction.atomic():
            msg = Message.objects.create(
                conversation=conversation,
                sender=user,
                text=text,
                client_message_id=client_message_id,
                status=Message.Status.SENT,
            )
            conversation.save(update_fields=['updated_at'])
        return msg, True

    @database_sync_to_async
    def _mark_messages_read(self, conversation_id, user):
        """Помечает все сообщения собеседника как прочитанные."""
        return Message.objects.filter(
            conversation_id=conversation_id,
            is_read=False,
        ).exclude(sender=user).update(is_read=True, status=Message.Status.READ)

    @database_sync_to_async
    def _mark_delivered_on_connect(self, conversation_id, user):
        """TAY-14: При подключении помечаем sent → delivered для сообщений получателя."""
        Message.objects.filter(
            conversation_id=conversation_id,
            status=Message.Status.SENT,
        ).exclude(sender=user).update(status=Message.Status.DELIVERED)

    @database_sync_to_async
    def _mark_single_delivered(self, message_id):
        """TAY-14: Помечаем конкретное сообщение как delivered когда WS получатель его видит."""
        Message.objects.filter(
            pk=message_id,
            status=Message.Status.SENT,
        ).update(status=Message.Status.DELIVERED)

    @database_sync_to_async
    def _get_missed_messages(self, conversation_id, last_seen_id):
        """TAY-15: Возвращает сообщения новее last_seen_id (максимум 200)."""
        msgs = list(
            Message.objects
            .filter(conversation_id=conversation_id, id__gt=last_seen_id)
            .order_by('created_at')
            .select_related('sender')[:200]
        )
        return [
            {
                'message_id': m.id,
                'sender_id': m.sender_id,
                'text': m.text,
                'created_at': m.created_at.isoformat(),
                'status': m.status,
                'client_message_id': m.client_message_id,
            }
            for m in msgs
        ]

    async def _resync(self, last_seen_id: int):
        """TAY-15: Отправляем пропущенные сообщения после переподключения."""
        missed = await self._get_missed_messages(self.conversation_id, last_seen_id)
        if missed:
            logger.info(
                "ws.resync user=%s conv=%s missed=%d since_id=%d",
                self.user.id, self.conversation_id, len(missed), last_seen_id,
            )
        for msg_data in missed:
            await self._send_event("message.new", {
                **msg_data,
                "conversation_id": int(self.conversation_id),
            })
