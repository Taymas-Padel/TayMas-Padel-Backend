# Интеграция чата — Flutter / Mobile

> **Версия протокола:** v1  
> **Транспорт:** REST (история, список диалогов) + WebSocket (realtime события)  
> **Аутентификация:** JWT Bearer (REST) / query-параметр `?token=` (WS)

---

## Оглавление

1. [Быстрый старт](#1-быстрый-старт)
2. [REST API](#2-rest-api)
3. [WebSocket протокол v1](#3-websocket-протокол-v1)
4. [Жизненный цикл сообщения](#4-жизненный-цикл-сообщения)
5. [Reconnect и Resync](#5-reconnect-и-resync)
6. [Идемпотентная отправка](#6-идемпотентная-отправка)
7. [Типовые сценарии с кодом](#7-типовые-сценарии-с-кодом)
8. [Коды ошибок](#8-коды-ошибок)
9. [Рекомендации по UX](#9-рекомендации-по-ux)

---

## 1. Быстрый старт

```
REST base URL:  https://api.example.com
WS URL:         wss://api.example.com/ws/chat/<conversation_id>/?token=<access_jwt>
```

Минимальный флоу открытия чата:
```
1. GET /api/chat/conversations/                 — список диалогов
2. GET /api/chat/conversations/<id>/messages/   — история сообщений (последние 50)
3. WSS /ws/chat/<id>/?token=<jwt>               — подключиться к realtime-каналу
4. Рисуем UI, слушаем события message.new
```

---

## 2. REST API

### Аутентификация

Все REST запросы требуют заголовок:
```
Authorization: Bearer <access_token>
```

---

### 2.1 Список диалогов

```
GET /api/chat/conversations/
```

**Ответ 200:**
```json
[
  {
    "id": 42,
    "companion": {
      "id": 7,
      "full_name": "Алибек Джаксыбеков",
      "avatar": "https://cdn.example.com/avatar.jpg",
      "phone_number": "+77071234567"
    },
    "last_message": {
      "id": 1337,
      "text": "Увидимся на корте!",
      "sender_id": 7,
      "created_at": "2026-05-04T09:15:00Z",
      "is_read": false,
      "status": "delivered"
    },
    "unread_count": 3,
    "updated_at": "2026-05-04T09:15:00Z"
  }
]
```

---

### 2.2 Начать диалог (или получить существующий)

```
POST /api/chat/conversations/start/
Content-Type: application/json

{ "user_id": 7 }
```

**Ответ 200** — возвращает объект диалога (как в п.2.1).  
**Ответ 403** — если пользователи не в друзьях.

---

### 2.3 История сообщений (cursor pagination)

```
GET /api/chat/conversations/<id>/messages/
```

| Параметр | Описание |
|----------|----------|
| `before_id=<id>` | Загрузить сообщения **старше** этого ID (скролл вверх) |
| `after_id=<id>` | Загрузить сообщения **новее** этого ID (resync после разрыва) |
| `limit=50` | Количество (макс 200) |

**Стратегия загрузки истории:**
```
Первая загрузка:  GET /messages/?limit=50           → получаем 50 последних
Скролл вверх:     GET /messages/?before_id=<id[0]>  → следующие 50 старше первого
```

**Ответ 200:**
```json
[
  {
    "id": 1330,
    "conversation": 42,
    "sender_id": 3,
    "text": "Привет!",
    "status": "read",
    "is_read": true,
    "client_message_id": "uuid-from-client",
    "created_at": "2026-05-04T08:00:00Z"
  },
  ...
]
```

Поля `status`:
| Значение | Смысл |
|----------|-------|
| `sent` | Сообщение сохранено на сервере |
| `delivered` | Получатель подключён к WS и видел его |
| `read` | Получатель явно прочитал (вызвал mark-read) |

---

### 2.4 Отправить сообщение (REST fallback)

> Используйте REST только как fallback при недоступности WS.  
> Основной способ отправки — через WebSocket (`message.send`).

```
POST /api/chat/conversations/<id>/messages/
Content-Type: application/json

{
  "text": "Привет!",
  "client_message_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

`client_message_id` — уникальный ID от клиента (UUID рекомендуется). Обеспечивает идемпотентность: повторный запрос с тем же ID вернёт оригинальное сообщение (200), не создав дубликат.

**Ответ 201** — создано:
```json
{
  "id": 1338,
  "sender_id": 3,
  "text": "Привет!",
  "status": "sent",
  "is_read": false,
  "client_message_id": "550e8400...",
  "created_at": "2026-05-04T09:20:00Z"
}
```

---

### 2.5 Пометить диалог прочитанным

```
POST /api/chat/conversations/<id>/read/
```

**Ответ 200:**
```json
{ "marked_read": 3 }
```

---

### 2.6 Бейдж непрочитанных (общий)

```
GET /api/chat/unread-count/
```

**Ответ 200:**
```json
{ "unread_count": 7 }
```

---

## 3. WebSocket протокол v1

### Подключение

```
wss://api.example.com/ws/chat/<conversation_id>/?token=<access_jwt>
```

Параметры URL:

| Параметр | Обязательный | Описание |
|----------|-------------|----------|
| `token` | ✅ | JWT access token |
| `last_seen` | ❌ | ID последнего известного сообщения (resync) |

---

### Формат фреймов

**Все сообщения** (входящие и исходящие) имеют структуру:
```json
{
  "v": 1,
  "type": "<event_type>",
  "payload": { ... }
}
```

---

### 3.1 Клиент → Сервер (входящие события)

#### message.send — отправить сообщение

```json
{
  "v": 1,
  "type": "message.send",
  "payload": {
    "text": "Текст сообщения",
    "client_message_id": "uuid-v4-here",
    "request_id": "req-abc123"
  }
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| `text` | string | ✅ | Текст (макс 4000 символов) |
| `client_message_id` | string | ❌ | UUID для идемпотентности (рекомендуется) |
| `request_id` | string | ❌ | Для сопоставления с ACK |

В ответ сервер пришлёт `ack` (отправителю) и `message.new` (всем в комнате).

---

#### message.read — прочитать сообщения

```json
{
  "v": 1,
  "type": "message.read",
  "payload": {}
}
```

Помечает все непрочитанные сообщения собеседника как прочитанные. Все участники получат событие `message.read`.

---

#### typing.start / typing.stop — индикатор набора текста

```json
{ "v": 1, "type": "typing.start", "payload": {} }
{ "v": 1, "type": "typing.stop",  "payload": {} }
```

---

### 3.2 Сервер → Клиент (исходящие события)

#### message.new — новое сообщение

```json
{
  "v": 1,
  "type": "message.new",
  "payload": {
    "message_id": 1338,
    "conversation_id": 42,
    "sender_id": 7,
    "text": "Привет!",
    "created_at": "2026-05-04T09:20:00.000Z",
    "status": "sent",
    "client_message_id": "uuid-v4-here"
  }
}
```

---

#### ack — подтверждение отправки (только отправителю)

```json
{
  "v": 1,
  "type": "ack",
  "payload": {
    "request_id": "req-abc123",
    "message_id": 1338,
    "status": "ok",
    "is_duplicate": false
  }
}
```

`is_duplicate: true` означает что сообщение с данным `client_message_id` уже существует — ID возвращён без создания нового.

---

#### message.read — кто-то прочитал сообщения

```json
{
  "v": 1,
  "type": "message.read",
  "payload": {
    "conversation_id": 42,
    "read_by_id": 7,
    "marked_count": 3
  }
}
```

---

#### typing.start / typing.stop — собеседник печатает

```json
{
  "v": 1,
  "type": "typing.start",
  "payload": {
    "conversation_id": 42,
    "user_id": 7,
    "user_name": "Алибек"
  }
}
```

```json
{
  "v": 1,
  "type": "typing.stop",
  "payload": {
    "conversation_id": 42,
    "user_id": 7
  }
}
```

---

#### error — ошибка обработки события

```json
{
  "v": 1,
  "type": "error",
  "payload": {
    "code": "rate_limit_exceeded",
    "message": "Слишком много запросов. Подождите."
  }
}
```

---

## 4. Жизненный цикл сообщения

```
Клиент A отправляет:
  message.send → [сервер сохраняет] → ack к A (status=ok)
                                     → message.new ко всем в комнате

Клиент B получает message.new:
  Сервер автоматически переводит статус: sent → delivered

Клиент B читает чат (скроллит вниз):
  message.read → [сервер обновляет] → message.read ко всем в комнате
                                    → Статус sent/delivered → read
```

**Диаграмма статусов:**
```
sent ──► delivered ──► read
         (WS получил)   (явно прочитал)
```

На Flutter: рисуй иконку статуса рядом с сообщением:
- `sent` → одна галочка (серая)
- `delivered` → две галочки (серые)  
- `read` → две галочки (синие)

---

## 5. Reconnect и Resync

При разрыве соединения (переключение сети, sleep телефона и т.д.):

1. Запомни ID последнего полученного сообщения (`last_seen_id`).
2. При переподключении передай `last_seen` в URL.
3. Сервер сам отправит все пропущенные сообщения как `message.new` события.

```
wss://api.example.com/ws/chat/42/?token=<jwt>&last_seen=1337
```

**Flutter пример (псевдокод):**
```dart
Future<void> reconnect() async {
  final lastSeen = await _messageRepo.getLastMessageId(conversationId);
  final url = 'wss://api.example.com/ws/chat/$conversationId/'
              '?token=$accessToken&last_seen=$lastSeen';
  _channel = WebSocketChannel.connect(Uri.parse(url));
  _channel.stream.listen(_onMessage, onDone: _scheduleReconnect);
}
```

**Стратегия экспоненциального backoff:**
```dart
int _reconnectAttempts = 0;

void _scheduleReconnect() {
  final delay = Duration(seconds: min(30, pow(2, _reconnectAttempts).toInt()));
  _reconnectAttempts++;
  Future.delayed(delay, reconnect);
}
```

---

## 6. Идемпотентная отправка

Генерируй `client_message_id` (UUID v4) на клиенте до отправки. Сохраняй его вместе с сообщением в локальной БД до получения `ack`.

```dart
Future<void> sendMessage(String text) async {
  final cmid = const Uuid().v4();
  
  // Сохраняем локально со статусом "отправка..."
  await _localDb.saveMessage(cmid, text, status: 'sending');
  
  _channel.sink.add(jsonEncode({
    'v': 1,
    'type': 'message.send',
    'payload': {
      'text': text,
      'client_message_id': cmid,
      'request_id': cmid,  // используем тот же ID для сопоставления ACK
    },
  }));
}

void _onMessage(dynamic raw) {
  final event = jsonDecode(raw);
  if (event['type'] == 'ack') {
    final cmid = event['payload']['request_id'];
    final msgId = event['payload']['message_id'];
    // Обновляем локально: cmid → server msgId, статус = sent
    _localDb.confirmMessage(cmid, msgId);
  }
  if (event['type'] == 'message.new') {
    // Рендерим новое сообщение
    _addToList(event['payload']);
  }
}
```

---

## 7. Типовые сценарии с кодом

### Открытие экрана чата

```dart
Future<void> openChat(int conversationId) async {
  // 1. Загружаем последние 50 сообщений через REST
  final history = await _api.getMessages(conversationId, limit: 50);
  _messages.addAll(history);
  
  // 2. Подключаем WS с last_seen для получения всего пропущенного
  final lastId = history.isEmpty ? 0 : history.last.id;
  await _connectWs(conversationId, lastSeenId: lastId);
  
  // 3. Помечаем прочитанными через WS
  _sendWsEvent('message.read', {});
}
```

### Загрузка старой истории (Pull-to-refresh / скролл вверх)

```dart
Future<void> loadOlder() async {
  if (_messages.isEmpty) return;
  final oldest = _messages.first.id;
  final older = await _api.getMessages(
    conversationId,
    beforeId: oldest,
    limit: 50,
  );
  _messages.insertAll(0, older);
}
```

### Обработка входящего события

```dart
void _handleWsEvent(Map<String, dynamic> event) {
  switch (event['type']) {
    case 'message.new':
      final payload = event['payload'];
      // Не добавляем если уже есть (по client_message_id)
      if (!_messages.any((m) => m.id == payload['message_id'])) {
        _messages.add(Message.fromWs(payload));
      }
      break;
    case 'message.read':
      // Обновляем статус у своих сообщений
      _markMessagesRead(event['payload']['read_by_id']);
      break;
    case 'typing.start':
      _showTypingIndicator(event['payload']['user_name']);
      break;
    case 'typing.stop':
      _hideTypingIndicator();
      break;
    case 'error':
      _handleError(event['payload']);
      break;
  }
}
```

---

## 8. Коды ошибок

### WebSocket close codes

| Код | Значение | Действие |
|-----|----------|----------|
| `4001` | Нет аутентификации | Обнови JWT, переподключись |
| `4003` | Нет доступа к диалогу | Показать ошибку пользователю |
| `4009` | Payload слишком большой | Уменьши текст сообщения |

### WS error event codes

| code | Значение |
|------|----------|
| `bad_format` | Неверная структура фрейма (нет v, type, payload) |
| `unknown_event` | Неизвестный тип события |
| `validation_error` | Текст пуст, слишком длинный или невалидный request_id |
| `rate_limit_exceeded` | Слишком много запросов — подожди и повтори |
| `server_error` | Внутренняя ошибка — сообщи в поддержку |

### REST коды

| Код | Значение |
|-----|----------|
| `400` | Невалидные данные запроса |
| `401` | JWT истёк или невалиден |
| `403` | Нет прав (не друзья) |
| `404` | Диалог не найден или нет доступа |
| `429` | Rate limit (если добавлен middleware) |

---

## 9. Рекомендации по UX

### Оптимистичное обновление UI

Не жди `ack` от сервера — сразу добавь сообщение в список со статусом "отправка":
```
[сообщение пользователя] ○  ← крутится/серый
```
После `ack` обновляй до реального ID и статуса `sent`:
```
[сообщение пользователя] ✓  ← одна галочка
```

### Typing indicator

- Показывай `typing.start` не дольше 5–10 секунд (на случай если `typing.stop` потеряется).
- Не отправляй `typing.start` чаще 1 раза в 2–3 секунды при вводе.

### Read receipts

- Вызывай `message.read` только когда экран чата действительно видим (`WidgetsBindingObserver.didChangeAppLifecycleState`).
- Обновляй статус галочек только для своих сообщений при получении события `message.read` от собеседника.

### Handling WS disconnect

Всегда показывай пользователю статус соединения. При разрыве — серый индикатор + автоматический reconnect.

---

## Зависимости на Flutter (pubspec.yaml)

```yaml
dependencies:
  web_socket_channel: ^2.4.0
  uuid: ^4.0.0
  dio: ^5.0.0        # для REST запросов
  sqflite: ^2.3.0    # для локального кэша сообщений (опционально)
```
