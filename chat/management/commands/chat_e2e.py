"""
E2E проверка чата: два пользователя, REST + WebSocket (без браузера).

Запуск (из корня проекта, с настроенной БД и миграциями):

  python manage.py chat_e2e

  # Уже существующие в БД пользователи (должны быть в друзьях):
  python manage.py chat_e2e --phone-a 77053795459 --phone-b 77066969698

Использует InMemory channel layer и LocMem cache на время прогона — Redis не обязателен.
Без --phone-* создаёт/обновляет e2e_chat_a / e2e_chat_b и заявку ACCEPTED.
С --phone-* ищет User по users_user.phone_number (несколько форматов номера).

Что проверяется:
  - REST: список диалогов, старт диалога, POST /messages/ + идемпотентность,
    GET cursor (after_id / before_id), POST /read/, unread-count
  - WS: connect обоих, message.send → ack + message.new у собеседника,
    typing.start/stop, message.read, дедуп по client_message_id на стороне WS
"""

import asyncio
import json
import re
import uuid
import urllib.parse

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from channels.testing import WebsocketCommunicator

from friends.models import FriendRequest
from chat.models import Conversation, Message

User = get_user_model()

# Уникальные телефоны, чтобы не пересекаться с ручными тестами
PHONE_A = '+79990001001'
PHONE_B = '+79990001002'
USER_A = 'e2e_chat_a'
USER_B = 'e2e_chat_b'


def _jwt(user):
    return str(RefreshToken.for_user(user).access_token)


def _phone_lookup_candidates(raw):
    """Варианты номера как в БД: +7705…, 7705…, 8 705…"""
    s = str(raw).strip().replace(' ', '')
    digits = re.sub(r'\D', '', s)
    out = {s}
    if digits:
        out.add('+' + digits)
        if len(digits) == 11 and digits.startswith('7'):
            out.add('8' + digits[1:])
    return {x for x in out if x}


def _resolve_user_by_phone(label, raw):
    for c in _phone_lookup_candidates(raw):
        u = User.objects.filter(phone_number=c).first()
        if u:
            return u
    raise CommandError(
        f'Пользователь {label} с номером {raw!r} не найден. '
        'Проверьте поле phone_number в админке / БД (ожидается как у логина, напр. +77053795459).'
    )


def _ensure_friends(user_a, user_b):
    if user_a.id == user_b.id:
        raise CommandError('Нужны два разных пользователя.')
    ok = FriendRequest.objects.filter(
        Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a),
        status=FriendRequest.Status.ACCEPTED,
    ).exists()
    if ok:
        return
    FriendRequest.objects.get_or_create(
        from_user=user_a,
        to_user=user_b,
        defaults={'status': FriendRequest.Status.ACCEPTED},
    )


async def _recv_json_until(communicator, type_whitelist, timeout=8.0):
    """Читает входящие JSON, пока type не из whitelist (строка или множество)."""
    if isinstance(type_whitelist, str):
        want = {type_whitelist}
    else:
        want = set(type_whitelist)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            remaining = max(0.1, deadline - loop.time())
            raw = await asyncio.wait_for(communicator.receive_from(), timeout=remaining)
            data = json.loads(raw)
            t = data.get('type')
            if t in want:
                return data
        except asyncio.TimeoutError:
            break
    raise AssertionError(f'Таймаут: не получили событие из {want}')


