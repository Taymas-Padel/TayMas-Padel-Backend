# Chat API — документация для Flutter-разработчика

Система личных сообщений (1-на-1) между друзьями. Только текст, без вложений.

**Базовый URL:** `{BASE_URL}/api/chat/`  
**Авторизация:** `Authorization: Bearer <access_token>` (JWT)

---

## Архитектура: как сделать «быструю» доставку

Бэкенд предоставляет **WebSocket API** для реального времени и **REST API** для загрузки истории и фоллбека. 

Для полноценной работы (realtime доставка, typing индикаторы, статусы прочитанности) рекомендуется использовать WebSocket. Если WebSocket по какой-то причине недоступен (обрыв сети), приложение должно временно перейти на REST API (short polling с параметром `after`).

### Вариант 1: WebSocket (Основной, Рекомендуемый)

**URL для подключения:**
`ws://{HOST}/ws/chat/<conversation_id>/?token=<jwt_access_token>`

Протокол обмена (строгий формат v1):
Все сообщения оборачиваются в объект с версией протокола, типом события и полезной нагрузкой.

**Отправка сообщения клиентом:**
```json
{
  "v": 1,
  "type": "message.send",
  "payload": {
    "text": "Привет!",
    "request_id": "уникальный_id_фронта"
  }
}
```

**Получение подтверждения отправки (ACK) от сервера:**
```json
{
  "v": 1,
  "type": "ack",
  "payload": {
    "request_id": "уникальный_id_фронта",
    "message_id": 158,
    "status": "ok"
  }
}
```

> Более подробно про события WebSocket (новые сообщения, прочитанность, печать собеседника) читай в файле [CHAT_WEBSOCKET_FLOW.md](./CHAT_WEBSOCKET_FLOW.md).

### Вариант 2: REST API (Fallback / Альтернатива)

```
┌─────────────────────────────────────────────────┐
│  Экран списка чатов                             │
│  Polling: GET /conversations/  каждые 5 сек     │
│  (обновляет last_message + unread_count)        │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Экран диалога (открыт)                         │
│  Polling: GET /conversations/<id>/messages/     │
│           ?after=<last_msg_id>  каждые 2 сек    │
│  (забирает только новые сообщения)              │
│  При входе: POST /conversations/<id>/read/      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Бейдж на иконке чата (любой экран)             │
│  Polling: GET /unread-count/  каждые 10 сек     │
└─────────────────────────────────────────────────┘
```

**Почему это быстро:**
- Запрос `?after=<id>` возвращает 0–N сообщений за ~десятки миллисекунд (один SQL-запрос по индексу).
- При polling каждые 2 сек задержка доставки: максимум 2 сек.
- Запрос лёгкий (~200 байт при 0 новых сообщений), трафик минимален.

---

## Эндпоинты

### 1. Список диалогов

```
GET /api/chat/conversations/
```

Возвращает все диалоги текущего пользователя, отсортированные по последнему сообщению.

**Ответ 200:**

```json
[
  {
    "id": 1,
    "companion": {
      "id": 42,
      "full_name": "Алексей Петров",
      "avatar": "/media/avatars/alex.jpg",
      "phone_number": "+77001234567"
    },
    "last_message": {
      "id": 155,
      "text": "Играем в 18:00?",
      "sender_id": 42,
      "created_at": "2026-02-23T15:30:00+05:00",
      "is_read": false
    },
    "unread_count": 3,
    "updated_at": "2026-02-23T15:30:00+05:00"
  }
]
```

- `companion` — собеседник (не ты).  
- `last_message` — `null`, если сообщений ещё не было.  
- `unread_count` — количество непрочитанных сообщений от собеседника.

---

### 2. Начать / открыть диалог

```
POST /api/chat/conversations/start/
Content-Type: application/json

{ "user_id": 42 }
```

Создаёт диалог с указанным пользователем (или возвращает существующий). Работает только с друзьями.

**Ответ 200:** объект диалога (формат как в списке).

**Ошибки:**

| Код | Когда                                |
|-----|--------------------------------------|
| 400 | `user_id` не передан или = себе      |
| 403 | Пользователь не в друзьях            |
| 404 | Пользователь не найден               |

**Когда вызывать:** при нажатии «Написать» у друга.

---

### 3. Получить сообщения диалога

