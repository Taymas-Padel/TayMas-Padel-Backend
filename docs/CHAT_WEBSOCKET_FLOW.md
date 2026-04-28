# Chat WebSocket Flow

Production-ready realtime чат на Django Channels + Redis.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (React/TypeScript)                                     │
│  - Подключение к WS: ws://api/ws/chat/<conversation_id>/?token │
│  - Отправка событий: message.new, typing.start, message.read   │
│  - Получение событий: в реальном времени                        │
│  - Fallback: REST при разрыве соединения                        │
└─────────────┬───────────────────────────────────────────────────┘
              │ WebSocket (HTTP Upgrade)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│ ASGI Server (Daphne)                                            │
│  - ProtocolTypeRouter: http → Django, websocket → Channels     │
│  - URLRouter: /ws/chat/<conversation_id>/ → ChatConsumer        │
└─────────────┬───────────────────────────────────────────────────┘
              │ (sync_to_async)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│ ChatConsumer (AsyncJsonWebsocketConsumer)                       │
│  1. Аутентификация: JWT токен из query params                  │
│  2. Проверка прав: пользователь участник диалога               │
│  3. Подключение к Redis группе: chat_{conversation_id}         │
│  4. Обработка событий и рассылка группе                        │
└─────────────┬───────────────────────────────────────────────────┘
              │ (channel_layer.group_send)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Redis Channel Layer                                             │
│  - Масштабирование: несколько ASGI процессов                   │
│  - Группы: chat_{conversation_id}                              │
│  - Сохранение состояния: TTL ~24ч                              │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│ PostgreSQL Database                                             │
│  - Message (sender, text, is_read, created_at, ...)            │
│  - Conversation (user1, user2, updated_at, ...)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## WebSocket URL

```
ws://localhost:8000/ws/chat/<conversation_id>/?token=<jwt_access_token>
```

или для HTTPS:

```
wss://api.example.com/ws/chat/<conversation_id>/?token=<jwt_access_token>
```

**Параметры:**
- `conversation_id` — ID диалога (обязателен)
- `token` — JWT access token (обязателен, из query params)

---

## Аутентификация

### 1. Получение JWT токена

```bash
POST /api/auth/crm/login/
Body: { "username": "admin", "password": "password" }

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 2. Подключение к WebSocket

```javascript
const token = localStorage.getItem('accessToken')
const conversationId = 123
const ws = new WebSocket(
  `ws://localhost:8000/ws/chat/${conversationId}/?token=${token}`
)
```

### 3. Проверка на backend

```python
# ChatConsumer._authenticate_token()
- Декодирует JWT токен
- Возвращает User объект
- Если токен невалиден → close(4001 Unauthorized)
- Если юзер не участник диалога → close(4003 Forbidden)
```

---

## События (Type)

### Отправка с клиента → Backend

#### `message.send` — отправить сообщение

```json
{
  "v": 1,
  "type": "message.send",
  "payload": {
    "text": "Привет!",
    "request_id": "unique-id-123"
  }
}
```

**Ответ:**
- Если OK: отправителю приходит `ack` с `request_id` и `message_id`, а всем в комнате рассылается `message.new`
- Если ошибка: `{"v": 1, "type": "error", "payload": {"code": "validation_error", "message": "Текст пуст"}}`

**Валидация:**
- `text` не пустой
- Макс 4000 символов
- Сохраняется в БД: `Message(conversation, sender, text, is_read=False, created_at=now)`

---

#### `message.read` — отметить прочитанными

```json
{
  "v": 1,
  "type": "message.read",
  "payload": {}
}
```

**Действие:**
- Отмечает все **непрочитанные сообщения собеседника** в диалоге как `is_read=True`
- Рассылает событие `message.read` в комнату

**Ответ для других участников:**
```json
{
  "v": 1,
  "type": "message.read",
  "payload": {
    "conversation_id": 123,
    "read_by_id": 1,
    "marked_count": 5
  }
}
```

---

#### `typing.start` — начало печати

```json
{
  "v": 1,
  "type": "typing.start",
  "payload": {}
}
```

**Ответ для собеседника:**
```json
{
  "v": 1,
  "type": "typing.start",
  "payload": {
    "conversation_id": 123,
    "user_id": 1,
    "user_name": "Иван Петров"
  }
}
```

---

#### `typing.stop` — конец печати

```json
{
  "v": 1,
  "type": "typing.stop",
  "payload": {}
}
```

**Ответ для собеседника:**
```json
{
  "v": 1,
  "type": "typing.stop",
  "payload": {
    "conversation_id": 123,
    "user_id": 1
  }
}
```

---

### Получение с Backend → Клиента

#### `ack` — подтверждение отправки (новое)

```json
{
  "v": 1,
  "type": "ack",
  "payload": {
    "request_id": "unique-id-123",
    "message_id": 456,
    "status": "ok"
  }
}
```

**Когда приходит:**
- Сразу после успешной обработки `message.send` (только отправителю). Позволяет обновить локальный UI и убрать "часики".

---

#### `message.new` — новое сообщение

```json
{
  "v": 1,
  "type": "message.new",
  "payload": {
    "message_id": 456,
    "conversation_id": 123,
    "sender_id": 1,
    "text": "Привет!",
    "created_at": "2026-04-27T15:30:00Z"
  }
}
```

**Когда приходит:**
- Когда **другой пользователь** отправляет сообщение в тот же диалог

---

#### `message.read` — сообщения прочитаны

```json
{
<<<<<<< HEAD
  "type": "message.read",
  "conversation_id": 123,
  "read_by_id": 2,
  "marked_count": 3
=======
  "v": 1,
  "type": "message.read",
  "payload": {
    "conversation_id": 123,
    "read_by_id": 2,
    "marked_count": 3
  }
>>>>>>> origin/main
}
```

**Когда приходит:**
- Когда **другой пользователь** отметил твои сообщения прочитанными

---

#### `typing.start` — собеседник печатает

```json
{
<<<<<<< HEAD
  "type": "typing.start",
  "conversation_id": 123,
  "user_id": 2,
  "user_name": "Мария Сидорова"
=======
  "v": 1,
  "type": "typing.start",
  "payload": {
    "conversation_id": 123,
    "user_id": 2,
    "user_name": "Мария Сидорова"
  }
>>>>>>> origin/main
}
```

---

#### `typing.stop` — собеседник закончил печать

```json
{
<<<<<<< HEAD
  "type": "typing.stop",
  "conversation_id": 123,
  "user_id": 2
=======
  "v": 1,
  "type": "typing.stop",
  "payload": {
    "conversation_id": 123,
    "user_id": 2
  }
>>>>>>> origin/main
}
```

---

## Восстановление после разрыва WS

### Сценарий

```
1. Клиент отправляет сообщение → WS закрывается (сеть отвалилась)
2. Клиент ждёт reconnect delay (~3 сек)
3. Пытается переподключиться с тем же токеном
4. Если успешно → подписан на новые события
5. Если失败 → fallback на REST для получения новых сообщений
```

### REST Fallback API

#### Получить список диалогов

```
GET /api/chat/conversations/
Auth: Bearer <token>

