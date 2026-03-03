# Карта проекта: Padel Club MVP

**Стек:** Django 4.2 + DRF + JWT (Djoser/SimpleJWT) + PostgreSQL  
**Frontend:** `app.html` (мобилка) + `crm.html` (CRM)  
**Последнее обновление:** 23 февраля 2026

---

## 1. Структура приложений (Apps)

```
padel_project/
├── config/          — настройки, главный urls.py, wsgi/asgi
├── users/           — пользователи, роли, SMS-вход, CRM-вход, профиль, stats, home
├── core/            — настройки клуба (время работы, отмена), выходные дни
├── courts/          — корты, типы, цены, галерея; CRUD для ADMIN
├── inventory/       — услуги/инвентарь (ракетки, вода); CRUD для ADMIN
├── bookings/        — бронирования, участники, тренер, услуги; CRM-расписание
├── memberships/     — абонементы (PADEL/GYM_UNLIMITED/GYM_PACK), заморозка
├── gym/             — посещения зала, QR-вход, персональные тренировки
├── finance/         — транзакции, история, сводка; API для ресепшн/клиента
├── gamification/    — матчи, ELO рейтинг, лидерборд
├── marketing/       — акции, промокоды
├── news/            — новости и объявления клуба
├── analytics/       — дашборд директора + дашборд ресепшн
├── friends/         — заявки в друзья
├── leads/           — воронка продаж / лиды (CRM); Lead, LeadComment, LeadTask
├── app.html         — тестовый фронт: мобильное приложение
└── crm.html         — тестовый фронт: CRM
```

---

## 2. Модели и связи

| App | Модели | Ключевые связи |
|-----|--------|----------------|
| **users** | `User` | AbstractUser; role (5 вариантов), phone, ELO, FCM, QR |
| **core** | `ClubSetting`, `ClosedDay` | — |
| **courts** | `Court`, `CourtImage` | CourtImage → Court |
| **inventory** | `Service` | — |
| **bookings** | `Booking`, `BookingService` | user/coach/participants → User; court → Court; BookingService → Service |
| **memberships** | `MembershipType`, `UserMembership` | UserMembership → User + MembershipType |
| **gym** | `GymVisit`, `PersonalTraining` | → User |
| **finance** | `Transaction` | → User; опционально → Booking или UserMembership |
| **gamification** | `Match` | team_a/team_b/judge → User; → Court |
| **marketing** | `Promotion` | — |
| **news** | `NewsItem` | — |
| **friends** | `FriendRequest` | from_user/to_user → User |
| **analytics** | — | агрегации по другим app |
| **leads** | `Lead`, `LeadComment`, `LeadTask` | Lead → User (assigned_to); LeadComment/Task → Lead + User |

---

## 3. Роли пользователей

| Роль | Вход | Доступ |
|------|------|--------|
| `ADMIN` | CRM по паролю | Всё |
| `RECEPTIONIST` | CRM по паролю | CRM, расписание, клиенты, QR-сканер |
| `COACH_PADEL` | SMS | Матчи, тренировки (добавление тренера к броням) |
| `COACH_FITNESS` | SMS | Персональные тренировки в зале |
| `CLIENT` | SMS | Брони, друзья, абонементы, QR, профиль |

---

## 4. Полная таблица API Endpoints

### Auth / Пользователи  `api/auth/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| POST | `mobile/send-code/` | Anon | Отправить SMS-код |
| POST | `mobile/login/` | Anon | Войти по SMS-коду → JWT |
| POST | `crm/login/` | Anon | Войти в CRM по паролю → JWT |
| GET | `home/` | Клиент | Главный экран: приветствие, ближ. бронь, абонемент, акции, новости |
| GET | `me/stats/` | Клиент | Персональная статистика (брони, часы, матчи, посещения зала) |
| GET | `search/?search=` | Auth | Поиск пользователей (для добавления друзей) |
| GET | `clients/?search=&role=` | Ресепшн | Список клиентов/сотрудников для CRM |
| GET | `reception/search/?phone=` | Ресепшн | Поиск клиента по телефону |
| GET | `reception/user/<id>/` | Ресепшн | Карточка клиента |
| POST | `reception/user/<id>/action/` | Ресепшн | Действия: unblock_qr, update_info, deactivate, activate |
| GET/PATCH | `users/me/` *(Djoser)* | Auth | Просмотр/обновление профиля |
| POST | `jwt/create/` *(Djoser)* | Anon | JWT по email+password |
| POST | `jwt/refresh/` *(Djoser)* | — | Обновить access-токен |

### Корты  `api/courts/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `` | Anon | Список активных кортов |
| GET | `<id>/` | Anon | Детальная карточка корта |
| GET | `manage/` | ADMIN | Все корты (включая неактивные) |
| POST | `manage/` | ADMIN | Создать корт |
| GET/PATCH/DELETE | `manage/<id>/` | ADMIN | Управление кортом |

### Инвентарь/Услуги  `api/inventory/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `services/` | Anon | Список активных услуг |
| GET | `services/manage/` | ADMIN | Все услуги |
| POST | `services/manage/` | ADMIN | Создать услугу |
| GET/PATCH/DELETE | `services/manage/<id>/` | ADMIN | Управление услугой |