async def _ws_two_users_flow(conv_id, token_a, token_b, ws_cmid, stdout, style):
    path_base = f'/ws/chat/{conv_id}/'
    q_a = urllib.parse.urlencode({'token': token_a})
    q_b = urllib.parse.urlencode({'token': token_b})

    from config.asgi import application

    comm_a = WebsocketCommunicator(application, f'{path_base}?{q_a}')
    comm_b = WebsocketCommunicator(application, f'{path_base}?{q_b}')

    ok_a, _ = await comm_a.connect()
    ok_b, _ = await comm_b.connect()
    assert ok_a and ok_b, 'WS connect должен принять оба клиента'
    stdout.write(style.SUCCESS('  WS: оба пользователя подключены к комнате\n'))

    # A → сообщение (уникальный cmid на прогон — иначе в БД уже есть от прошлых запусков)
    cmid = ws_cmid
    await comm_a.send_json_to(
        {
            'v': 1,
            'type': 'message.send',
            'payload': {
                'text': 'Привет от A по WebSocket',
                'client_message_id': cmid,
                'request_id': 'req-ws-1',
            },
        }
    )

    ack = await _recv_json_until(comm_a, 'ack')
    assert ack['payload'].get('message_id'), 'ожидали ack с message_id'
    assert ack['payload'].get('is_duplicate') is False
    msg_id = ack['payload']['message_id']

    new_b = await _recv_json_until(comm_b, 'message.new')
    assert new_b['payload']['message_id'] == msg_id
    assert new_b['payload']['text'] == 'Привет от A по WebSocket'
    stdout.write(style.SUCCESS(f'  WS: A отправил → B получил message.new (id={msg_id})\n'))

    # Идемпотентность по WS
    await comm_a.send_json_to(
        {
            'v': 1,
            'type': 'message.send',
            'payload': {
                'text': 'Привет от A по WebSocket',
                'client_message_id': cmid,
                'request_id': 'req-ws-2',
            },
        }
    )
    ack2 = await _recv_json_until(comm_a, 'ack')
    assert ack2['payload']['message_id'] == msg_id
    assert ack2['payload'].get('is_duplicate') is True
    stdout.write(style.SUCCESS('  WS: повтор с тем же client_message_id → is_duplicate=True\n'))

    # Typing: B шлёт, A получает
    await comm_b.send_json_to({'v': 1, 'type': 'typing.start', 'payload': {}})
    typ_a = await _recv_json_until(comm_a, 'typing.start')
    assert typ_a['payload'].get('user_id') is not None
    await comm_b.send_json_to({'v': 1, 'type': 'typing.stop', 'payload': {}})
    await _recv_json_until(comm_a, 'typing.stop')
    stdout.write(style.SUCCESS('  WS: typing.start / typing.stop дошли до A\n'))

    # B помечает прочитанным — A получает message.read
    await comm_b.send_json_to({'v': 1, 'type': 'message.read', 'payload': {}})
    read_a = await _recv_json_until(comm_a, 'message.read')
    assert read_a['payload'].get('marked_count', 0) >= 1
    stdout.write(style.SUCCESS('  WS: B message.read → A получил message.read\n'))

    await comm_a.disconnect()
    await comm_b.disconnect()
    stdout.write(style.SUCCESS('  WS: отключение корректно\n'))


