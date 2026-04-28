# WebSocket Chat - Quick Start

## Статус реализации

✅ **Completed:**
- Production WebSocket consumer с JWT аутентификацией (`chat/consumers.py`)
- WebSocket URL routing (`chat/routing.py`)
- ASGI server configuration (`config/asgi.py`)
- Redis channel layer configuration (`config/settings.py`)
- Документация WS protocol (`docs/CHAT_WEBSOCKET_FLOW.md`)
- requirements.txt обновлен (channels, channels-redis, daphne)

---

## Запуск локально

### 1. Убедиться что Redis работает

```bash
redis-cli ping
# Ответ: PONG
```

### 2. Запустить Daphne вместо `manage.py runserver`

```bash
cd /Users/arhat/TayMas-Padel/TayMas-Padel-Backend
.venv/bin/python -m daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

**Вывод должен быть:**
```
2026-04-27 15:30:00 - Daphne(8000) starting up
2026-04-27 15:30:00 - Listening on TCP address 127.0.0.1:8000
2026-04-27 15:30:00 - Listening on unix socket /tmp/daphne.sock
```

### 3. Отдельно: Frontend вив

```bash
cd /Users/arhat/TayMas-Padel/TayMas-Padel-Frontend
npm run dev  # или npm run build
```

**ВАЖНО:** Обновить proxy в `vite.config.ts` на локальный backend:

```typescript
proxy: {
  '/api': 'http://localhost:8000',
  '/ws': {
    target: 'ws://localhost:8000',
    ws: true
  }
}
```

---

## Тестирование WebSocket

### Способ 1: wscat (быстро)

```bash
npm install -g wscat

# 1. Получить JWT токен
curl -X POST http://127.0.0.1:8000/api/auth/crm/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' 

# Ответ: {"access":"eyJ0eX...", "refresh":"..."}

# 2. Подключиться к WebSocket
wscat -c "ws://127.0.0.1:8000/ws/chat/1/?token=eyJ0eX..."

# 3. Отправить сообщение
> {"type":"message.new","text":"Hello World"}

# 4. Получить ответ (в другом терминале то же самое для второго пользователя)
< {"type":"message.new","message_id":123,"sender_id":1,"text":"Hello World","created_at":"..."}
```

### Способ 2: Python (более полный тест)

```python
import asyncio
import websockets
import json

async def test_ws_chat():
    token = "eyJ0eX..."  # из POST /api/auth/crm/login/
    
    async with websockets.connect(
        f"ws://127.0.0.1:8000/ws/chat/1/?token={token}"
    ) as ws:
        # Отправить сообщение
        await ws.send(json.dumps({
            "type": "message.new",
            "text": "Test message"
        }))
        
        # Получить ответ
        response = await ws.recv()
        print("Server response:", json.loads(response))
        
        # Отправить typing event
        await ws.send(json.dumps({
            "type": "typing.start"
        }))

asyncio.run(test_ws_chat())
```

### Способ 3: Frontend (React)

Примерный код в `src/api/chat.ts`:

```typescript
export class ChatWebSocket {
  private ws: WebSocket | null = null
  
  async connect(conversationId: number, token: string) {
    return new Promise((resolve, reject) => {
      const url = `ws://localhost:8000/ws/chat/${conversationId}/?token=${token}`
      
      this.ws = new WebSocket(url)
      
      this.ws.onopen = () => {
        console.log('✅ WebSocket connected')
        resolve(this.ws)
      }
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        console.log('📨 Received:', data)
        this.handleMessage(data)
      }
      
      this.ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        reject(error)
      }
      
      this.ws.onclose = () => {
        console.warn('⚠️ WebSocket disconnected')
      }
    })
  }
  
  sendMessage(text: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'message.new',
        text
      }))
    }
  }
  
  private handleMessage(data: any) {
    switch (data.type) {
      case 'message.new':
        // Показать сообщение в UI
        break
      case 'typing.start':
        // Показать "печатает..."
        break
    }
  }
}
```

---

## Проверка успеха

### Критерии приёма (Acceptance Criteria)

- ✅ **< 1s message delivery** на локальной сети
  ```
  Время: отправка WS → сохранение в БД → broadcast через Redis → получение клиентом
  Целевое: < 1 сек на 127.0.0.1
  Проверка: wscat test или логирование timestamps
  ```

- ✅ **WS client recovery** при разрыве соединения
  ```
  Сценарий: закрыть WS → клиент переподключается → продолжить отправку
  Проверка: kill -9 процесс или выключить сеть → client reconnects
  ```

- ✅ **Документирован WS flow**
  ```
  Файл: docs/CHAT_WEBSOCKET_FLOW.md
  Содержит: архитектуру, события, API endpoints, deploy, troubleshooting
  ```

---

## Интеграция в Production

Когда готовы:

1. **Развернуть на сервер**
   ```bash
   scp requirements.txt user@server:/app/
   ssh user@server "cd /app && pip install -r requirements.txt"
   ```

2. **Настроить ASGI server** (Systemd или Docker)
   ```ini
   [Service]
   ExecStart=/app/.venv/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application
   ```

3. **SSL для WSS**
   ```nginx
   location /ws/ {
       proxy_pass http://127.0.0.1:8000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```

4. **Redis** должен быть доступен через network (не localhost)

---

## Отладка

### Логирование

```python
# config/settings.py
import logging
logging.basicConfig(level=logging.DEBUG)

# chat/consumers.py
logger = logging.getLogger(__name__)
logger.info(f"User {user.id} connected to conversation {self.conversation_id}")
```

### Redis мониторинг

```bash
redis-cli
> SUBSCRIBE "asgi:chat_1"  # Слушать события группы chat_1
> KEYS "asgi:*"            # Все каналы
```

### Django ORM логи

```python
# settings.py
LOGGING = {
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {'handlers': ['console'], 'level': 'DEBUG'},
    }
}
```

---

## Известные проблемы

| Проблема | Симптом | Решение |
|----------|---------|---------|
| "Channel layer not configured" | WebSocket не отправляет | `redis-cli ping` → запустить Redis |
| JWT token invalid | 4001 Close code | Обновить token через refresh endpoint |
| "User is not conversation member" | 4003 Close code | Проверить conversation_id и user membership |
| Message не сохраняется в БД | Сообщение приходит но потом исчезает | Проверить logs → обычно ошибка в `_save_message()` |
| "Connection refused" | Не подключается к WebSocket | Проверить что Daphne запущен на 8000 |

