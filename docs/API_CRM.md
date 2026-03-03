# Padel Club — API документация для CRM (React)

Документ описывает **все эндпоинты бэкенда, используемые веб-приложением CRM** (ресепшн и админ). Для мобильного приложения (клиенты и тренеры) используется отдельная документация: **`API_MOBILE.md`**.

---

## Общие сведения

| Параметр | Значение |
|----------|-----------|
| **Base URL** | `http://213.155.23.227/api` |
| **Swagger** | `http://213.155.23.227/swagger/` |
| **Авторизация** | JWT: заголовок `Authorization: Bearer <access_token>` |
| **Формат тела** | JSON (`Content-Type: application/json`) |
| **Даты/время** | ISO 8601, например `2026-03-28T14:00:00Z` |

### Роли CRM

| Роль | Описание |
|------|----------|
| **ADMIN** | Полный доступ ко всему: дашборды, клиенты, брони, финансы, абонементы, лиды, управление кортами/услугами/акциями/новостями. |
| **RECEPTIONIST** | Клиенты, брони, оплаты, абонементы, расписание, финансы, QR, лиды. |
| **SALES_MANAGER** | Менеджер продаж: лиды/воронка, просмотр клиентов. Не видит брони, финансы, QR, управление. |

Эндпоинты с пометкой **(только ADMIN)** доступны только пользователям с ролью `ADMIN`. Лиды доступны: ADMIN, RECEPTIONIST, SALES_MANAGER.

---

## 1. Авторизация

### 1.1 Вход в CRM

Вход только по логину и паролю. Клиенты и тренеры в CRM через этот эндпоинт не входят (для них — мобильный вход по SMS).

```
POST /api/auth/crm/login/
```

**Auth:** не требуется

**Request body:**
```json
{
  "username": "reception1",
  "password": "your_password"
}
```

`username` может быть логин или номер телефона.

**Response 200:**
```json
{
  "refresh": "eyJ...",
  "access": "eyJ...",
  "user_id": 1,
  "role": "RECEPTIONIST",
  "first_name": "Иван",
  "last_name": "Иванов"
}
```

**Errors:**
- `401` — неверный логин или пароль
- `403` — у пользователя нет доступа к CRM (роль не ADMIN и не RECEPTIONIST)

---

### 1.2 Обновление токена

```
POST /api/auth/jwt/refresh/
```

**Request body:**
```json
{
  "refresh": "eyJ..."
}
```

