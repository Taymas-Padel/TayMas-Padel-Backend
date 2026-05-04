"""
TAY-17: Базовые тесты чата (REST + модель).

Запуск:
  python manage.py test chat --verbosity=2

WebSocket тесты (channels.testing) запускаются отдельно с InMemoryChannelLayer:
  pytest chat/tests_ws.py  (если настроен pytest-asyncio)
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .models import Conversation, Message

User = get_user_model()


def _make_user(phone):
    return User.objects.create_user(
        username=phone, phone_number=phone, password='testpass123'
    )


def _auth(user):
    """Возвращает Bearer-заголовок для APIClient."""
    token = RefreshToken.for_user(user).access_token
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


class MessageModelTestCase(TestCase):
    """Тесты модели Message."""

    def setUp(self):
        self.u1 = _make_user('+77710000001')
        self.u2 = _make_user('+77710000002')
        # Создаём диалог напрямую (без FriendRequest) для unit-тестов
        u1, u2 = (self.u1, self.u2) if self.u1.id < self.u2.id else (self.u2, self.u1)
        self.conv = Conversation.objects.create(user1=u1, user2=u2)

    def test_default_status_is_sent(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.u1, text='Hello')
        self.assertEqual(msg.status, Message.Status.SENT)
        self.assertFalse(msg.is_read)

    def test_client_message_id_uniqueness(self):
        """Один client_message_id не должен создавать два сообщения."""
        cmid = 'idem-test-001'
        msg1 = Message.objects.create(
            conversation=self.conv, sender=self.u1, text='Hi', client_message_id=cmid
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Message.objects.create(
                conversation=self.conv, sender=self.u1, text='Duplicate', client_message_id=cmid
            )

    def test_null_client_message_id_allows_duplicates(self):
        """Без client_message_id дубликаты разрешены (нет ограничения)."""
        Message.objects.create(conversation=self.conv, sender=self.u1, text='A')
        Message.objects.create(conversation=self.conv, sender=self.u1, text='A')
        self.assertEqual(Message.objects.filter(conversation=self.conv).count(), 2)


class ChatRESTTestCase(TestCase):
    """Тесты REST API чата."""

    def setUp(self):
        self.client = APIClient()
        self.u1 = _make_user('+77720000001')
        self.u2 = _make_user('+77720000002')
        u1, u2 = (self.u1, self.u2) if self.u1.id < self.u2.id else (self.u2, self.u1)
        self.conv = Conversation.objects.create(user1=u1, user2=u2)

    def _url_messages(self, conv_id=None):
        cid = conv_id or self.conv.id
        return f'/api/chat/conversations/{cid}/messages/'

    # ── Auth ──────────────────────────────────────────────────────────

    def test_message_list_requires_auth(self):
        r = self.client.get(self._url_messages())
        self.assertIn(r.status_code, [401, 403])

    def test_send_requires_auth(self):
        r = self.client.post(self._url_messages(), {'text': 'Hi'}, format='json')
        self.assertIn(r.status_code, [401, 403])

    # ── Send message ─────────────────────────────────────────────────

    def test_send_message_success(self):
        r = self.client.post(
            self._url_messages(),
            {'text': 'Привет!'},
            format='json',
            **_auth(self.u1),
        )
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(data['status'], 'sent')
        self.assertFalse(data['is_read'])

    def test_send_empty_text_rejected(self):
        r = self.client.post(
            self._url_messages(), {'text': '   '}, format='json', **_auth(self.u1),
        )
        self.assertEqual(r.status_code, 400)

    def test_send_too_long_text_rejected(self):
        r = self.client.post(
            self._url_messages(), {'text': 'X' * 4001}, format='json', **_auth(self.u1),
        )
        self.assertEqual(r.status_code, 400)

    def test_foreign_user_cannot_access_conversation(self):
        stranger = _make_user('+77729999999')
        r = self.client.get(self._url_messages(), **_auth(stranger))
        self.assertEqual(r.status_code, 404)

    # ── TAY-9: Idempotency ───────────────────────────────────────────

    def test_idempotent_send_no_duplicate(self):
        payload = {'text': 'Тест идемпотентности', 'client_message_id': 'test-cmid-42'}
        r1 = self.client.post(self._url_messages(), payload, format='json', **_auth(self.u1))
        r2 = self.client.post(self._url_messages(), payload, format='json', **_auth(self.u1))

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()['id'], r2.json()['id'])
        self.assertEqual(
            Message.objects.filter(client_message_id='test-cmid-42').count(), 1
        )

    # ── TAY-13: Cursor pagination ────────────────────────────────────

    def test_cursor_pagination_before_id(self):
        msgs = [
            Message.objects.create(conversation=self.conv, sender=self.u1, text=f'Msg {i}')
            for i in range(5)
        ]
        r = self.client.get(
            f'{self._url_messages()}?before_id={msgs[-1].id}',
            **_auth(self.u1),
        )
        self.assertEqual(r.status_code, 200)
        ids = [m['id'] for m in r.json()]
        self.assertNotIn(msgs[-1].id, ids)
        self.assertIn(msgs[0].id, ids)

    def test_cursor_pagination_after_id(self):
        msgs = [
            Message.objects.create(conversation=self.conv, sender=self.u1, text=f'Msg {i}')
            for i in range(5)
        ]
        r = self.client.get(
            f'{self._url_messages()}?after_id={msgs[0].id}',
            **_auth(self.u1),
        )
        self.assertEqual(r.status_code, 200)
        ids = [m['id'] for m in r.json()]
        self.assertNotIn(msgs[0].id, ids)
        self.assertIn(msgs[-1].id, ids)

    # ── TAY-14: Delivery status ──────────────────────────────────────

    def test_mark_read_updates_status(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.u2, text='Hi')
        self.assertEqual(msg.status, Message.Status.SENT)

        r = self.client.post(
            f'/api/chat/conversations/{self.conv.id}/read/',
            **_auth(self.u1),
        )
        self.assertEqual(r.status_code, 200)
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
        self.assertEqual(msg.status, Message.Status.READ)

    # ── Unread count ─────────────────────────────────────────────────

    def test_unread_count(self):
        Message.objects.create(conversation=self.conv, sender=self.u2, text='Msg 1')
        Message.objects.create(conversation=self.conv, sender=self.u2, text='Msg 2')

        r = self.client.get('/api/chat/unread-count/', **_auth(self.u1))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['unread_count'], 2)

    def test_own_messages_not_in_unread(self):
        Message.objects.create(conversation=self.conv, sender=self.u1, text='Mine')
        r = self.client.get('/api/chat/unread-count/', **_auth(self.u1))
        self.assertEqual(r.json()['unread_count'], 0)

    # ── TAY-10: N+1 — стабильное число запросов ──────────────────────

    def test_conversation_list_query_count(self):
        for i in range(3):
            Message.objects.create(conversation=self.conv, sender=self.u2, text=f'Msg {i}')

        from django.db import connection, reset_queries
        from django.test.utils import override_settings

        with override_settings(DEBUG=True):
            reset_queries()
            r = self.client.get('/api/chat/conversations/', **_auth(self.u1))
            n_queries = len(connection.queries)

        self.assertEqual(r.status_code, 200)
        # Должно быть константное число запросов (не N+1)
        # 1 запрос на conversations + select_related users + аннотации = ~3-4 max
        self.assertLess(n_queries, 10)
