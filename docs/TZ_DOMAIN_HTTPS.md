# ТЗ: Поддомен + HTTPS для API (taymaspadel.newlevelhub.kz)

> Исполнитель: разработчик (junior) — делает всё на сервере (DNS, nginx, certbot).
> Тимлид — правит код/`.env` и деплоит, делает финальную проверку.
> Цель: завести поддомен `taymaspadel.newlevelhub.kz`, поднять на нём валидный HTTPS и перевести фронт (веб на Vercel/локально + мобилка) на `https://` и `wss://`.

---

## 0. Исходное состояние сервера (проверено)

- ОС: **AlmaLinux 9.7**
- Бэкенд **уже работает** по `http://213.155.23.227` и `https://213.155.23.227` (самоподписанный серт).
- Приложение: сервис **`padel`** — Daphne (ASGI) на `127.0.0.1:8001` → вебсокеты (`wss://`) поддерживаются.
- Nginx, PostgreSQL, Redis — запущены и работают.
- **certbot ещё НЕ установлен** — джун поставит.

**Реальные пути на сервере:**
| Что | Путь |
|-----|------|
| Nginx-конфиг сайта | `/etc/nginx/conf.d/padel.conf` |
| Проект Django | `/opt/padel/padel_project` |
| venv | `/opt/padel/venv` |
| `.env` приложения | `/opt/padel/padel_project/.env` |
| systemd-сервис | `padel` (перезапуск: `sudo systemctl restart padel`) |
| Существующий самоподписанный серт (на IP) | `/etc/ssl/padel/padel.crt` / `.key` |

> Джун может **начинать сразу** — ждать деплоя не нужно.

---

## 1. Доступы (получить у тимлида ОТДЕЛЬНО, не хранить в этом файле)

- SSH: `almalinux@213.155.23.227`, порт `22`, пароль — в личке. root: `sudo -i` (обычно не нужен, у команд есть `sudo`).
- Панель PS.kz (домен/DNS) — доступ в личке.
- Домен: `newlevelhub.kz`. Создаём поддомен: `taymaspadel.newlevelhub.kz`.

> ⚠️ Логины/пароли/ключи НЕ коммитить в git и НЕ вставлять в этот файл.

---

## 2. Зоны ответственности и порядок

| # | Задача | Кто |
|---|--------|-----|
| 1 | DNS-запись поддомена | **Джун** |
| 2 | Nginx: добавить домен в `server_name` (порт 80) | **Джун** |
| 3 | HTTPS через certbot | **Джун** |
| 4 | `.env`: `ALLOWED_HOSTS` | **Тимлид** |
| 5 | `settings.py`: CORS/CSRF | **Тимлид** |
| 6 | Фронт: baseUrl + `wss://` | **Тимлид** |

**Порядок:** Джун 1→2→3 → пишет тимлиду «DNS + HTTPS готовы» → Тимлид 4→5→6 и деплоит → совместная проверка (раздел 8–9).

> До шага 4 открытие `https://taymaspadel.newlevelhub.kz/api/...` будет отдавать `400 Bad Request (DisallowedHost)` — это НОРМАЛЬНО (домен ещё не в `ALLOWED_HOSTS`). Джуну чинить не нужно.

---

## 3. Шаг 1 (ДЖУН) — DNS в панели PS.kz

1. PS.kz → домен `newlevelhub.kz` → DNS-записи.
2. Создать **A-запись**: хост `taymaspadel`, тип `A`, значение `213.155.23.227`, TTL по умолчанию.
3. Сохранить.

**Проверка:**
```bash
dig +short taymaspadel.newlevelhub.kz
# ожидаем: 213.155.23.227
```
Дальше идти только когда вернётся правильный IP (5–30 мин).

---

## 4. Шаг 2 (ДЖУН) — Nginx: добавить домен

> ⚠️ Только ДОБАВИТЬ имя домена. Ничего не удалять. Самоподписанный 443-блок на IP не трогать — certbot сам всё сделает.

```bash
ssh almalinux@213.155.23.227
sudo cp /etc/nginx/conf.d/padel.conf /etc/nginx/conf.d/padel.conf.bak   # бэкап (обязательно!)
sudo nano /etc/nginx/conf.d/padel.conf
```

Найти **блок с `listen 80;`** и в его строке `server_name` добавить домен (существующий IP оставить):
```nginx
server_name taymaspadel.newlevelhub.kz 213.155.23.227;
```

Проверить и применить — **только если проверка успешна**:
```bash
sudo nginx -t
sudo systemctl reload nginx
```
Если `nginx -t` ругается — откатить и написать тимлиду:
```bash
sudo cp /etc/nginx/conf.d/padel.conf.bak /etc/nginx/conf.d/padel.conf
sudo systemctl reload nginx
```

---

