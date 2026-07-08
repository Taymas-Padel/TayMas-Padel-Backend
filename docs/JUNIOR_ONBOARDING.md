# Онбординг разработчика: как поднять проект локально и залить изменения

> Проект: **TayMas Padel** — бэкенд падел-центра на Django 4.2 + DRF + Channels (WebSocket-чат).
> Стек: Python, PostgreSQL, Redis, Daphne (ASGI).
> Репозиторий: **https://github.com/Taymas-Padel/TayMas-Padel-Backend.git**

Порядок: сначала подними проект локально (разделы 1–8), убедись что работает, потом делай задачу (раздел 9), потом залей в git (раздел 10). На сервер изменения выкатывает тимлид.


---

## 1. Что нужно установить заранее

| Инструмент | Версия | Зачем |
|-----------|--------|-------|
| Python | 3.11+ | сам проект |
| PostgreSQL | 14+ | база данных |
| Redis | 6+ | WebSocket-чат (Channels) + кеш |
| Git | любой | клонирование/пуш |

**macOS (через Homebrew):**
```bash
brew install python postgresql@16 redis git
brew services start postgresql@16
brew services start redis
```

**Windows:** ставь Python с python.org, PostgreSQL с postgresql.org, Redis — через WSL2 (в Windows нативного Redis нет) или Memurai. Проще всего работать в WSL2 (Ubuntu).

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip postgresql redis git
sudo systemctl start postgresql redis
```

---

## 2. Клонировать репозиторий

```bash
git clone https://github.com/Taymas-Padel/TayMas-Padel-Backend.git
cd TayMas-Padel-Backend
```

---

## 3. Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Создать базу данных PostgreSQL

```bash
# зайти в psql
psql postgres        # или: sudo -u postgres psql

# внутри psql выполнить:
CREATE USER padel_user WITH PASSWORD 'padel_pass';
CREATE DATABASE padel_db OWNER padel_user;
GRANT ALL PRIVILEGES ON DATABASE padel_db TO padel_user;
\q
```

---

## 5. Файл `.env` (в корне проекта, рядом с `manage.py`)

Проект читает настройки из `.env`. Создай файл `.env` со следующим содержимым (для локальной разработки):

```ini
# --- Django ---
SECRET_KEY=dev-local-secret-key-change-me-1234567890
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# --- PostgreSQL (как в разделе 4) ---
DB_NAME=padel_db
DB_USER=padel_user
DB_PASSWORD=padel_pass
DB_HOST=localhost
DB_PORT=5432

# --- Redis (для чата) ---
REDIS_URL=redis://127.0.0.1:6379

# --- Оплата (заглушка для разработки) ---
PAYMENT_PROVIDER=stub

# --- SMS мастер-код (для входа без реального SMS) ---
SMS_MASTER_CODE=000000
```

> `SECRET_KEY` можно оставить как есть для локалки. `.env` в git не коммитится (он в `.gitignore`).

---

## 6. Миграции и суперпользователь

```bash
python manage.py migrate
python manage.py createsuperuser      # создай админа (email/пароль)
```

---

## 7. Запуск проекта

```bash
python manage.py runserver
```

> В проекте установлен `daphne`, поэтому `runserver` умеет и обычный HTTP, и WebSocket (чат) — отдельно ничего запускать не надо. Redis при этом должен быть запущен.

Проект поднимется на `http://127.0.0.1:8000`.

---

## 8. Проверка что всё работает

Открой в браузере:
- `http://127.0.0.1:8000/swagger/` — документация API (должна открыться).
- `http://127.0.0.1:8000/admin/` — админка (войти под суперюзером).
- `http://127.0.0.1:8000/api/courts/` — список кортов (может быть пустым `[]` — это ок).

Если всё открывается — проект поднят. Данные (корты, услуги и т.д.) можно создать через админку или скриптами из папки `scripts/`.

---

## 9. Задача

**Основная задача — завести домен + HTTPS для API и перевести фронт на защищённый адрес.**

Подробное пошаговое ТЗ по этой части — в файле **`docs/TZ_DOMAIN_HTTPS.md`** (в этом же репозитории). Там:
- реальные пути и настройки сервера,
- шаги DNS → Nginx → certbot,
- какие правки в коде нужны (`.env`, `settings.py`),
- проверки, что всё работает и ничего не сломано.

> Доступы к серверу (SSH) и панели домена (PS.kz) — тимлид пришлёт в личку. Пароли/ключи никуда не коммитить.

Изменения в **коде** (например `config/settings.py`) делай локально, проверяй, что проект запускается, и заливай в git (раздел 10). Изменения на **сервере** (DNS, Nginx, certbot) — делаются напрямую по SSH, они в git не попадают.

---

## 10. Как залить изменения в git

```bash
# создать ветку под задачу
git checkout -b feature/domain-https

# посмотреть что изменил
git status
git diff

# добавить и закоммитить (осмысленное сообщение)
git add <изменённые_файлы>
git commit -m "feat: настройки под домен taymaspadel.newlevelhub.kz (CSRF/ALLOWED_HOSTS)"

# запушить ветку
git push -u origin feature/domain-https
```

Дальше:
- открой Pull Request на GitHub (ветка → `main`) и напиши тимлиду на ревью,
- **или**, если договоритесь, тимлид сам смёржит.

> ⚠️ НЕ пушь напрямую в `main` без согласования. НЕ коммить `.env`, пароли, ключи.

После мёржа в `main` **тимлид сам зайдёт на сервер и выполнит `git pull` + перезапуск** — тебе на сервере код катить не нужно.

---

## 11. Частые проблемы

| Проблема | Решение |
|----------|---------|
| `django.db.utils.OperationalError` при `migrate` | PostgreSQL не запущен или неверные данные в `.env` (DB_*) |
| Ошибки про Redis / чат не работает | Redis не запущен: `brew services start redis` / `sudo systemctl start redis` |
| `ALLOWED_HOSTS` ошибка при старте | проверь, что в `.env` есть строка `ALLOWED_HOSTS=localhost,127.0.0.1` |
| `SECRET_KEY` ошибка | в `.env` должна быть непустая строка `SECRET_KEY=...` |
| `ModuleNotFoundError` | не активировал venv или не сделал `pip install -r requirements.txt` |

---

## 12. Правила

- `.env`, пароли, ключи — **никогда** не коммитить.
- Работать в отдельной ветке, не пушить в `main` без ревью.
- Серверные конфиги менять только с бэкапом (см. `TZ_DOMAIN_HTTPS.md`).
- Если что-то непонятно или рискованно — спросить тимлида, не «чинить наугад».