```
GET /api/chat/conversations/{conv_id}/messages/
GET /api/chat/conversations/{conv_id}/messages/?after=155
GET /api/chat/conversations/{conv_id}/messages/?after=155&limit=100
```

**Query-параметры:**

| Параметр | Тип | По умолчанию | Описание                                           |
|----------|-----|-------------|----------------------------------------------------|
| `after`  | int | —           | ID последнего полученного сообщения (id > after)  |
| `limit`  | int | 50          | Количество сообщений (макс 200)                   |

**Ответ 200:**

```json
[
  {
    "id": 156,
    "conversation": 1,
    "sender_id": 5,
    "text": "Давай!",
    "is_read": false,
    "created_at": "2026-02-23T15:31:12+05:00"
  }
]
```

Сообщения отсортированы по `created_at` ASC (старые → новые).

---

### 4. Отправить сообщение

```
POST /api/chat/conversations/{conv_id}/send/
Content-Type: application/json

{ "text": "Привет! Играем сегодня?" }
```

**Ограничения:**
- Текст не может быть пустым.
- Максимальная длина — 4000 символов.

**Ответ 201:**

```json
{
  "id": 158,
  "conversation": 1,
  "sender_id": 5,
  "text": "Привет! Играем сегодня?",
  "is_read": false,
  "created_at": "2026-02-23T15:32:00+05:00"
}
```

**Совет:** после отправки сразу добавь сообщение в локальный список (оптимистичный UI), не жди следующий polling.

---

### 5. Пометить прочитанными

```
POST /api/chat/conversations/{conv_id}/read/
```

Помечает все непрочитанные сообщения **от собеседника** в этом диалоге как прочитанные.

**Ответ 200:**

```json
{ "marked_read": 3 }
```

**Когда вызывать:**
- При открытии экрана диалога.
- В каждом цикле polling, если пришли новые сообщения.

---

### 6. Общий счётчик непрочитанных сообщений

```
GET /api/chat/unread-count/
```

**Ответ 200:**

```json
{ "unread_count": 7 }
```

**Использование:** бейдж на иконке «Чат» в нижней навигации. Polling каждые 10 сек на любом экране.

---

## Уведомления о новых сообщениях

При каждом новом сообщении бэкенд создаёт **уведомление** типа `MESSAGE` для получателя.

Модель уведомления уже используется в приложении (раздел «Оповещения»), поэтому для чата просто добавлен новый тип.

### Формат уведомления

Пример объекта из `GET /api/notifications/`:

```json
{
  "id": 501,
  "notification_type": "MESSAGE",
  "type_label": "Сообщение",
  "title": "Сообщение от Иван Иванов",
  "body": "Привет! Играем сегодня вечером?…",
  "is_read": false,
  "data": {
    "conversation_id": 1,
    "message_id": 158,
    "sender_id": 5
  },
  "created_at": "2026-02-23T15:32:00+05:00"
}
```

- `notification_type = "MESSAGE"` — можно фильтровать уведомления по этому типу.
- `type_label = "Сообщение"` — уже подготовленная строка для UI.
- `data.conversation_id` — ID диалога.
- `data.message_id` — ID сообщения.
- `data.sender_id` — ID отправителя.

### Эндпоинты уведомлений

Уведомления общие для всего приложения (брони, друзья, чат и т.д.), для чата используем тот же API:

- `GET /api/notifications/?type=MESSAGE` — только уведомления о новых сообщениях.
- `GET /api/notifications/unread-count/` — общий счётчик непрочитанных уведомлений (включая чат, брони и т.д.).
- `POST /api/notifications/{id}/read/` — пометить конкретное уведомление прочитанным.
- `POST /api/notifications/read-all/` — пометить все уведомления прочитанными.

### Рекомендуемое поведение Flutter-клиента

- При получении push (FCM) про новое сообщение (если будет подключен FCM), в payload можно передавать `conversation_id` и сразу открывать нужный диалог.
- При открытии приложения из раздела «Оповещения»:
  - Если `notification_type == "MESSAGE"` и есть `data.conversation_id`, нужно открыть экран диалога с этим `conversation_id`.
  - Параллельно можно обновить список сообщений через `GET /api/chat/conversations/{conv_id}/messages/`.

---

## Flutter: пример реализации polling