## 5. Шаг 3 (ДЖУН) — HTTPS (Let's Encrypt / certbot)

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d taymaspadel.newlevelhub.kz
```
В процессе:
- ввести email для уведомлений;
- согласиться с условиями;
- на вопрос про redirect выбрать **«2: Redirect» (HTTP → HTTPS)**.

Certbot сам добавит для домена отдельный 443-блок с валидным сертификатом (самоподписанный серт на IP не тронет).

Проверить автопродление:
```bash
sudo certbot renew --dry-run
sudo nginx -t
```

**После этого джун пишет тимлиду: «DNS + HTTPS готовы».**

---

## 6. Шаг 4–6 (ТИМЛИД) — код и деплой

### 6.1 `.env` → `/opt/padel/padel_project/.env`
Добавить домен в `ALLOWED_HOSTS` (IP оставить):
```ini
ALLOWED_HOSTS=taymaspadel.newlevelhub.kz,213.155.23.227,localhost,.ngrok-free.app
```
> Рекомендация к прод-запуску (не обязательно сейчас): `DEBUG=False` и убрать `SMS_MASTER_CODE=000000` (иначе любой входит с кодом 000000).

### 6.2 `config/settings.py` — CSRF
CORS сейчас **оставляем открытым** (`CORS_ALLOW_ALL_ORIGINS = True` уже стоит в `settings.py`) — этого достаточно, чтобы работали и локальный веб, и мобилка. Закрывать под конкретные домены будем позже, перед прод-запуском.

Единственное, что стоит добавить — домен в `CSRF_TRUSTED_ORIGINS` (для форм/админки по https):
```python
CSRF_TRUSTED_ORIGINS = [
    "https://taymaspadel.newlevelhub.kz",
    "https://*.ngrok-free.app",
]
```

### 6.3 Деплой и рестарт
```bash
cd /opt/padel/padel_project
git pull origin main
sudo systemctl restart padel
sudo systemctl status padel      # active (running)
```

### 6.4 Фронт
- baseUrl API → `https://taymaspadel.newlevelhub.kz/api/`
- вебсокеты чата → `wss://taymaspadel.newlevelhub.kz/ws/chat/<id>/?token=<jwt>`
- Убедиться, что нигде не осталось `http://213.155.23.227` и `ws://` (иначе браузер заблокирует mixed-content).

---

## 7. Протокол: если нужно менять код (ВАЖНО)

Джун **код и `.env` сам НЕ правит и НЕ пушит**. Если по ходу выясняется, что нужна правка в коде/`.env`:
1. Джун останавливается и пишет тимлиду: **какой файл**, **какую строку**, **на что менять**, **зачем** (какая ошибка).
2. Тимлид сам правит, пушит, деплоит (`git pull` + `systemctl restart padel`) и отвечает «готово».
3. Джун продолжает и перепроверяет.

Джун меняет только серверные конфиги вне проекта: DNS (панель), `/etc/nginx/...`, certbot.

---

## 8. Проверка ДЖУНОМ (что всё работает)

Выполнить и приложить вывод к отчёту:

```bash
# 1. DNS указывает на сервер
dig +short taymaspadel.newlevelhub.kz          # ждём 213.155.23.227

# 2. Сертификат валидный, API отвечает (без -k! замок должен быть настоящим)
curl -I https://taymaspadel.newlevelhub.kz/api/courts/
# ждём: HTTP/2 200  (или 400 DisallowedHost, ЕСЛИ тимлид ещё не сделал шаг 4 — это ок)

# 3. HTTP редиректит на HTTPS
curl -I http://taymaspadel.newlevelhub.kz/api/courts/
# ждём: 301/308 и Location: https://...

# 4. Автопродление серта работает
sudo certbot renew --dry-run                    # без ошибок

# 5. Nginx-конфиг валиден, сервисы живы
sudo nginx -t
systemctl is-active nginx padel redis
```

**Критерии готовности (Definition of Done):**
- [ ] `dig` → `213.155.23.227`
- [ ] `curl -I https://...` без `-k` → нет ошибки сертификата (200 или 400-DisallowedHost до шага 4)
- [ ] http редиректит на https
- [ ] `certbot renew --dry-run` без ошибок
- [ ] `nginx -t` = ok; `nginx`, `padel`, `redis` = active
- [ ] Сделан `.bak` конфига

---

## 9. Проверка ТИМЛИДОМ (джун справился и НИЧЕГО не сломал)

После того как джун отчитался, и после своего шага 4–6:

```bash
# А) Старый доступ по IP не сломан (бэк доступен как раньше)
curl -kI https://213.155.23.227/api/courts/        # ждём 200
curl -I  http://213.155.23.227/api/courts/         # отвечает/редиректит

# Б) Домен отдаёт валидный HTTPS и 200 (после шага 4 ALLOWED_HOSTS)
curl -I https://taymaspadel.newlevelhub.kz/api/courts/   # ждём HTTP/2 200

# В) Сервисы живы, конфиг цел
sudo nginx -t
systemctl is-active nginx padel redis postgresql
sudo systemctl status padel --no-pager | head -5   # active (running)

# Г) Бэкап конфига на месте (можно откатиться)
ls -l /etc/nginx/conf.d/padel.conf.bak
```

**Проверка через браузер/приложение (главное):**
- [ ] `https://taymaspadel.newlevelhub.kz/swagger/` открывается с валидным замком.
- [ ] Веб-фронт (локально) логинится, грузит данные — в консоли **нет** ошибок mixed-content.
- [ ] Мобильное приложение работает по `https://`.
- [ ] **Чат работает по `wss://`** (сообщения ходят в реальном времени) — главный тест ASGI/вебсокетов.
- [ ] Старые запросы по IP ещё отвечают (ничего не отвалилось).

Если любой пункт красный — попросить джуна откатить nginx из `.bak` и разобрать причину вместе.

---

## 10. Отчёт джуна тимлиду (по завершении)

1. Вывод команд из раздела 8 (1–5).
2. Скрин `https://taymaspadel.newlevelhub.kz/swagger/` с замком.
3. Какие файлы на сервере менял и где лежит `.bak`.

---

## 11. Что НЕ трогать джуну

- Код проекта и `.env` в `/opt/padel/padel_project` (только через тимлида).
- Сервисы деплоя: Daphne (`padel`), Redis, systemd, PostgreSQL.
- Самоподписанный 443-блок/серт на IP — не удалять (certbot добавит домен рядом).
- SMS-шлюз, платёжный провайдер (Kaspi).