class Command(BaseCommand):
    help = 'E2E: два пользователя, полный сценарий REST + WebSocket (без браузера).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone-a',
            type=str,
            default=None,
            help='Номер пользователя A (как в БД или 7705…): не создавать e2e_chat_a, взять из User',
        )
        parser.add_argument(
            '--phone-b',
            type=str,
            default=None,
            help='Номер пользователя B',
        )

    def handle(self, *args, **options):
        overrides = {
            # APIClient обращается к хосту "testserver" — иначе DisallowedHost
            'ALLOWED_HOSTS': ['127.0.0.1', 'localhost', 'testserver'],
            'CHANNEL_LAYERS': {
                'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
            },
            'CACHES': {
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'chat_e2e_cmd',
                },
            },
        }
        with override_settings(**overrides):
            self._run_sync(options)

    def _run_sync(self, options):
        style = self.style
        phone_a = options.get('phone_a')
        phone_b = options.get('phone_b')

        run_id = uuid.uuid4().hex[:12]
        cmid_rest = f'e2e-rest-idem-{run_id}'
        ws_cmid = f'e2e-ws-idem-{run_id}'

        self.stdout.write(style.NOTICE('=== Chat E2E: подготовка пользователей и дружбы ===\n'))

        if phone_a and phone_b:
            user_a = _resolve_user_by_phone('A', phone_a)
            user_b = _resolve_user_by_phone('B', phone_b)
            _ensure_friends(user_a, user_b)
            self.stdout.write(
                f'  Режим: пользователи из БД по номерам → {user_a.username} (id={user_a.id}) ↔ '
                f'{user_b.username} (id={user_b.id})\n'
            )
        elif phone_a or phone_b:
            raise CommandError('Укажите оба: --phone-a и --phone-b, или не указывайте (тестовые e2e_chat_*).')
        else:
            user_a, _ = User.objects.get_or_create(
                username=USER_A,
                defaults={
                    'phone_number': PHONE_A,
                    'password': 'e2e_pass_chat_123',
                },
            )
            if user_a.phone_number != PHONE_A:
                user_a.phone_number = PHONE_A
                user_a.save(update_fields=['phone_number'])
            user_a.set_password('e2e_pass_chat_123')
            user_a.save()

            user_b, _ = User.objects.get_or_create(
                username=USER_B,
                defaults={
                    'phone_number': PHONE_B,
                    'password': 'e2e_pass_chat_123',
                },
            )
            if user_b.phone_number != PHONE_B:
                user_b.phone_number = PHONE_B
                user_b.save(update_fields=['phone_number'])
            user_b.set_password('e2e_pass_chat_123')
            user_b.save()

            fr = FriendRequest.objects.filter(
                from_user=user_a,
                to_user=user_b,
            ).first()
            if not fr:
                FriendRequest.objects.create(
                    from_user=user_a,
                    to_user=user_b,
                    status=FriendRequest.Status.ACCEPTED,
                )
            else:
                if fr.status != FriendRequest.Status.ACCEPTED:
                    fr.status = FriendRequest.Status.ACCEPTED
                    fr.save(update_fields=['status'])

        conv = Conversation.get_or_create_for_users(user_a, user_b)
        self.stdout.write(f'  Диалог id={conv.id} ({user_a.username} ↔ {user_b.username})\n')

        token_a = _jwt(user_a)
        token_b = _jwt(user_b)

        ca = APIClient()
        cb = APIClient()
        ca.credentials(HTTP_AUTHORIZATION=f'Bearer {token_a}')
        cb.credentials(HTTP_AUTHORIZATION=f'Bearer {token_b}')

        self.stdout.write(style.NOTICE('\n=== REST: список диалогов, старт, сообщения, read ===\n'))

        r = ca.get('/api/chat/conversations/')
        assert r.status_code == 200, r.content
        assert any(c['id'] == conv.id for c in r.json()), 'диалог должен быть в списке у A'
        self.stdout.write(style.SUCCESS('  GET /conversations/ — ок\n'))

        r = ca.post('/api/chat/conversations/start/', {'user_id': user_b.id}, format='json')
        assert r.status_code == 200
        assert r.json()['id'] == conv.id
        self.stdout.write(style.SUCCESS('  POST /conversations/start/ — ок\n'))

        r = ca.post(
            f'/api/chat/conversations/{conv.id}/messages/',
            {'text': 'REST от A', 'client_message_id': cmid_rest},
            format='json',
        )
        assert r.status_code == 201, r.content
        mid = r.json()['id']
        assert r.json()['status'] == 'sent', r.json()

        r = ca.post(
            f'/api/chat/conversations/{conv.id}/messages/',
            {'text': 'REST от A', 'client_message_id': cmid_rest},
            format='json',
        )
        assert r.status_code == 200
        assert r.json()['id'] == mid
        self.stdout.write(style.SUCCESS('  POST /messages/ идемпотентность — ок\n'))

        r = cb.get(f'/api/chat/conversations/{conv.id}/messages/?after_id={mid - 1}')
        assert r.status_code == 200
        bodies = r.json()
        assert any(m['id'] == mid for m in bodies)
        self.stdout.write(style.SUCCESS('  GET /messages/?after_id= — ок\n'))

        r = cb.post(f'/api/chat/conversations/{conv.id}/read/')
        assert r.status_code == 200
        assert r.json()['marked_read'] >= 1
        self.stdout.write(style.SUCCESS('  POST /read/ от B — ок\n'))

        msg = Message.objects.get(pk=mid)
        msg.refresh_from_db()
        assert msg.is_read is True
        assert msg.status == Message.Status.READ
        self.stdout.write(style.SUCCESS('  В БД сообщение помечено read — ок\n'))

        r = ca.get('/api/chat/unread-count/')
        assert r.status_code == 200
        self.stdout.write(style.SUCCESS(f'  GET /unread-count/ — {r.json()}\n'))

        # cursor before_id: создаём ещё одно сообщение и проверяем slice
        r = ca.post(
            f'/api/chat/conversations/{conv.id}/messages/',
            {'text': 'ещё одно для cursor'},
            format='json',
        )
        assert r.status_code == 201
        last_id = r.json()['id']
        r = cb.get(f'/api/chat/conversations/{conv.id}/messages/?before_id={last_id}&limit=10')
        assert r.status_code == 200
        ids = [m['id'] for m in r.json()]
        assert last_id not in ids
        self.stdout.write(style.SUCCESS('  GET /messages/?before_id= — ок\n'))

        self.stdout.write(style.NOTICE('\n=== WebSocket (in-process, Channels) ===\n'))
        asyncio.run(
            _ws_two_users_flow(conv.id, token_a, token_b, ws_cmid, self.stdout, style)
        )

        self.stdout.write(style.SUCCESS('\n=== Все проверки пройдены ===\n'))