**Response 200:**
```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

После обновления старый `refresh` аннулируется — сохраняйте новый.

---

### 1.3 Проверка токена

```
POST /api/auth/jwt/verify/
```

**Request body:**
```json
{
  "token": "<access_token>"
}
```

**Response 200** — пустое тело при валидном токене.  
**401** — токен истёк или невалиден.

---

## 2. Дашборды

### 2.1 Дашборд ресепшн

Краткая сводка на сегодня: брони, ожидающие оплаты, выручка, ближайшие брони.

```
GET /api/analytics/reception/
```

**Доступ:** RECEPTIONIST, ADMIN

**Response 200:**
```json
{
  "today": "25.03.2026",
  "bookings_today": 12,
  "pending_payments": 3,
  "today_revenue": 150000.0,
  "upcoming_bookings": [
    {
      "id": 101,
      "court": "Корт 1",
      "start_time": "14:00",
      "client": "Азамат Есимханулы",
      "status": "PENDING",
      "is_paid": false,
      "price": 5000.0
    }
  ]
}
```

---

### 2.2 Дашборд директора

Расширенная аналитика: выручка по периодам, загрузка кортов, структура выручки по типам.

```
GET /api/analytics/dashboard/
```

**Доступ:** только ADMIN

**Response 200:**
```json
{
  "period": {
    "date": "2026-03-25",
    "month": "March 2026"
  },
  "kpi": {
    "today_revenue": 150000.0,
    "week_revenue": 450000.0,
    "month_revenue": 1200000.0,
    "total_revenue": 5000000.0,
    "occupancy_rate_today": "65.0%",
    "bookings_today": 12,
    "pending_payments": 3,
    "week_bookings": 45,
    "total_clients": 320,
    "new_clients_this_month": 28
  },
  "revenue_structure": [
    {
      "type": "BOOKING",
      "label": "Оплата бронирования",
      "amount": 800000.0,
      "count": 120
    },
    {
      "type": "MEMBERSHIP",
      "label": "Покупка абонемента",
      "amount": 400000.0,
      "count": 15
    }
  ],
  "work_hours": "7:00 – 23:00"
}
```

---

## 3. Расписание и бронирования

### 3.1 Расписание по кортам на дату

Расписание всех кортов на выбранный день с бронями.

```
GET /api/bookings/manager/schedule/?date=YYYY-MM-DD
```

**Параметры:** `date` — дата (по умолчанию — сегодня).

**Response 200:**
```json
{
  "date": "2026-03-25",
  "schedule": [
    {
      "court_id": 1,
      "court_name": "Корт 1",
      "court_type": "INDOOR",
      "bookings": [
        {
          "id": 101,
          "start_time": "2026-03-25T10:00:00Z",
          "end_time": "2026-03-25T11:00:00Z",
          "court_name": "Корт 1",
          "client_name": "Азамат Есимханулы",
          "client_phone": "+77001234567",
          "status": "CONFIRMED",
          "is_paid": true,
          "price": "5000.00",
          "coach_name": "Алексей Тренер",
          "participants": ["daniyar"],
          "services": [
            { "service_name": "Ракетка", "quantity": 1, "price_at_moment": "2000.00" }
          ]
        }
      ]
    }
  ]
}
```

---

### 3.2 Все брони (список с фильтрами)

```
GET /api/bookings/all/?date=YYYY-MM-DD&status=CONFIRMED&court_id=1&client_id=42
```

**Параметры (все опциональны):**
| Параметр | Описание |
|----------|-----------|
| `date` | Фильтр по дате брони |
| `status` | `PENDING`, `CONFIRMED`, `CANCELED`, `COMPLETED` |
| `court_id` | ID корта |
| `client_id` | ID клиента (владельца брони) |

**Response 200:** массив объектов брони (те же поля, что в расписании: `id`, `start_time`, `end_time`, `court_name`, `client_name`, `client_phone`, `status`, `is_paid`, `price`, `coach_name`, `participants`, `services`).

---

### 3.3 Создать бронь от имени клиента

Ресепшн/админ создаёт бронирование за выбранного клиента.

```
POST /api/bookings/reception/create/
```

**Request body:**
```json
{
  "client_id": 42,
  "court": 1,
  "start_time": "2026-03-28T14:00:00Z",
  "duration": 60,
  "coach": 3,
  "payment_method": "KASPI",
  "promo_code": "",
  "services": [
    { "service_id": 1, "quantity": 1 }
  ]
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `client_id` | int | да | ID клиента |
| `court` | int | да | ID корта |
| `start_time` | string (ISO) | да | Начало брони |
| `duration` | int | да | Длительность в минутах (30–240) |
| `coach` | int | нет | ID тренера |
| `payment_method` | string | нет | `KASPI`, `CARD`, `CASH` |
| `promo_code` | string | нет | Промокод |
| `services` | array | нет | `[{ "service_id": 1, "quantity": 1 }]` |

**Response 201:** объект созданной брони (как в разделе 3.1).  
**400** — ошибки валидации (корт занят, время в прошлом, выходной и т.д.).

---

### 3.4 Подтвердить оплату брони

Фиксирует факт оплаты на ресепшн (создаётся транзакция).

```
POST /api/bookings/{id}/confirm-payment/
```

**Request body:**
```json
{
  "payment_method": "CASH"
}
```

Допустимые значения: `KASPI`, `CARD`, `CASH`, `UNKNOWN`.

**Response 200:**
```json
{
  "status": "Оплата подтверждена.",
  "booking_id": 101,
  "is_paid": true,
  "payment_method": "CASH"
}
```

**400** — бронь уже оплачена или отменена.

---

## 4. Клиенты

### 4.1 Список клиентов (с поиском и фильтром по роли)

```
GET /api/auth/clients/?search=иван&role=CLIENT
```

**Параметры:**
| Параметр | Описание |
|----------|----------|
| `search` | Поиск по имени, фамилии, телефону, username |
| `role` | `CLIENT`, `COACH_PADEL`, `COACH_FITNESS` или пусто (все перечисленные) |

**Response 200:** массив пользователей (сериализатор ресепшн):

```json
[
  {
    "id": 42,
    "username": "+77001234567",
    "phone_number": "+77001234567",
    "first_name": "Азамат",
    "last_name": "Есимханулы",
    "avatar": null,
    "is_qr_blocked": false,
    "last_device_id": "...",
    "role": "CLIENT",
    "rating_elo": 1200,
    "is_profile_complete": true,
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

---

### 4.2 Поиск клиента по телефону

Удобно для быстрого поиска при создании брони или выдаче абонемента.

```
GET /api/auth/reception/search/?phone=7700
```

**Параметры:** `phone` — минимум 4 символа (часть номера).

**Response 200:** массив клиентов (те же поля, что в 4.1). Ресепшн видит только пользователей с ролью CLIENT.

**400** — если передано меньше 4 символов.

---

### 4.3 Карточка клиента

```
GET /api/auth/reception/user/{id}/
```

**Response 200:** один объект пользователя (как в 4.1).  
**404** — пользователь не найден.

---

### 4.4 Действия с клиентом

```
POST /api/auth/reception/user/{id}/action/
```

**Request body зависит от действия.**

Доступны только для пользователей с ролью **CLIENT**.

#### Разблокировать QR

```json
{ "action": "unblock_qr" }
```

**Response 200:**
```json
{
  "status": "success",
  "message": "QR-код разблокирован для ...",
  "is_qr_blocked": false
}
```

#### Обновить имя/фамилию

```json
{
  "action": "update_info",
  "first_name": "Иван",
  "last_name": "Иванов"
}
```

**Response 200:**
```json
{
  "status": "success",
  "message": "Данные обновлены.",
  "user": { "id": 42, "first_name": "Иван", "last_name": "Иванов" }
}
```

#### Деактивировать аккаунт

```json
{ "action": "deactivate" }
```

#### Активировать аккаунт

```json
{ "action": "activate" }
```

**403** — если целевой пользователь не клиент. **400** — неизвестное `action`.

---

## 5. Финансы

### 5.1 Все транзакции (с фильтрами)

```
GET /api/finance/transactions/?date=2026-03-25&type=BOOKING&method=KASPI&user_id=42
```

**Параметры (все опциональны):**
| Параметр | Описание |
|----------|----------|
| `date` | Дата в формате `YYYY-MM-DD` |
| `type` | Тип: `BOOKING`, `MEMBERSHIP`, `REFUND`, `SALARY`, `OTHER` |
| `method` | Способ оплаты: `KASPI`, `CARD`, `CASH`, `BONUS`, `UNKNOWN` |
| `user_id` | ID пользователя |

**Response 200:** массив транзакций:

```json
[
  {
    "id": 20,
    "amount": "5000.00",
    "transaction_type": "BOOKING",
    "transaction_type_label": "Оплата бронирования",
    "payment_method": "KASPI",
    "payment_method_label": "Kaspi / QR",
    "description": "Оплата брони #101",
    "created_at": "2026-03-25T10:00:00Z",
    "created_at_formatted": "25.03.2026 10:00",
    "amount_court": "5000.00",
    "amount_coach": "0.00",
    "amount_services": "0.00",
    "amount_discount": "0.00",
    "booking": 101,
    "user_membership": null
  }
]
```

---

### 5.2 Финансовая сводка

```
GET /api/finance/summary/?period=today
```

**Параметры:** `period` — `today`, `month` или `all`.

**Response 200:**
```json
{
  "period": "today",
  "total": 150000.0,
  "by_payment_method": {
    "Kaspi / QR": 100000.0,
    "Наличные": 50000.0
  },
  "by_type": {
    "Оплата бронирования": 120000.0,
    "Покупка абонемента": 30000.0
  }
}
```

---

## 6. Абонементы

### 6.1 Выдать абонемент клиенту (ресепшн)

Создаёт абонемент выбранного типа для клиента и запись о транзакции.

```
POST /api/memberships/reception/buy/
```

**Request body:**
```json
{
  "client_id": 42,
  "membership_type_id": 1,
  "payment_method": "CASH"
}
```

`payment_method`: `CASH`, `KASPI`, `CARD`, `UNKNOWN`.

**Response 201:**
```json
{
  "status": "Абонемент выдан",
  "membership_id": 15,
  "client": "Азамат Есимханулы",
  "type": "Padel Pro",
  "end_date": "2026-04-25",
  "payment_method": "CASH"
}
```

**400** — не указаны `client_id` или `membership_type_id`, или тип не найден/неактивен.

---

### 6.2 Список всех абонементов

```
GET /api/memberships/all/?client_id=42&is_active=true
```

**Параметры:**
| Параметр | Описание |
|----------|----------|
| `client_id` | Фильтр по клиенту |
| `is_active` | `true` / `false` — только активные или неактивные |

**Response 200:** массив объектов `UserMembership` с полями вроде: `id`, `user`, `user_name`, `membership_type_name`, `type_name`, `start_date`, `end_date`, `hours_remaining`, `visits_remaining`, `is_active`, `is_frozen`, `freeze_start_date`, `created_at`.

---

### 6.3 Типы абонементов — список (для выбора при выдаче)

Публичный эндпоинт, можно вызывать без токена или с токеном (для выпадающего списка в CRM).

```
GET /api/memberships/types/
```

**Response 200:** массив типов с полями: `id`, `name`, `service_type`, `total_hours`, `total_visits`, `days_valid`, `price`, `description`, `is_active`.  
`service_type`: `PADEL`, `GYM_UNLIMITED`, `GYM_PACK`.

---

## 7. Управление типами абонементов (CRUD)

Доступ: RECEPTIONIST, ADMIN.

### Список всех типов (включая неактивные)

```
GET /api/memberships/types/manage/
```

**Response 200:** массив типов (полная модель, включая `discount_on_court` и т.д.).

### Создать тип

```
POST /api/memberships/types/manage/
```

**Request body (пример):**
```json
{
  "name": "Padel Pro",
  "service_type": "PADEL",
  "price": "50000.00",
  "days_valid": 30,
  "total_hours": "30.0",
  "total_visits": 0,
  "discount_on_court": 0,
  "is_active": true
}
```

### Детали / обновление / удаление

```
GET    /api/memberships/types/manage/{id}/
PATCH  /api/memberships/types/manage/{id}/
DELETE /api/memberships/types/manage/{id}/
```

---

## 8. QR-сканер (вход в зал/падел)

Ресепшн проверяет QR, сгенерированный в мобильном приложении клиента.

```
POST /api/gym/qr/scan/
```

**Request body:**
```json
{
  "qr_content": "2:1vuUZi:zvrSNipTTJ5...",
  "location": "PADEL"
}
```

**location:** `GYM` (турникет зала), `PADEL` (ресепшн падела), `ALL` (общий вход).

**Response 200 (доступ разрешён):**
```json
{
  "status": "SUCCESS",
  "user_id": 42,
  "user": "Азамат Есимханулы",
  "phone": "+77001234567",
  "is_qr_blocked": false,
  "details": "Член клуба (абонемент Падел) | Бронь: Корт 1 (14:00–15:30)"
}
```

**403 (доступ запрещён):**
```json
{
  "status": "DENIED",
  "error": "QR-код устарел. Попросите сгенерировать новый."
}
```

**403 (QR заблокирован):**
```json
{
  "status": "BLOCKED",
  "error": "QR-доступ заблокирован для ... Обратитесь на ресепшн."
}
```

---

## 9. Услуги / инвентарь (CRUD)

**Доступ: только ADMIN.**

### Список всех услуг (включая неактивные)

```
GET /api/inventory/services/manage/
```

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Аренда ракетки",
    "price": "2000.00",
    "is_active": true
  }
]
```

### Создать услугу

```
POST /api/inventory/services/manage/
```

**Request body:**
```json
{
  "name": "Мячи (3 шт)",
  "price": "1500.00",
  "is_active": true
}
```

### Детали / обновление / удаление

```
GET    /api/inventory/services/manage/{id}/
PATCH  /api/inventory/services/manage/{id}/
DELETE /api/inventory/services/manage/{id}/
```

Для выпадающего списка при создании брони используется публичный список: **GET** `/api/inventory/services/` (только активные).

---

## 10. Корты (CRUD)

**Доступ: только ADMIN.**

### Список всех кортов (включая неактивные)

```
GET /api/courts/manage/
```

**Response 200:** массив кортов с полями: `id`, `name`, `court_type`, `description`, `price_per_hour`, `image`, `gallery`, `is_active`.  
`court_type`: `INDOOR`, `OUTDOOR`, `PANORAMIC`.

### Создать корт

```
POST /api/courts/manage/
```

**Request body:**
```json
{
  "name": "Корт 1",
  "court_type": "INDOOR",
  "description": "Основной корт",
  "price_per_hour": "8000.00",
  "is_active": true
}
```

Поле `image` — загрузка файла (multipart/form-data), при необходимости отдельно.

### Детали / обновление / удаление

```
GET    /api/courts/manage/{id}/
PATCH  /api/courts/manage/{id}/
DELETE /api/courts/manage/{id}/
```

В формах создания брони в CRM используется **GET** `/api/courts/` — список активных кортов.

---

## 11. Акции / промокоды (CRUD)

**Доступ: только ADMIN.**

### Список всех акций

```
GET /api/marketing/manage/
```

**Response 200:** массив с полями: `id`, `title`, `description`, `image_url`, `priority`, `promo_code`, `discount_type`, `discount_value`, `start_date`, `end_date`, `is_active`.  
`discount_type`: `PERCENT`, `FIXED`.

### Создать акцию

```
POST /api/marketing/manage/
```

**Request body (пример):**
```json
{
  "title": "Скидка 20% на утро",
  "description": "С 7:00 до 12:00",
  "image_url": "https://...",
  "priority": 10,
  "promo_code": "MORNING20",
  "discount_type": "PERCENT",
  "discount_value": "20.00",
  "start_date": "2026-03-01T00:00:00Z",
  "end_date": "2026-04-01T23:59:59Z",
  "is_active": true
}
```

### Детали / обновление / удаление

```
GET    /api/marketing/manage/{id}/
PATCH  /api/marketing/manage/{id}/
DELETE /api/marketing/manage/{id}/
```

---

## 12. Новости (CRUD)

**Доступ: только ADMIN.**

### Список всех новостей (включая неопубликованные)

```
GET /api/news/manage/
```

**Response 200:** массив с полями: `id`, `title`, `content`, `category`, `category_label`, `image_url`, `is_pinned`, `created_at`, `created_at_formatted`.  
В модели есть также `is_published`, `updated_at` (если сериализатор их отдаёт).

`category`: `NEWS`, `EVENT`, `PROMO`, `ANNOUNCEMENT`.

### Создать новость

```
POST /api/news/manage/
```

**Request body (пример):**
```json
{
  "title": "Открытие нового корта",
  "content": "Текст новости...",
  "category": "NEWS",
  "image_url": "https://...",
  "is_published": true,
  "is_pinned": false
}
```

### Детали / обновление / удаление

```
GET    /api/news/manage/{id}/
PATCH  /api/news/manage/{id}/
DELETE /api/news/manage/{id}/
```

---

## 13. Справочники для форм CRM (без токена или с токеном)

Имеет смысл вызывать при загрузке экранов создания брони и выдачи абонемента.

| Метод | URL | Назначение |
|-------|-----|------------|
| GET | `/api/courts/` | Список активных кортов (выбор корта в брони) |
| GET | `/api/auth/coaches/` | Список тренеров (выбор тренера в брони) |
| GET | `/api/inventory/services/` | Список активных услуг (доп. услуги в брони) |
| GET | `/api/memberships/types/` | Типы абонементов (выдача абонемента) |

Формат ответов описан в **API_MOBILE.md** (корты, тренеры, услуги, типы абонементов).

---

## 14. Обработка ошибок

- **401** — не авторизован или токен истёк. Нужно обновить токен через `/api/auth/jwt/refresh/` или перенаправить на страницу входа.
- **403** — нет прав (например, ресепшн открыл эндпоинт только для ADMIN).
- **404** — ресурс не найден (неверный ID).
- **400** — ошибка валидации. Тело ответа: `{ "field_name": ["сообщение"] }` или `{ "detail": "сообщение" }`.
- **429** — превышен лимит запросов (throttling).

---

## 15. Воронка продаж / Лиды

Система управления потенциальными клиентами (лидами) с канбан-доской.

**Доступ:** RECEPTIONIST, ADMIN.

### Стадии воронки

| Код | Название |
|-----|----------|
| `NEW` | Новые обращения |
| `IN_PROGRESS` | В работе |
| `NEGOTIATION` | Переговоры |
| `SOLD` | Успешная продажа |
| `LOST` | Закрыто / потеря |

### Источники лида

| Код | Название |
|-----|----------|
| `PHONE_CALL` | Звонок |
| `INSTAGRAM` | Instagram |
| `WEBSITE` | Сайт |
| `WALK_IN` | Пришёл сам |
| `REFERRAL` | Рекомендация |
| `WHATSAPP` | WhatsApp |
| `OTHER` | Другое |

---

### 15.1 Канбан-доска (все стадии сразу)

Основной эндпоинт для отрисовки доски. Возвращает лиды, уже сгруппированными по стадиям.

```
GET /api/leads/kanban/?assigned_to=me&search=Азамат
```

**Параметры:**
| Параметр | Описание |
|----------|----------|
| `assigned_to` | `me` — только мои лиды; число — по ID менеджера |
| `search` | Поиск по имени или телефону |

**Response 200:**
```json
[
  {
    "stage": "NEW",
    "label": "Новые обращения",
    "count": 3,
    "leads": [
      {
        "id": 1,
        "name": "Азамат",
        "phone": "+77001234567",
        "email": null,
        "source": "INSTAGRAM",
        "source_label": "Instagram",
        "stage": "NEW",
        "stage_label": "Новые обращения",
        "assigned_to": 2,
        "assigned_to_name": "Иван Ресепшн",
        "last_contact": null,
        "last_contact_formatted": null,
        "created_at": "2026-03-25T10:00:00Z",
        "created_at_formatted": "25.03.2026",
        "comments_count": 0,
        "tasks_count": 1,
        "open_tasks_count": 1
      }
    ]
  },
  { "stage": "IN_PROGRESS", "label": "В работе", "count": 1, "leads": [] },
  { "stage": "NEGOTIATION", "label": "Переговоры", "count": 0, "leads": [] },
  { "stage": "SOLD", "label": "Успешная продажа", "count": 2, "leads": [] },
  { "stage": "LOST", "label": "Закрыто / потеря", "count": 0, "leads": [] }
]
```

---

### 15.2 Список лидов (плоский, с фильтрами)

```
GET /api/leads/?stage=NEW&assigned_to=me&search=Азамат
```

**Response 200:** массив лидов (те же поля, что в одной стадии из канбана).

---

### 15.3 Создать лид

Вызывается из быстрой формы «Добавить лид».

```
POST /api/leads/
```

**Request body:**
```json
{
  "name": "Азамат",
  "phone": "+77001234567",
  "email": "azamat@mail.ru",
  "source": "INSTAGRAM",
  "stage": "NEW",
  "notes": "Интересуется утренними тренировками",
  "assigned_to": 2,
  "last_contact": "2026-03-25T10:00:00Z"
}
```

Обязательные поля: `name`, `phone`. Остальные — опциональные.  
По умолчанию `stage = NEW`, `source = OTHER`.

**Response 201:** полный объект лида (с комментариями и задачами).

---

### 15.4 Детали лида

```
GET /api/leads/{id}/
```

**Response 200:** полный объект с вложенными `comments[]` и `tasks[]`:

```json
{
  "id": 1,
  "name": "Азамат",
  "phone": "+77001234567",
  "email": null,
  "source": "INSTAGRAM",
  "source_label": "Instagram",
  "stage": "IN_PROGRESS",
  "stage_label": "В работе",
  "notes": "Интересуется утренними тренировками",
  "assigned_to": 2,
  "assigned_to_name": "Иван Ресепшн",
  "last_contact": "2026-03-25T10:00:00Z",
  "last_contact_formatted": "25.03.2026 10:00",
  "created_at": "2026-03-20T09:00:00Z",
  "created_at_formatted": "20.03.2026 09:00",
  "comments": [
    {
      "id": 5,
      "text": "Клиент перезвонит в пятницу",
      "author": 2,
      "author_name": "Иван Ресепшн",
      "created_at": "2026-03-25T10:00:00Z",
      "created_at_formatted": "25.03.2026 10:00"
    }
  ],
  "tasks": [
    {
      "id": 3,
      "title": "Перезвонить и уточнить расписание",
      "due_datetime": "2026-03-28T10:00:00Z",
      "due_datetime_formatted": "28.03.2026 10:00",
      "assigned_to": 2,
      "assigned_to_name": "Иван Ресепшн",
      "is_done": false,
      "created_at": "2026-03-25T10:00:00Z"
    }
  ]
}
```

---

### 15.5 Обновить лид

```
PATCH /api/leads/{id}/
```

**Request body** (любые поля из создания, все опциональные):
```json
{
  "notes": "Уточнил — хочет абонемент на 3 месяца",
  "assigned_to": 3
}
```

**Response 200:** полный обновлённый объект лида.

---

### 15.6 Удалить лид

```
DELETE /api/leads/{id}/
```

**Response 204:** нет тела.

---

### 15.7 Переместить лид (drag & drop)

Вызывается при перетаскивании карточки между колонками канбан-доски.

```
POST /api/leads/{id}/move/
```

**Request body:**
```json
{ "stage": "NEGOTIATION" }
```

**Response 200:**
```json
{
  "status": "ok",
  "id": 1,
  "stage": "NEGOTIATION",
  "stage_label": "Переговоры",
  "last_contact": "2026-03-25T12:00:00Z"
}
```

Автоматически обновляет `last_contact` на текущее время.

---

### 15.8 Добавить комментарий (история взаимодействий)

```
POST /api/leads/{id}/comments/
```

**Request body:**
```json
{ "text": "Клиент перезвонит в пятницу, интересует корт 1" }
```

**Response 201:**
```json
{
  "id": 6,
  "text": "Клиент перезвонит в пятницу, интересует корт 1",
  "author": 2,
  "author_name": "Иван Ресепшн",
  "created_at": "2026-03-25T11:00:00Z",
  "created_at_formatted": "25.03.2026 11:00"
}
```

Добавление комментария автоматически обновляет `last_contact` лида.

---

### 15.9 Список комментариев к лиду

```
GET /api/leads/{id}/comments/
```

**Response 200:** массив комментариев (те же поля).

---

### 15.10 Удалить комментарий

```
DELETE /api/leads/{id}/comments/{comment_id}/
```

Менеджер может удалить только свой комментарий. ADMIN — любой.  
**Response 204:** нет тела.

---

### 15.11 Добавить задачу / напоминание

```
POST /api/leads/{id}/tasks/
```

**Request body:**
```json
{
  "title": "Перезвонить и уточнить расписание",
  "due_datetime": "2026-03-28T10:00:00Z",
  "assigned_to": 2
}
```

| Поле | Обязательное | Описание |
|------|--------------|----------|
| `title` | да | Текст задачи |
| `due_datetime` | да | Срок выполнения (ISO) |
| `assigned_to` | нет | ID сотрудника-исполнителя |

**Response 201:** объект задачи.

---

### 15.12 Список задач лида

```
GET /api/leads/{id}/tasks/
```

**Response 200:** массив задач.

---

### 15.13 Обновить задачу (отметить выполненной)

```
PATCH /api/leads/{id}/tasks/{task_id}/
```

**Request body (пример — отметить выполненной):**
```json
{ "is_done": true }
```

**Response 200:** обновлённый объект задачи.

---

### 15.14 Удалить задачу

```
DELETE /api/leads/{id}/tasks/{task_id}/
```

**Response 204:** нет тела.

---

### 15.15 Статистика воронки

```
GET /api/leads/stats/
```

**Response 200:**
```json
{
  "total": 42,
  "sold_count": 18,
  "conversion_rate": 42.9,
  "stages": [
    { "stage": "NEW",         "label": "Новые обращения",   "count": 10, "percent": 23.8 },
    { "stage": "IN_PROGRESS", "label": "В работе",          "count": 8,  "percent": 19.0 },
    { "stage": "NEGOTIATION", "label": "Переговоры",        "count": 6,  "percent": 14.3 },
    { "stage": "SOLD",        "label": "Успешная продажа",  "count": 18, "percent": 42.9 },
    { "stage": "LOST",        "label": "Закрыто / потеря",  "count": 0,  "percent": 0.0  }
  ]
}
```

---

## 16. Рекомендации для React

- **Хранение токена:** после успешного `POST /api/auth/crm/login/` сохранять `access` и `refresh` (например, в памяти + localStorage или только в памяти для большей безопасности).
- **Заголовок запросов:** для всех запросов к API добавлять `Authorization: Bearer ${accessToken}`. При ответе 401 — попробовать обновить токен через `POST /api/auth/jwt/refresh/` с сохранённым `refresh`; при успехе — повторить исходный запрос с новым `access`.
- **Base URL:** вынести в конфиг (например, `process.env.REACT_APP_API_URL` или константа), по умолчанию `http://213.155.23.227/api`.
- **Роутинг по ролям:** после логина проверять `role` из ответа и показывать/скрывать разделы (например, «Дашборд директора», «Управление кортами/услугами/акциями/новостями» только для ADMIN).
- **Даты в формах:** для `start_time` при создании брони отправлять значение в ISO 8601 (например, из `<input type="datetime-local">` преобразовать в ISO с учётом таймзоны сервера).

---

## Сводная таблица эндпоинтов CRM

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| POST | `/api/auth/crm/login/` | — | Вход в CRM |
| POST | `/api/auth/jwt/refresh/` | — | Обновить токен |
| POST | `/api/auth/jwt/verify/` | — | Проверить токен |
| GET | `/api/analytics/reception/` | Ресепшн, Админ | Дашборд ресепшн |
| GET | `/api/analytics/dashboard/` | Только Админ | Дашборд директора |
| GET | `/api/bookings/manager/schedule/?date=` | Ресепшн, Админ | Расписание по кортам |
| GET | `/api/bookings/all/?date=&status=&court_id=&client_id=` | Ресепшн, Админ | Все брони |
| POST | `/api/bookings/reception/create/` | Ресепшн, Админ | Создать бронь за клиента |
| POST | `/api/bookings/{id}/confirm-payment/` | Ресепшн, Админ | Подтвердить оплату |
| GET | `/api/auth/clients/?search=&role=` | Ресепшн, Админ | Список клиентов |
| GET | `/api/auth/reception/search/?phone=` | Ресепшн, Админ | Поиск по телефону |
| GET | `/api/auth/reception/user/{id}/` | Ресепшн, Админ | Карточка клиента |
| POST | `/api/auth/reception/user/{id}/action/` | Ресепшн, Админ | Действия с клиентом |
| GET | `/api/finance/transactions/?date=&type=&method=&user_id=` | Ресепшн, Админ | Транзакции |
| GET | `/api/finance/summary/?period=` | Ресепшн, Админ | Сводка |
| POST | `/api/memberships/reception/buy/` | Ресепшн, Админ | Выдать абонемент |
| GET | `/api/memberships/all/?client_id=&is_active=` | Ресепшн, Админ | Все абонементы |
| GET/POST | `/api/memberships/types/manage/` | Ресепшн, Админ | Типы абонементов |
| GET/PATCH/DELETE | `/api/memberships/types/manage/{id}/` | Ресепшн, Админ | Тип по ID |
| POST | `/api/gym/qr/scan/` | Ресепшн, Админ | Сканировать QR |
| GET/POST | `/api/inventory/services/manage/` | Только Админ | Услуги |
| GET/PATCH/DELETE | `/api/inventory/services/manage/{id}/` | Только Админ | Услуга по ID |
| GET/POST | `/api/courts/manage/` | Только Админ | Корты |
| GET/PATCH/DELETE | `/api/courts/manage/{id}/` | Только Админ | Корт по ID |
| GET/POST | `/api/marketing/manage/` | Только Админ | Акции |
| GET/PATCH/DELETE | `/api/marketing/manage/{id}/` | Только Админ | Акция по ID |
| GET/POST | `/api/news/manage/` | Только Админ | Новости |
| GET/PATCH/DELETE | `/api/news/manage/{id}/` | Только Админ | Новость по ID |
| GET | `/api/courts/` | — | Список кортов (для форм) |
| GET | `/api/auth/coaches/` | — | Список тренеров (для форм) |
| GET | `/api/inventory/services/` | — | Список услуг (для форм) |
| GET | `/api/memberships/types/` | — | Типы абонементов (для форм) |
| **Лиды / Воронка продаж** | | | |
| GET | `/api/leads/kanban/` | Ресепшн, Админ | Канбан-доска (все стадии сразу) |
| GET | `/api/leads/stats/` | Ресепшн, Админ | Статистика воронки |
| GET/POST | `/api/leads/` | Ресепшн, Админ | Список лидов / создать лид |
| GET/PATCH/DELETE | `/api/leads/{id}/` | Ресепшн, Админ | Детали / ред. / удаление лида |
| POST | `/api/leads/{id}/move/` | Ресепшн, Админ | Переместить в другую стадию (drag & drop) |
| GET/POST | `/api/leads/{id}/comments/` | Ресепшн, Админ | История взаимодействий |
| DELETE | `/api/leads/{id}/comments/{comment_id}/` | Ресепшн, Админ | Удалить комментарий |
| GET/POST | `/api/leads/{id}/tasks/` | Ресепшн, Админ | Задачи / напоминания |
| PATCH/DELETE | `/api/leads/{id}/tasks/{task_id}/` | Ресепшн, Админ | Обновить / удалить задачу |
