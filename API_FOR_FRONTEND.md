# API для фронтенда (мобилка + CRM)

База: `http(s)://<host>/api/`  
Авторизация: `Authorization: Bearer <access_token>` (JWT).  
Полная документация: `/swagger/`, `/redoc/`.

---

## Важные эндпоинты, которые часто пропускают

| Метод | URL | Роль | Назначение |
|-------|-----|------|------------|
| **POST** | `auth/me/fcm/` | Auth | Сохранить FCM token для пуш-уведомлений после логина. Body: `{ "fcm_token": "..." }` |
| **GET** | `core/closed-days/?from=YYYY-MM-DD&to=YYYY-MM-DD` | Anon | Выходные/праздники для календаря. Без параметров — с сегодня по +1 год. |
| **POST** | `core/closed-days/` | Admin | Создать выходной. Body: `{ "date": "YYYY-MM-DD", "reason": "..." }`. |
| **GET** | `gym/visits/` | Auth | История посещений зала текущего пользователя. |
| **GET** | `marketing/validate-promo/?code=XXX` | Anon | Проверка промокода без применения. Ответ: `{ "valid": true, "title", "discount_type", "discount_value" }` или `{ "valid": false, "error": "..." }`. |
| **GET** | `auth/coaches/` | Anon | Список тренеров (id, full_name, role, coach_price) для выбора в брони. |
| **GET** | `bookings/available-coaches/?datetime=ISO&duration=60` | Anon | Тренеры, свободные в указанный слот. |
| **POST** | `bookings/price-preview/` | Auth | Превью суммы с учётом абонемента. Body: `court_id`, `start_time`, `duration`, `coach_id?`, `service_ids[]`. |
| **GET** | `bookings/coach/schedule/?from=&to=` | Coach | Расписание броней тренера (где он назначен). |
| **POST** | `gamification/matches/create/` | Coach | Создать матч и начислить ELO. Body: `team_a`, `team_b` (массивы ID), `score`, `winner_team` (A/B/DRAW), `court?`. |

---

## Защита API (кто может пользоваться)

**Да, у вас уже есть защита.** Случайный человек не сможет полноценно пользоваться API:

- **JWT-авторизация**: почти все действия (брони, абонементы, профиль, отмена, оплата и т.д.) требуют заголовок `Authorization: Bearer <access_token>`. Токен выдаётся только после успешного входа: мобильный — по SMS-коду (`mobile/login/`), CRM — по логину/паролю (`crm/login/`).
- **Роли и права**:
  - **Клиент** — свои брони, свой абонемент, друзья, зал, матчи с участием.
  - **Тренер** — свои брони как тренер (`coach/schedule/`), отмена своих слотов, создание матчей и ввод счёта (ELO).
  - **Ресепшн** — поиск клиентов, создание/оплата броней от имени клиента, выдача абонементов, расписание, транзакции.
  - **Админ** — всё выше + управление услугами, типами абонементов, акциями, кортами, новостями.
- **Публичные (без токена)** — только чтение: список кортов, список тренеров, проверка слотов, проверка промокода, выходные дни, настройки клуба, лидерборд, список акций/новостей. Создать бронь, купить абонемент или изменить данные без токена нельзя.
- **CORS**: в настройках Django задаётся список разрешённых доменов для запросов из браузера; запросы с других доменов можно ограничить.
- **Throttling**: включён для анонимных запросов (ограничение по числу запросов в час).

Итого: **без логина** доступно только чтение справочников и проверок. **С логином** — только те действия, которые разрешены роли пользователя.

---

## Auth (`api/auth/`)

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `mobile/send-code/` | Отправка SMS-кода (body: `phone_number`) |
| POST | `mobile/login/` | Вход по коду (body: `phone_number`, `code`, `device_id`) → JWT |
| POST | `crm/login/` | Вход в CRM (body: `username`, `password`) → JWT |
| **POST** | **`me/fcm/`** | **Обновление FCM токена (body: `fcm_token`)** |
| GET | `home/` | Главный экран: приветствие, ближайшая бронь, абонемент, акции, новости |
| GET | `me/stats/` | Персональная статистика (брони, часы, матчи, зал) |
| GET | `coaches/` | Список тренеров для брони |
| GET | `clients/?search=&role=` | Список клиентов/тренеров (ресепшн) |
| GET | `search/?search=` | Поиск пользователей (друзья) |
| GET | `reception/search/?phone=` | Поиск клиента по телефону (ресепшн) |
| GET | `reception/user/<id>/` | Карточка клиента (ресепшн) |
| POST | `reception/user/<id>/action/` | Действия: unblock_qr, update_info, activate, deactivate (ресепшн) |
| GET/PATCH | `users/me/` *(Djoser)* | Профиль текущего пользователя |
| POST | `jwt/refresh/` | Обновить access по refresh |
| POST | `jwt/blacklist/` | Выход (blacklist refresh) |

