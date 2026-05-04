# Запуск бэкенда на сервере (с поддержкой чата / WebSocket)

> Ubuntu 22.04 LTS, Python 3.11, PostgreSQL 15, Redis 7

---

## 1. Установка системных зависимостей

```bash
sudo apt update && sudo apt upgrade -y

# Python, pip, venv
sudo apt install -y python3.11 python3.11-venv python3-pip

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Redis
sudo apt install -y redis-server

# Supervisor (для управления процессами)
sudo apt install -y supervisor

# Nginx (reverse proxy)
sudo apt install -y nginx
```

---

## 2. Redis — настройка и запуск

```bash
# Включить и запустить
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Проверить
redis-cli ping
# Должен вернуть: PONG
```

**Важно для продакшена** — в `/etc/redis/redis.conf`:
```
bind 127.0.0.1          # слушать только localhost
requirepass your_secret_redis_password
maxmemory 256mb
maxmemory-policy allkeys-lru
```

```bash
sudo systemctl restart redis-server
```

---

## 3. PostgreSQL — создать базу и пользователя

```bash
sudo -u postgres psql

CREATE USER padel_user WITH PASSWORD 'strong_password_here';
CREATE DATABASE padel_db OWNER padel_user;
GRANT ALL PRIVILEGES ON DATABASE padel_db TO padel_user;
\q
```

---

## 4. Проект — клонировать и настроить

```bash
cd /home/ubuntu
git clone https://github.com/Taymas-Padel/TayMas-Padel-Backend.git padel
cd padel

# Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Создать .env для продакшена
cp .env .env.production
nano .env.production
```

**`.env.production`** (заполни своими значениями):
```env
DEBUG=False
SECRET_KEY=your-very-secret-key-here-min-50-chars

ALLOWED_HOSTS=api.example.com,www.api.example.com

DB_NAME=padel_db
DB_USER=padel_user
DB_PASSWORD=strong_password_here
DB_HOST=localhost
DB_PORT=5432

# Redis (если пароль установлен)
REDIS_URL=redis://:your_secret_redis_password@127.0.0.1:6379

PAYMENT_PROVIDER=kaspi
KASPI_MERCHANT_ID=your_merchant_id
KASPI_SECRET_KEY=your_secret_key
```

---

## 5. Применить миграции и собрать статику

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings

# Миграции (включая новую миграцию чата 0002)
python manage.py migrate

# Статика (если есть)
python manage.py collectstatic --noinput

# Проверить что всё ок
python manage.py check --deploy
```

---

## 6. Daphne — ASGI сервер для HTTP + WebSocket

Daphne уже установлен (он в INSTALLED_APPS). Он заменяет Gunicorn/uWSGI для проектов с Django Channels.

```bash
# Тест запуска вручную
source venv/bin/activate
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

## 7. Supervisor — автозапуск и мониторинг

Создай файл конфигурации:

```bash
sudo nano /etc/supervisor/conf.d/padel.conf
```

```ini
[program:padel]
command=/home/ubuntu/padel/venv/bin/daphne
        -b 127.0.0.1
        -p 8000
        --proxy-headers
        config.asgi:application
directory=/home/ubuntu/padel
user=ubuntu
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/padel/daphne.err.log
stdout_logfile=/var/log/padel/daphne.out.log
environment=
    DJANGO_SETTINGS_MODULE="config.settings",
    PYTHONPATH="/home/ubuntu/padel"
```

```bash
# Создать папку для логов
sudo mkdir -p /var/log/padel
sudo chown ubuntu:ubuntu /var/log/padel

# Перечитать конфиги supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Запустить
sudo supervisorctl start padel

# Проверить статус
sudo supervisorctl status
```

---

## 8. Nginx — reverse proxy (HTTP + WS upgrade)

```bash
sudo nano /etc/nginx/sites-available/padel
```

```nginx
upstream padel_asgi {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # Размер тела запроса (для загрузки файлов)
    client_max_body_size 10M;

    # Таймаут для WebSocket соединений
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;

    location / {
        proxy_pass http://padel_asgi;
        proxy_http_version 1.1;

        # Обязательно для WebSocket upgrade
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/ubuntu/padel/staticfiles/;
        expires 30d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/padel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 9. SSL — Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com
sudo systemctl enable certbot.timer
```

---

## 10. Проверка работы WebSocket

```bash
# Установить wscat для теста
npm install -g wscat

# Подключиться (замени токен на реальный)
wscat -c "wss://api.example.com/ws/chat/1/?token=eyJ..."
```

После подключения отправить:
```json
{"v":1,"type":"message.send","payload":{"text":"Тест","request_id":"test-1"}}
```

Должны получить:
```json
{"v":1,"type":"ack","payload":{"request_id":"test-1","message_id":...,"status":"ok","is_duplicate":false}}
```

---

## 11. Мониторинг и логи

```bash
# Логи daphne
tail -f /var/log/padel/daphne.out.log
tail -f /var/log/padel/daphne.err.log

# Статус процесса
sudo supervisorctl status padel

# Redis мониторинг
redis-cli monitor  # все команды в realtime

# Количество активных WS ключей rate-limiting
redis-cli --scan --pattern 'ws_rl:*' | wc -l
```

---

## 12. Обновление деплоя

```bash
cd /home/ubuntu/padel
source venv/bin/activate

# Получить обновления
git pull origin main

# Установить новые зависимости (если появились)
pip install -r requirements.txt

# Применить миграции
python manage.py migrate

# Перезапустить сервис
sudo supervisorctl restart padel
```

---

## 13. Минимальные требования к серверу

| Ресурс | Минимум | Рекомендуется |
|--------|---------|---------------|
| CPU | 1 vCPU | 2+ vCPU |
| RAM | 1 GB | 2 GB |
| Диск | 20 GB SSD | 40 GB SSD |
| Redis RAM | 256 MB | 512 MB |
| OS | Ubuntu 22.04 | Ubuntu 22.04 |

---

## 14. Возможные проблемы и решения

### WebSocket не подключается (502)

Проверь что Nginx правильно проксирует upgrade-заголовки:
```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Redis connection refused

```bash
sudo systemctl status redis-server
redis-cli -a your_password ping
```

Убедись что `REDIS_URL` в `.env` совпадает с `requirepass` в redis.conf.

### Migration errors после обновления

```bash
python manage.py showmigrations chat
python manage.py migrate chat
```

### Daphne не стартует

```bash
sudo supervisorctl tail padel stderr
# Или вручную:
source venv/bin/activate
daphne -b 0.0.0.0 -p 8001 config.asgi:application
```
