# Деплой на VPS (AlmaLinux 9)

> Стек: Django 4.2 + PostgreSQL + Gunicorn + Nginx

---

## 1. Подготовка сервера

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git nginx postgresql-server postgresql-contrib

# инициализация PostgreSQL
sudo postgresql-setup --initdb --unit postgresql
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

---

## 2. База данных (PostgreSQL)

```bash
sudo -u postgres psql
```
```sql
CREATE USER padel_user WITH PASSWORD 'СЛОЖНЫЙ_ПАРОЛЬ';
CREATE DATABASE padel_db OWNER padel_user;
GRANT ALL PRIVILEGES ON DATABASE padel_db TO padel_user;
\q
```

---

## 3. Загрузка кода

```bash
sudo mkdir -p /opt && cd /opt
sudo mkdir -p padel
sudo chown "$USER":"$USER" /opt/padel
cd /opt/padel

# сюда подставь URL своего репозитория
git clone https://github.com/YOUR_REPO/padel_project.git .
```

---

## 4. Виртуальное окружение и зависимости

На AlmaLinux модуль `venv` уже встроен в Python, отдельный пакет `python3-virtualenv` не нужен.

```bash
cd /opt/padel
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Переменные окружения `.env`

Создай файл `/opt/padel/.env`:

```ini
# ---- Django ----
SECRET_KEY=<сгенерируй: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False
ALLOWED_HOSTS=<IP_сервера>,<домен>

# ---- БД PostgreSQL ----
DB_NAME=padel_db
DB_USER=padel_user
DB_PASSWORD=СЛОЖНЫЙ_ПАРОЛЬ
DB_HOST=localhost
DB_PORT=5432

# ---- Медиа/статика ----
# Директории создаются ниже (collectstatic)

# ---- Оплата (пока заглушка) ----
PAYMENT_PROVIDER=stub
KASPI_MERCHANT_ID=
KASPI_SECRET_KEY=

# ---- SMS мастер-код (ТОЛЬКО разработка, УБРАТЬ на проде!) ----
# SMS_MASTER_CODE=000000
```

> ⚠️ В продакшне **уберите** `SMS_MASTER_CODE` — иначе любой сможет войти с кодом 000000.

---

## 6. Настройка `config/settings.py` для прода

Добавь в `settings.py` чтение DB из `.env`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'padel_db'),
        'USER': os.environ.get('DB_USER', 'padel_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
```

---

## 7. Миграции, статика, суперпользователь

```bash
cd /opt/padel
source venv/bin/activate

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## 8. Gunicorn — systemd сервис

Создай файл `/etc/systemd/system/padel.service`:

```ini
[Unit]
Description=Padel Project Gunicorn
After=network.target

[Service]
User=almalinux
Group=nginx
WorkingDirectory=/opt/padel
EnvironmentFile=/opt/padel/.env
ExecStart=/opt/padel/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/padel.sock \
    --access-logfile /var/log/padel/access.log \
    --error-logfile /var/log/padel/error.log \
    config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo mkdir -p /var/log/padel
sudo chown almalinux:nginx /var/log/padel
sudo chown -R almalinux:nginx /opt/padel
sudo systemctl daemon-reload
sudo systemctl enable padel
sudo systemctl start padel
sudo systemctl status padel
```

---

## 9. Nginx конфиг

На AlmaLinux виртуальные хосты обычно лежат в `/etc/nginx/conf.d/`.

Создай `/etc/nginx/conf.d/padel.conf`:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    client_max_body_size 20M;

    location /static/ {
        alias /opt/padel/static/;
        expires 30d;
    }

    location /media/ {
        alias /opt/padel/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://unix:/run/padel.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 10. HTTPS (Let's Encrypt)

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
sudo systemctl reload nginx
```

---

## 11. CORS для мобилки

В `config/settings.py` добавь IP/домен сервера:

```python
CORS_ALLOWED_ORIGINS = [
    "https://YOUR_DOMAIN",
]
# Или для разработки мобилки (временно):
# CORS_ALLOW_ALL_ORIGINS = True
```

---

## 12. Обновление кода (деплой новой версии)

```bash
cd /opt/padel
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart padel
```

---

## 13. Чеклист перед запуском

- [ ] `DEBUG=False` в `.env`
- [ ] `SECRET_KEY` — длинный случайный ключ (не дефолтный!)
- [ ] `ALLOWED_HOSTS` — домен и IP сервера
- [ ] `SMS_MASTER_CODE` — **убрано** из `.env`
- [ ] `PAYMENT_PROVIDER` — `stub` (пока), `kaspi` после подключения
- [ ] База данных PostgreSQL настроена
- [ ] `collectstatic` выполнен
- [ ] Nginx обслуживает `/static/` и `/media/`
- [ ] Gunicorn запущен через systemd
- [ ] HTTPS настроен через Let's Encrypt
- [ ] Суперпользователь создан
- [ ] FCM (Firebase) настроен если нужны пуш-уведомления

---

## 14. Структура файлов на сервере

```
/opt/padel/
├── config/              # Настройки Django
├── users/               # Аутентификация, профили
├── courts/              # Корты
├── bookings/            # Бронирования
├── memberships/         # Абонементы
├── lobby/               # Поиск партнёров (лобби)
├── gamification/        # ELO, матчи, лидерборд
├── friends/             # Друзья и лента
├── notifications/       # Уведомления
├── payments/            # Платёжная абстракция
├── finance/             # История транзакций
├── media/               # Загруженные файлы
├── static/              # collectstatic output
├── venv/                # Python окружение
├── .env                 # Секреты (НЕ в git!)
├── requirements.txt     # Зависимости
├── manage.py
├── test_mobile_api.py   # Тест эндпоинтов
├── API_FOR_FRONTEND.md  # Документация API
└── DEPLOY.md            # Этот файл
```

---

## Быстрая проверка после деплоя

```bash
# Проверить что сервер отвечает
curl https://YOUR_DOMAIN/api/courts/

# Запустить тест всех эндпоинтов (на сервере)
cd /var/www/padel && source venv/bin/activate
# Поменяй BASE в test_mobile_api.py на https://YOUR_DOMAIN
python test_mobile_api.py
```