---

## Корты (`api/courts/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `` | Список активных кортов (поля: id, name, court_type, description, price_per_hour, image, gallery) |
| GET | `<id>/` | Детали корта |
| GET/POST | `manage/` | Список всех / создание (ADMIN) |
| GET/PATCH/DELETE | `manage/<id>/` | Редактирование корта (ADMIN) |

---

## Брони (`api/bookings/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `` | Мои предстоящие брони |
| GET | `history/` | История броней (включая отменённые) |
| GET | `<id>/` | Детали брони |
| POST | `create/` | Создать бронь (court, start_time, duration, coach?, services?, friends_ids?, promo_code?, payment_method) |
| POST | `<id>/cancel/` | Отменить бронь. **При отмене:** если бронь была оплачена часами абонемента (`membership_used` не null), часы автоматически возвращаются на счёт абонемента. |
| GET | `check-availability/?court_id=&date=` | Занятые слоты на дату |
| **GET** | **`available-coaches/?datetime=ISO&duration=60`** | **Свободные тренеры в слот** |
| **POST** | **`price-preview/`** | **Превью цены с абонементом (court_id, start_time, duration, coach_id?, service_ids[])** |
| POST | `reception/create/` | Создать бронь от имени клиента (client_id + те же поля) (ресепшн) |
| POST | `<id>/confirm-payment/` | Подтвердить оплату (body: payment_method) (ресепшн) |
| GET | `manager/schedule/?date=` | Расписание по кортам на день (ресепшн) |
| GET | `all/?date=&status=&court_id=&client_id=` | Все брони с фильтрами (ресепшн) |
| **GET** | **`coach/schedule/?from=YYYY-MM-DD&to=YYYY-MM-DD`** | **Расписание броней тренера (брони, где он назначен). Без параметров — с сегодня по +14 дней.** |

При создании брони услуги передавать как: `"services": [{"service_id": 1, "quantity": 1}]`.

**Ответы GET (список/детали брони)** теперь включают поле **`membership_used`** (id абонемента или `null`): если бронь была оплачена часами PADEL-абонемента, здесь будет id этого абонемента. По нему можно показывать в UI «Оплачено по абонементу» и учитывать, что при отмене часы вернутся на счёт.

---

## Услуги (`api/inventory/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `services/` | Список активных услуг (для выбора в брони) |
| GET/POST | `services/manage/` | Список всех / создание (ADMIN) |
| GET/PATCH/DELETE | `services/manage/<id>/` | Редактирование (ADMIN) |

---

## Абонементы (`api/memberships/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `types/` | Типы абонементов (магазин) |
| GET/POST | `types/manage/` | Все типы / создание (ресепшн/ADMIN) |
| GET/PATCH/DELETE | `types/manage/<id>/` | Редактирование типа (ресепшн/ADMIN) |
| POST | `buy/<id>/` | Купить абонемент (текущий пользователь) |
| POST | `reception/buy/` | Выдать абонемент клиенту (body: client_id, membership_type_id, payment_method) (ресепшн) |
| GET | `all/?client_id=&is_active=` | Все абонементы (ресепшн) |
| GET | `my/` | Мои абонементы |
| POST | `my/<id>/freeze/` | Заморозить |
| POST | `my/<id>/unfreeze/` | Разморозить |
| GET | `my/<id>/history/` | История транзакций по абонементу |

---