### Бронирования  `api/bookings/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `` | Auth | Предстоящие брони (только незавершённые и неотменённые) |
| GET | `history/` | Auth | История всех броней (включая отменённые) |
| GET | `<id>/` | Auth | Детальная бронь |
| POST | `create/` | Auth | Создать бронь (с абонементом, промокодом, друзьями, тренером, услугами) |
| POST | `<id>/cancel/` | Auth | Отменить бронь |
| POST | `reception/create/` | Ресепшн | Создать бронь от имени клиента (поле `client_id`) |
| POST | `<id>/confirm-payment/` | Ресепшн | Подтвердить оплату (PENDING → CONFIRMED, выбрать способ оплаты) |
| GET | `check-availability/?court_id=&date=` | Anon | Свободные слоты |
| GET | `manager/schedule/?date=` | Ресепшн | Расписание кортов на день |
| GET | `all/?date=&status=&court_id=&client_id=` | Ресепшн | Все брони с фильтрами |

### Абонементы  `api/memberships/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `types/` | Anon | Список типов абонементов |
| POST | `buy/<id>/` | Auth | Купить абонемент |
| GET | `my/` | Auth | Мои абонементы |
| POST | `my/<id>/freeze/` | Auth | Заморозить абонемент |
| POST | `my/<id>/unfreeze/` | Auth | Разморозить абонемент |
| GET | `my/<id>/history/` | Auth | История транзакций по абонементу |

### Зал  `api/gym/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| POST | `checkin/` | Auth | Вход в зал (абонемент / разовый) |
| GET | `qr/generate/` | Auth | Сгенерировать QR для входа (60 сек) |
| POST | `qr/scan/` | Ресепшн | Сканировать QR турникетом (GYM/PADEL/ALL) |
| GET | `personal-training/` | Auth | Список персональных тренировок |
| POST | `personal-training/` | Auth | Записаться к тренеру |
| GET/PATCH/DELETE | `personal-training/<id>/` | Auth | Управление тренировкой |

### Финансы  `api/finance/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `history/` | Auth | История транзакций текущего пользователя |
| GET | `transactions/?date=&type=&method=&user_id=` | Ресепшн | Все транзакции с фильтрами |
| GET | `summary/?period=today\|month\|all` | Ресепшн | Финансовая сводка |

### Геймификация  `api/gamification/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `matches/` | Auth | История матчей (мои или все если тренер/ADMIN) |
| POST | `matches/create/` | Тренер | Создать матч + пересчёт ELO |
| GET | `leaderboard/?limit=` | Anon | Таблица лидеров по ELO |

### Маркетинг  `api/marketing/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `promos/` | Anon | Активные акции |

### Новости  `api/news/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `?category=NEWS\|EVENT\|PROMO\|ANNOUNCEMENT` | Anon | Список новостей |
| GET | `<id>/` | Anon | Полный текст новости |
| GET/POST | `manage/` | ADMIN | Управление новостями |
| GET/PATCH/DELETE | `manage/<id>/` | ADMIN | Управление новостью |

### Лиды / Воронка продаж  `api/leads/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `kanban/` | Ресепшн | Канбан-доска (все стадии сразу) |
| GET | `stats/` | Ресепшн | Статистика воронки / конверсия |
| GET/POST | `` | Ресепшн | Список лидов / создать лид |
| GET/PATCH/DELETE | `<id>/` | Ресепшн | Детали / редактирование / удаление |
| POST | `<id>/move/` | Ресепшн | Переместить в другую стадию (drag & drop) |
| GET/POST | `<id>/comments/` | Ресепшн | История взаимодействий |
| DELETE | `<id>/comments/<comment_id>/` | Ресепшн | Удалить комментарий |
| GET/POST | `<id>/tasks/` | Ресепшн | Задачи / напоминания |
| PATCH/DELETE | `<id>/tasks/<task_id>/` | Ресепшн | Обновить / удалить задачу |

### Аналитика  `api/analytics/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `dashboard/` | ADMIN | Расширенный дашборд директора (выручка, загрузка, клиенты) |
| GET | `reception/` | Ресепшн | Дашборд ресепшн (сегодня: брони, ожидающие оплаты, ближайшие) |

### Друзья  `api/friends/`

| Метод | URL | Роль | Описание |
|-------|-----|------|----------|
| GET | `` | Auth | Список друзей |
| POST | `send/` | Auth | Отправить заявку |
| GET | `requests/` | Auth | Входящие заявки |
| GET | `requests/outgoing/` | Auth | Исходящие заявки |
| POST | `respond/` | Auth | Принять/отклонить заявку |
| POST | `cancel/` | Auth | Отменить свою заявку |
| POST | `remove/` | Auth | Удалить из друзей |

### Настройки клуба  `api/core/`

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `settings/` | Настройки клуба (время работы, политика отмены) |

---

## 5. Исправленные баги (Feb 23, 2026)

| # | Баг | Статус |
|---|-----|--------|
| 1 | `status='PAID'` в QR-сканере (статуса не существует → DENIED всегда) | ✅ Исправлен |
| 2 | `transaction_type='PAYMENT'` в GymCheckIn (500 ошибка) | ✅ Исправлен |
| 3 | `POST /api/courts/` без ограничений — любой клиент мог создать корт | ✅ Исправлен |
| 4 | `ManagerScheduleView` / `DirectorDashboardView` — `IsAdminUser` (только суперюзеры) | ✅ Исправлен |
| 5 | Двойной `booking.save()` в CreateBookingSerializer | ✅ Исправлен |
| 6 | Способ оплаты всегда KASPI — нет выбора | ✅ Исправлен |
| 7 | Analytics: захардкожено 15 рабочих часов | ✅ Исправлен |
| 8 | Можно добавить незнакомца в участники брони | ✅ Исправлен |

---

## 6. Документация

- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`