Response:
[
  {
    "id": 123,
    "companion": {
      "id": 2,
      "full_name": "Иван Петров",
      "avatar": "...",
      "phone_number": "+77777777777"
    },
    "last_message": {
      "id": 456,
      "text": "Привет!",
      "sender_id": 1,
      "created_at": "...",
      "is_read": false
    },
    "unread_count": 3,
    "updated_at": "..."
  }
]
```

---

#### Получить сообщения (пагинация)

```
GET /api/chat/conversations/123/messages/?after=456&limit=50
Auth: Bearer <token>

Response:
[
  {
    "id": 457,
    "conversation": 123,
    "sender_id": 2,
    "text": "А что ты думаешь?",
    "is_read": false,
    "created_at": "2026-04-27T15:31:00Z"
  },
  ...
]
```

**Параметры:**
- `after=<message_id>` — только сообщения с id > after (для incrementalupdate)
- `limit=50` — кол-во (макс 200)

---

#### Отправить сообщение (fallback REST)

```
POST /api/chat/conversations/123/send/
Auth: Bearer <token>
Body: { "text": "Привет!" }

Response: { message_id, sender_id, created_at, ... }
```

---

#### Отметить прочитанными (REST)

```
POST /api/chat/conversations/123/read/
Auth: Bearer <token>

Response: { "marked_read": 5 }
```

---

## Логика восстановления (Frontend)

```typescript
class ChatService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  async connect(conversationId: number, token: string) {
    try {
      this.ws = new WebSocket(
        `ws://api/ws/chat/${conversationId}/?token=${token}`
      )
      this.ws.onopen = () => this.onConnected()
      this.ws.onmessage = (e) => this.onMessage(e)
      this.ws.onerror = (e) => this.onError(e)
      this.ws.onclose = (e) => this.onClose(e)
    } catch (err) {
      await this.fallbackToRest()
    }
  }

  private onClose(event: CloseEvent) {
    // 4001 Unauthorized, 4003 Forbidden → не переподключаться
    if (event.code === 4001 || event.code === 4003) {
      console.error('Auth failed, redirecting to login')
      return
    }

    // Иначе пытаемся переподключиться
    this.reconnect()
  }

  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      // Переходим на REST polling
      this.fallbackToRest()
      return
    }

    const delay = Math.min(1000 * (2 ** this.reconnectAttempts), 30000)
    setTimeout(() => {
      this.reconnectAttempts++
      this.connect(this.conversationId, this.token)
    }, delay)
  }

  private async fallbackToRest() {
    // Получить новые сообщения через REST
    const messages = await fetchMessages(
      this.conversationId,
      this.lastMessageId
    )
    this.addMessagesToUI(messages)

    // Периодический polling (каждые 5 сек)
    this.restPollInterval = setInterval(async () => {
      const newMessages = await fetchMessages(
        this.conversationId,
        this.lastMessageId
      )
      if (newMessages.length > 0) {
        this.addMessagesToUI(newMessages)
      }
    }, 5000)
  }
}
```

---

## Развёртывание

### Локально (dev)

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Redis должен работать
redis-server

# 3. Запустить ASGI сервер (вместо runserver)
daphne -b 127.0.0.1 -p 8000 config.asgi:application

# 4. Frontend подключается к ws://127.0.0.1:8000/ws/chat/...
```