## Зал (`api/gym/`)

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `checkin/` | Вход в зал (проверка абонемента/разовый) |
| **GET** | **`visits/`** | **История посещений зала (текущий пользователь)** |
| GET | `qr/generate/` | Сгенерировать QR для входа (60 сек) |
| POST | `qr/scan/` | Сканировать QR (ресепшн) |
| GET/POST | `personal-training/` | Список / запись на тренировку |
| GET/PATCH/DELETE | `personal-training/<id>/` | Детали тренировки |

---

## Финансы (`api/finance/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `history/` | Мои транзакции |
| GET | `transactions/?date=&type=&method=&user_id=` | Все транзакции (ресепшн) |
| GET | `summary/?period=today|month|all` | Сводка (ресепшн) |

---

## Геймификация (`api/gamification/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `matches/` | Мои матчи. С параметром `?all=1` — все матчи (для тренера/админа). |
| POST | `matches/create/` | Создать матч (только тренер/ADMIN). Body: `team_a`, `team_b` (массивы ID), `score`, `winner_team` (A/B/DRAW), `court` (опционально). После сохранения автоматически пересчитывается ELO: ±25 очков победителям/проигравшим. |
| GET | `leaderboard/?limit=` | Топ по ELO (публично). |

---

## Маркетинг (`api/marketing/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `promos/` | Активные акции |
| **GET** | **`validate-promo/?code=XXX`** | **Проверка промокода (без применения)** |
| GET/POST | `manage/` | Список акций / создание (ADMIN) |
| GET/PATCH/DELETE | `manage/<id>/` | Редактирование акции (ADMIN) |

---

## Новости (`api/news/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `?category=NEWS|EVENT|PROMO|ANNOUNCEMENT` | Список новостей |
| GET | `<id>/` | Детали новости |
| GET/POST | `manage/` | Управление (ADMIN) |
| GET/PATCH/DELETE | `manage/<id>/` | Редактирование (ADMIN) |

---

## Настройки и календарь (`api/core/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `settings/` | Настройки клуба (OPEN_TIME, CLOSE_TIME, CANCELLATION_HOURS) |
| **GET** | **`closed-days/?from=YYYY-MM-DD&to=YYYY-MM-DD`** | **Выходные/праздники для календаря** |
| **POST** | **`closed-days/`** | **Создать выходной (Admin). Body: `date`, `reason`.** |

---

## Аналитика (`api/analytics/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `dashboard/` | Дашборд директора (ADMIN) |
| GET | `reception/` | Дашборд ресепшн (ресепшн) |

---

## Друзья (`api/friends/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `` | Список друзей |
| POST | `send/` | Отправить заявку (body: to_user_id) |
| GET | `requests/` | Входящие заявки |
| GET | `requests/outgoing/` | Исходящие заявки |
| POST | `respond/` | Принять/отклонить (body: request_id, action: accept|reject) |
| POST | `cancel/` | Отменить заявку (body: request_id) |
| POST | `remove/` | Удалить из друзей (body: user_id) |

---

## Лобби — поиск партнёров (`api/lobby/`)

### Концепция нового флоу
1. **OPEN** → Лобби создаётся **без корта и времени**. Игроки присоединяются по ELO диапазону.
2. **WAITING** → Часть игроков собрана.
3. **NEGOTIATING** → Все игроки собраны. Любой участник предлагает корт+дату+время, остальные голосуют.
4. **READY** → Предложение принято (все проголосовали или создатель нажал «Принять»). Корт и время зафиксированы.
5. **BOOKED** → Бронь создана, ждём оплату от каждого.
6. **PAID** → Все оплатили. Бронь подтверждена.

### Форматы игры
| Значение | Описание |
|----------|----------|
| `SINGLE` | 1×1 (2 игрока) |
| `DOUBLE` | 2×2 (4 игрока) |

### Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `lobby/?elo=<число>` | Список лобби. По умолчанию фильтр ±200 ELO текущего юзера. `?elo=all` — без фильтра |
| POST | `lobby/` | Создать лобби. Body: `title`, `game_format` (SINGLE/DOUBLE), `elo_min?`, `elo_max?`, `comment?` |
| GET | `lobby/my/` | Мои лобби (где я создатель или участник) |
| GET | `lobby/<id>/` | Детали лобби (с предложениями времени и участниками) |
| POST | `lobby/<id>/join/` | Вступить в лобби (проверяется ELO) |
| POST | `lobby/<id>/leave/` | Покинуть лобби |
| POST | `lobby/<id>/assign-teams/` | Распределить по командам. Body: `{"teams": {"<user_id>": "A", ...}}` (только создатель) |
| **POST** | **`lobby/<id>/proposals/`** | **Предложить корт и время** (только когда статус NEGOTIATING). Body: `court`, `scheduled_time` (ISO), `duration_minutes` |
| GET | `lobby/<id>/proposals/` | Список предложений времени/корта |
| **POST** | **`lobby/<id>/proposals/<pid>/vote/`** | **Проголосовать за предложение** (только статус NEGOTIATING). Если все проголосовали — принимается автоматически |
| **POST** | **`lobby/<id>/proposals/<pid>/accept/`** | **Принять предложение** (только создатель, статус NEGOTIATING) |
| POST | `lobby/<id>/book/` | Создать бронь (только статус READY, команды назначены) |
| POST | `lobby/<id>/pay/` | Оплатить свою долю. Body: `payment_method` (CASH/CARD/ONLINE). Опционально: `use_membership` (bool) |

### Создание лобби (body)
```json
{
  "title": "Ищем 4-ку на вечер",
  "game_format": "DOUBLE",
  "elo_min": 1000,
  "elo_max": 1400,
  "comment": "Новички приветствуются"
}
```

### Предложение времени/корта (body)
```json
{
  "court": 1,
  "scheduled_time": "2026-03-05T18:00:00",
  "duration_minutes": 90
}
```

### Ответ детали лобби (ключевые поля)
```json
{
  "id": 12,
  "status": "NEGOTIATING",
  "elo_min": 1000,
  "elo_max": 1400,
  "elo_label": "ELO 1000–1400",
  "court": null,
  "scheduled_time": null,
  "current_players_count": 4,
  "max_players": 4,
  "participants": [...],
  "proposals": [
    {
      "id": 3,
      "proposed_by_name": "Азамат",
      "court_name": "Корт 1",
      "court_price": 3000,
      "scheduled_time": "2026-03-05T18:00:00+05:00",
      "duration_minutes": 90,
      "votes_count": 2,
      "i_voted": true,
      "estimated_share": "750.00"
    }
  ]
}
```

---

## Платёжные сессии (`api/payments/`)

Используется для отслеживания статуса оплаты при интеграции с реальным провайдером (Kaspi и др.).

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `payments/session/<uuid>/status/` | Статус платёжной сессии (поллинг после перехода на страницу оплаты) |
| POST | `payments/webhook/<provider>/` | Вебхук от платёжного провайдера (только для Kaspi/Card) |

### Текущий провайдер
Настраивается в `.env` через `PAYMENT_PROVIDER`:
- `stub` — заглушка (мгновенная оплата, для разработки)
- `kaspi` — реальный Kaspi (подключить позже)

---

## Уведомления (`api/notifications/`)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `notifications/` | Список уведомлений (новые сверху) |
| GET | `notifications/unread-count/` | Кол-во непрочитанных: `{"unread_count": 3}` |
| POST | `notifications/<id>/read/` | Отметить одно как прочитанное |
| POST | `notifications/read-all/` | Отметить все как прочитанные |

Уведомления отправляются автоматически при:
- Заполнении лобби (статус → NEGOTIATING)
- Принятии предложения времени (статус → READY)
- Подтверждении брони (все оплатили)

---

## Что ещё учесть фронту

- **Аватар пользователя**: в профиле приходит поле `avatar` (URL). Изменение — через PATCH `users/me/` с `multipart/form-data` и полем `avatar` (файл), если бэкенд это поддерживает. Иначе только через админку/ресепшн.
- **Пагинация**: в большинстве списков пагинация не включена глобально; при больших объёмах можно добавить `?page_size=` и пагинацию на бэке.
- **Сброс пароля (CRM)**: если нужен «Забыли пароль» для ресепшн — используется Djoser: `POST /api/auth/users/reset_password/` (email) и подтверждение по ссылке (настроить в проекте).
- **Изображения**: корты и пользователи возвращают относительные пути к медиа (`/media/...`). Базовый URL медиа: `MEDIA_URL` с сервера (обычно `http(s)://<host>/media/`).