### ChatService (Dart)

```dart
class ChatService {
  final Dio _dio;
  Timer? _pollTimer;
  int? _lastMessageId;

  // Начать polling сообщений в открытом диалоге
  void startPolling(int convId, Function(List<Message>) onNewMessages) {
    _pollTimer = Timer.periodic(Duration(seconds: 2), (_) async {
      final url = '/api/chat/conversations/$convId/messages/'
          + (_lastMessageId != null ? '?after=$_lastMessageId' : '');
      final res = await _dio.get(url);
      final messages = (res.data as List).map((m) => Message.fromJson(m)).toList();
      if (messages.isNotEmpty) {
        _lastMessageId = messages.last.id;
        onNewMessages(messages);
        // Пометить прочитанными
        _dio.post('/api/chat/conversations/$convId/read/');
      }
    });
  }

  // Пример интеграции WebSocket
  void connectWebSocket(int convId, String token) {
    final wsUrl = 'ws://api.example.com/ws/chat/$convId/?token=$token';
    final channel = IOWebSocketChannel.connect(Uri.parse(wsUrl));
    
    channel.stream.listen((message) {
      final data = jsonDecode(message);
      if (data['v'] != 1) return;
      
      switch (data['type']) {
        case 'message.new':
          // новое сообщение от собеседника
          break;
        case 'ack':
          // сообщение доставлено на сервер
          break;
      }
    });
    
    // Отправка
    channel.sink.add(jsonEncode({
      "v": 1,
      "type": "message.send",
      "payload": {
        "text": "Привет",
        "request_id": "test-1"
      }
    }));
  }

  void stopPolling() {
    _pollTimer?.cancel();
  }

  // Отправить сообщение
  Future<Message> send(int convId, String text) async {
    final res = await _dio.post(
      '/api/chat/conversations/$convId/send/',
      data: {'text': text},
    );
    final msg = Message.fromJson(res.data);
    _lastMessageId = msg.id;
    return msg;
  }
}
```

### Оптимистичный UI при отправке

```dart
void onSendPressed() {
  final text = _controller.text.trim();
  if (text.isEmpty) return;
  _controller.clear();

  // 1. Сразу показываем в списке (без задержки)
  final tempMsg = Message(
    id: -1, // временный
    senderId: myUserId,
    text: text,
    createdAt: DateTime.now(),
    isRead: false,
  );
  setState(() => _messages.add(tempMsg));
  _scrollToBottom();

  // 2. Отправляем на сервер
  chatService.send(convId, text).then((realMsg) {
    setState(() {
      _messages.remove(tempMsg);
      _messages.add(realMsg);
    });
  });
}
```

---

## Экраны в приложении

### Экран 1: Список чатов

- Запрос: `GET /api/chat/conversations/`
- Показывать: аватар собеседника, имя, текст последнего сообщения, время, бейдж unread.
- Нажатие → экран диалога.
- Если диалогов нет → «У вас пока нет сообщений».
- Кнопка «Новый чат» → выбрать друга из списка → `POST /api/chat/conversations/start/`.

### Экран 2: Диалог

- При открытии: `GET .../messages/` (без `after` — загрузить историю) + `POST .../read/`.
- Polling каждые 2 сек с `?after=<last_id>`.
- Поле ввода внизу → `POST .../send/`.
- Сообщения свои — справа (синие), чужие — слева (серые).
- При уходе с экрана → `stopPolling()`.

### Бейдж

- На иконке «Чат» в BottomNavigationBar.
- `GET /api/chat/unread-count/` каждые 10 сек.
- Если `unread_count > 0` — показать число; если 0 — скрыть.

---

## Коды ошибок

| Код | Описание                                          |
|-----|---------------------------------------------------|
| 400 | Пустой текст, нет `user_id`, превышена длина      |
| 403 | Не друзья (при `start`)                           |
| 404 | Диалог/пользователь не найден или нет доступа     |

---

## Ограничения и правила

1. **Только друзья** — начать диалог можно только с пользователем, у которого `FriendRequest.status = ACCEPTED`.
2. **Только текст** — без фото, файлов, голосовых.
3. **Максимум 4000 символов** на сообщение.
4. **Удаление сообщений** — пока не реализовано.
5. **Групповые чаты** — пока не реализовано (только 1-на-1).