---

### Production

```bash
# 1. Использовать Daphne с Supervisor/systemd
# /etc/systemd/system/padel-chat.service
[Service]
ExecStart=/path/to/venv/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 2. Redis должен быть отдельно (не localhost!)
# Конфиг: config/settings.py CHANNEL_LAYERS['default']['CONFIG']['hosts']

# 3. Nginx proxy для WSS (SSL)
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
}

# 4. SSL сертификат для WSS
# certbot / Let's Encrypt
```

---

## Мониторинг

### Проверка Redis

```bash
redis-cli
> KEYS "asgi:*"        # Все каналы
> INFO stats          # Статистика
> MONITOR              # Отслеживание команд
```

---

### Логирование

```python
# config/settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'chat.consumers': {
            'handlers': ['console'],
            'level': 'INFO',
        }
    }
}
```

---

## Тестирование

### WebSocket Test (wscat)

```bash
npm install -g wscat

# Подключиться
wscat -c "ws://127.0.0.1:8000/ws/chat/123/?token=eyJ0..."

# Отправить
<<<<<<< HEAD
{"type": "message.new", "text": "Hello"}

# Получить
{"type": "message.new", "message_id": 456, ...}
=======
{"v": 1, "type": "message.send", "payload": {"text": "Hello", "request_id": "test"}}

# Получить (ack)
{"v": 1, "type": "ack", "payload": {"request_id": "test", "message_id": 456, "status": "ok"}}

# Получить (new message)
{"v": 1, "type": "message.new", "payload": {"message_id": 456, "conversation_id": 123, "sender_id": 1, "text": "Hello", "created_at": "..."}}
>>>>>>> origin/main
```

---

### Python unittest

```python
# chat/tests.py
from channels.testing import WebsocketCommunicator
from chat.consumers import ChatConsumer

async def test_message_new():
    communicator = WebsocketCommunicator(
        ChatConsumer.as_asgi(),
        "/ws/chat/123/?token=fake"
    )
    connected, subprotocol = await communicator.connect()
    assert connected

    await communicator.send_json_to({
<<<<<<< HEAD
        "type": "message.new",
        "text": "Test"
    })

    response = await communicator.receive_json_from()
    assert response['type'] == 'message.new'
=======
        "v": 1,
        "type": "message.send",
        "payload": {
            "text": "Test"
        }
    })

    response = await communicator.receive_json_from()
    assert response['type'] in ('ack', 'message.new')
>>>>>>> origin/main
```

---

## Performance

### Latency

- **WS подключение**: ~50-100ms (один раз)
- **Отправка сообщения**: <200ms (локально), <1s (интернет)
- **Получение события**: <100ms (Redis broadcast)

### Масштабирование

- **Redis**: ~10k concurrent connections
- **Daphne процессы**: 1-4 на ядро CPU
- **БД**: пулинг Postgres (connection limit)

---

## Часто встречаемые проблемы

### 1. WebSocket не подключается

**Причина**: JWT токен неверный или истекший  
**Решение**: обновить токен через `/api/auth/jwt/refresh/`

### 2. "Channel layer not configured"

**Причина**: Redis не работает  
**Решение**: `redis-server` в отдельном терминале

### 3. Сообщение не сохраняется

**Причина**: `database_sync_to_async` ошибка  
**Решение**: проверить логи и оборачивать БД операции

### 4. Typing events повисают

**Решение**: клиент должен отправить `typing.stop` при потере фокуса

---

## Миграция с REST Polling

Если уже есть старый чат на REST:

1. Завести оба механизма параллельно (REST + WS)
2. Frontend пытается WS, на ошибку → REST polling
3. Постепенно отключать REST endpoints
4. В продакшене оставить REST как backup

---

## Справочник Endpoints

| Метод | URL | Описание |
|-------|-----|---------|
| WS | `/ws/chat/<id>/?token=...` | Realtime чат |
| GET | `/api/chat/conversations/` | Список диалогов |
| POST | `/api/chat/conversations/start/` | Новый диалог |
| GET | `/api/chat/conversations/<id>/messages/` | История сообщений |
| POST | `/api/chat/conversations/<id>/send/` | Отправить сообщение (REST) |
| POST | `/api/chat/conversations/<id>/read/` | Отметить прочитанными |
| GET | `/api/chat/unread-count/` | Общий счётчик непрочитанных |

