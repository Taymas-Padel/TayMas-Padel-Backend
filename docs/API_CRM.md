# Padel Club — Полная документация CRM-системы (для React)

> Единый справочник для разработчика фронтенда CRM.  
> Backend: Django 4.2 + DRF + JWT | DB: PostgreSQL  
> Мобильное приложение — отдельная документация: **`API_MOBILE.md`**

---

## Содержание

1. [Общие сведения](#1-общие-сведения)
2. [Роли и права доступа](#2-роли-и-права-доступа)
3. [Навигация CRM (структура меню)](#3-навигация-crm-структура-меню)
4. [Авторизация](#4-авторизация)
5. [Главная панель (Dashboard)](#5-главная-панель-dashboard)
6. [Управление клиентской базой](#6-управление-клиентской-базой)
7. [Система управления лидами (Воронка продаж)](#7-система-управления-лидами-воронка-продаж)
8. [Управление бронированиями](#8-управление-бронированиями)
9. [Система абонементов](#9-система-абонементов)
10. [База тренеров](#10-база-тренеров)
11. [Управление кортами](#11-управление-кортами)
12. [Услуги и инвентарь](#12-услуги-и-инвентарь)
13. [Финансовый модуль](#13-финансовый-модуль)
14. [QR-сканер (вход в клуб)](#14-qr-сканер-вход-в-клуб)
15. [Маркетинг (акции и промокоды)](#15-маркетинг-акции-и-промокоды)
16. [Новости и объявления](#16-новости-и-объявления)
17. [Уведомления](#17-уведомления)
18. [Настройки клуба](#18-настройки-клуба)
19. [Турниры и мероприятия](#19-турниры-и-мероприятия-планируется)
20. [Аналитика и отчетность](#20-аналитика-и-отчетность-планируется)
21. [Управление пользователями CRM](#21-управление-пользователями-crm)
22. [Справочники для форм](#22-справочники-для-форм)
23. [Обработка ошибок](#23-обработка-ошибок)
24. [Рекомендации для React](#24-рекомендации-для-react)
25. [Сводная таблица всех эндпоинтов](#25-сводная-таблица-всех-эндпоинтов)

---

## 1. Общие сведения

| Параметр | Значение |
|----------|-----------|
| **Base URL** | `http://213.155.23.227/api` |
| **Swagger** | `http://213.155.23.227/swagger/` |
| **Авторизация** | JWT: заголовок `Authorization: Bearer <access_token>` |
| **Content-Type** | `application/json` |
| **Даты/время** | ISO 8601 (`2026-03-28T14:00:00Z`) |
| **Деньги** | `string` (decimal, 2 знака): `"5000.00"` |

---

## 2. Роли и права доступа

### 2.1 Роли CRM

| Роль | Вход в CRM | Описание |
|------|------------|----------|
| **ADMIN** | По паролю | Полный доступ: всё ниже + управление кортами, услугами, акциями, новостями, системные настройки |
| **RECEPTIONIST** | По паролю | Дашборды, клиенты, брони, оплаты, абонементы, расписание, финансы, QR, лиды |
| **SALES_MANAGER** | По паролю | Лиды/воронка продаж, просмотр клиентов. Не видит: брони, финансы, QR, управление |

### 2.2 Матрица доступа по модулям

| Модуль CRM | ADMIN | RECEPTIONIST | SALES_MANAGER |
|------------|:-----:|:------------:|:-------------:|
| Дашборд ресепшн | ✅ | ✅ | ❌ |
| Дашборд директора | ✅ | ❌ | ❌ |
| Клиенты (просмотр, поиск) | ✅ | ✅ | ✅ (только просмотр) |
| Действия с клиентом (QR, деактивация) | ✅ | ✅ | ❌ |
| Лиды / Воронка продаж | ✅ | ✅ | ✅ |
| Расписание кортов | ✅ | ✅ | ❌ |
| Все бронирования | ✅ | ✅ | ❌ |
| Создать бронь | ✅ | ✅ | ❌ |
| Подтвердить оплату | ✅ | ✅ | ❌ |
| Финансы (транзакции, сводка) | ✅ | ✅ | ❌ |
| Выдать абонемент | ✅ | ✅ | ❌ |
| Все абонементы | ✅ | ✅ | ❌ |
| QR-сканер | ✅ | ✅ | ❌ |
| Управление кортами (CRUD) | ✅ | ❌ | ❌ |
| Управление услугами (CRUD) | ✅ | ❌ | ❌ |
| Управление типами абонементов | ✅ | ✅ | ❌ |
| Управление акциями (CRUD) | ✅ | ❌ | ❌ |
| Управление новостями (CRUD) | ✅ | ❌ | ❌ |
| Настройки клуба | ✅ | ❌ | ❌ |

### 2.3 React: роутинг по ролям

После логина (из поля `role` в ответе) фронтенд должен:
- Показывать/скрывать пункты меню согласно матрице выше
- При `role === 'SALES_MANAGER'` — показывать только: Лиды, Клиенты (только просмотр)
- При `role === 'RECEPTIONIST'` — всё кроме управления кортами/услугами/акциями/новостями/настроек
- При `role === 'ADMIN'` — всё

---

## 3. Навигация CRM (структура меню)

Рекомендуемая структура sidebar для React:

```
📊  Главная панель
    ├── Дашборд ресепшн          (RECEPTIONIST, ADMIN)
    └── Дашборд директора        (только ADMIN)

👥  Клиенты
    ├── База клиентов            (все CRM-роли)
    ├── Поиск по телефону        (все CRM-роли)
    └── Карточка клиента         (RECEPTIONIST, ADMIN)

📊  Лиды / Воронка продаж
    ├── Канбан-доска             (все CRM-роли)
    ├── Список лидов             (все CRM-роли)
    └── Статистика воронки       (все CRM-роли)

📅  Бронирования
    ├── Расписание кортов        (RECEPTIONIST, ADMIN)
    ├── Все бронирования         (RECEPTIONIST, ADMIN)
    └── Создать бронь            (RECEPTIONIST, ADMIN)

🎫  Абонементы
    ├── Выдать абонемент         (RECEPTIONIST, ADMIN)
    ├── Все абонементы           (RECEPTIONIST, ADMIN)
    └── Типы абонементов (CRUD)  (RECEPTIONIST, ADMIN)

👨‍🏫  Тренеры
    └── Список тренеров          (RECEPTIONIST, ADMIN)

💰  Финансы
    ├── Транзакции               (RECEPTIONIST, ADMIN)
    └── Сводка                   (RECEPTIONIST, ADMIN)

📱  QR-сканер                    (RECEPTIONIST, ADMIN)

⚙️  Управление (только ADMIN)
    ├── Корты (CRUD)
    ├── Услуги / Инвентарь (CRUD)
    ├── Акции / Промокоды (CRUD)
    ├── Новости (CRUD)
    └── Настройки клуба
```

---

## 4. Авторизация

### 4.1 Вход в CRM

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

Допустимые роли для CRM: `ADMIN`, `RECEPTIONIST`, `SALES_MANAGER`.

**Errors:** `401` — неверный логин/пароль. `403` — роль не имеет доступа к CRM.

---

### 4.2 Обновление токена

```
POST /api/auth/jwt/refresh/
```

**Request:** `{ "refresh": "eyJ..." }`  
**Response:** `{ "access": "eyJ...", "refresh": "eyJ..." }`

Старый refresh аннулируется — сохраняйте новый.

---

### 4.3 Проверка токена

```
POST /api/auth/jwt/verify/
```

**Request:** `{ "token": "<access_token>" }`  
**200** — валиден. **401** — истёк или невалиден.

---

## 5. Главная панель (Dashboard)

### 5.1 Дашборд ресепшн

Сводка на сегодня: брони, ожидающие оплаты, выручка, ближайшие брони.

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

**React-подсказка:** KPI-карточки вверху (4 метрики), ниже — таблица/список ближайших броней с кнопкой «Принять оплату» для неоплаченных.

---

### 5.2 Дашборд директора

Расширенная аналитика: выручка по периодам, загрузка кортов, структура выручки.

```
GET /api/analytics/dashboard/
```

**Доступ:** только ADMIN

**Response 200:**
```json
{
  "period": { "date": "2026-03-25", "month": "March 2026" },
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
    { "type": "BOOKING", "label": "Оплата бронирования", "amount": 800000.0, "count": 120 },
    { "type": "MEMBERSHIP", "label": "Покупка абонемента", "amount": 400000.0, "count": 15 }
  ],
  "work_hours": "7:00 – 23:00"
}
```

**React-подсказка:** 8 KPI-карточек (в 2 ряда по 4), блок «Структура выручки» — bar chart или список карточек.

---

## 6. Управление клиентской базой

### 6.1 Список клиентов (с поиском и фильтрами)

```
GET /api/auth/clients/?search=иван&role=CLIENT
```

**Доступ:** RECEPTIONIST, ADMIN, SALES_MANAGER

| Параметр | Описание |
|----------|----------|
| `search` | Поиск по имени, фамилии, телефону, username |
| `role` | `CLIENT`, `COACH_PADEL`, `COACH_FITNESS`, или пусто (клиенты + тренеры) |

**Response 200:**
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

**React-подсказка:** таблица с колонками: Аватар, Имя, Телефон, Роль, QR-статус, ELO, Дата регистрации. Строка кликабельна → открывает карточку клиента.

---

### 6.2 Быстрый поиск по телефону

```
GET /api/auth/reception/search/?phone=7700
```

**Доступ:** RECEPTIONIST, ADMIN

**Параметры:** `phone` — минимум 4 символа. Возвращает только пользователей с ролью CLIENT.

**Response 200:** массив клиентов (те же поля).

**React-подсказка:** используется как автокомплит при создании брони или выдаче абонемента.

---

### 6.3 Карточка клиента (детальный профиль)

```
GET /api/auth/reception/user/{id}/
```

**Доступ:** RECEPTIONIST, ADMIN

**Response 200:** один объект пользователя (как в 6.1).

**React-подсказка:** показывать: контактные данные, QR-статус, ELO, дата регистрации. Внизу — кнопки действий и вкладки: «Брони клиента» (GET `/api/bookings/all/?client_id={id}`), «Абонементы» (GET `/api/memberships/all/?client_id={id}`), «Транзакции» (GET `/api/finance/transactions/?user_id={id}`).

---

### 6.4 Действия с клиентом

```
POST /api/auth/reception/user/{id}/action/
```

**Доступ:** RECEPTIONIST, ADMIN. Действия доступны только для пользователей с ролью CLIENT.

#### Разблокировать QR

**Request:** `{ "action": "unblock_qr" }`  
**Response:** `{ "status": "success", "message": "QR-код разблокирован...", "is_qr_blocked": false }`

#### Обновить имя/фамилию

**Request:** `{ "action": "update_info", "first_name": "Иван", "last_name": "Иванов" }`  
**Response:** `{ "status": "success", "message": "Данные обновлены.", "user": { "id": 42, "first_name": "Иван", "last_name": "Иванов" } }`

#### Деактивировать аккаунт

**Request:** `{ "action": "deactivate" }`

#### Активировать аккаунт

**Request:** `{ "action": "activate" }`

**Ошибки:** `403` — если целевой пользователь не клиент. `400` — неизвестное action.

---

## 7. Система управления лидами (Воронка продаж)

Модуль для работы с потенциальными клиентами. Канбан-доска с drag & drop.

**Доступ:** ADMIN, RECEPTIONIST, SALES_MANAGER

### Стадии воронки

| Код | Название | Цвет (рекомендация) |
|-----|----------|---------------------|
| `NEW` | Новые обращения | синий |
| `IN_PROGRESS` | В работе | оранжевый |
| `NEGOTIATION` | Переговоры | фиолетовый |
| `SOLD` | Успешная продажа | зелёный |
| `LOST` | Закрыто / потеря | красный |

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

### 7.1 Канбан-доска (все стадии сразу)

```
GET /api/leads/kanban/?assigned_to=me&search=Азамат
```

| Параметр | Описание |
|----------|----------|
| `assigned_to` | `me` — мои лиды; число — по ID менеджера; пусто — все |
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
        "assigned_to_name": "Иван Менеджер",
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
  { "stage": "IN_PROGRESS", "label": "В работе", "count": 1, "leads": [...] },
  { "stage": "NEGOTIATION", "label": "Переговоры", "count": 0, "leads": [] },
  { "stage": "SOLD", "label": "Успешная продажа", "count": 2, "leads": [...] },
  { "stage": "LOST", "label": "Закрыто / потеря", "count": 0, "leads": [] }
]
```

**React-подсказка:** рендерить 5 колонок (каждый элемент массива — колонка). Карточка лида: имя, телефон, источник, менеджер, кол-во открытых задач. Drag & drop — при перетаскивании вызывать `POST /api/leads/{id}/move/`.

---

### 7.2 Список лидов (плоский, с фильтрами)

```
GET /api/leads/?stage=NEW&assigned_to=me&search=Азамат
```

**Response:** массив лидов (формат как в одной стадии канбана).

---

### 7.3 Создать лид

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

| Поле | Обязательное | По умолчанию |
|------|:------------:|:------------:|
| `name` | да | — |
| `phone` | да | — |
| `email` | нет | null |
| `source` | нет | `OTHER` |
| `stage` | нет | `NEW` |
| `notes` | нет | пусто |
| `assigned_to` | нет | null |
| `last_contact` | нет | null |

**Response 201:** полный объект лида (с `comments[]` и `tasks[]`).

**React-подсказка:** быстрая модалка с полями: имя, телефон, email, источник (select), менеджер (select, загрузить из `/api/auth/clients/?role=ADMIN` + `?role=RECEPTIONIST` + `?role=SALES_MANAGER`), заметки.

---

### 7.4 Детали лида (карточка)

```
GET /api/leads/{id}/
```

**Response 200:**
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
  "assigned_to_name": "Иван Менеджер",
  "last_contact": "2026-03-25T10:00:00Z",
  "last_contact_formatted": "25.03.2026 10:00",
  "created_at": "2026-03-20T09:00:00Z",
  "created_at_formatted": "20.03.2026 09:00",
  "comments": [
    {
      "id": 5,
      "text": "Клиент перезвонит в пятницу",
      "author": 2,
      "author_name": "Иван Менеджер",
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
      "assigned_to_name": "Иван Менеджер",
      "is_done": false,
      "created_at": "2026-03-25T10:00:00Z"
    }
  ]
}
```

**React-подсказка:** модальное окно или страница с блоками: Контакты, Стадия (кнопки переключения), Менеджер (select), Заметки, История комментариев (хронология), Задачи (чекбоксы).

---

### 7.5 Обновить лид

```
PATCH /api/leads/{id}/
```

**Request body** (все поля опциональные): `{ "notes": "...", "assigned_to": 3 }`  
**Response 200:** полный обновлённый объект.

---

### 7.6 Удалить лид

```
DELETE /api/leads/{id}/
```

**Response 204.**

---

### 7.7 Переместить лид (drag & drop)

```
POST /api/leads/{id}/move/
```

**Request:** `{ "stage": "NEGOTIATION" }`

**Response 200:**
```json
{ "status": "ok", "id": 1, "stage": "NEGOTIATION", "stage_label": "Переговоры", "last_contact": "2026-03-25T12:00:00Z" }
```

Автоматически обновляет `last_contact`.

---

### 7.8 Комментарии (история взаимодействий)

**Список:**
```
GET /api/leads/{id}/comments/
```

**Добавить:**
```
POST /api/leads/{id}/comments/
```
**Request:** `{ "text": "Клиент перезвонит в пятницу" }`  
**Response 201:** объект комментария. Автоматически обновляет `last_contact`.

**Удалить:**
```
DELETE /api/leads/{id}/comments/{comment_id}/
```
Менеджер может удалить только свой. ADMIN — любой.

---

### 7.9 Задачи / напоминания

**Список:**
```
GET /api/leads/{id}/tasks/
```

**Добавить:**
```
POST /api/leads/{id}/tasks/
```
**Request:**
```json
{ "title": "Перезвонить", "due_datetime": "2026-03-28T10:00:00Z", "assigned_to": 2 }
```
`title` и `due_datetime` обязательны. `assigned_to` опционален.

**Обновить (отметить выполненной):**
```
PATCH /api/leads/{id}/tasks/{task_id}/
```
**Request:** `{ "is_done": true }`

**Удалить:**
```
DELETE /api/leads/{id}/tasks/{task_id}/
```

---

### 7.10 Статистика воронки

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
    { "stage": "NEW", "label": "Новые обращения", "count": 10, "percent": 23.8 },
    { "stage": "IN_PROGRESS", "label": "В работе", "count": 8, "percent": 19.0 },
    { "stage": "NEGOTIATION", "label": "Переговоры", "count": 6, "percent": 14.3 },
    { "stage": "SOLD", "label": "Успешная продажа", "count": 18, "percent": 42.9 },
    { "stage": "LOST", "label": "Закрыто / потеря", "count": 0, "percent": 0.0 }
  ]
}
```

**React-подсказка:** 3 KPI-карточки (всего, продажи, конверсия %) + progress-bar по каждой стадии.

---

### 7.11 Получить список менеджеров (для select «Назначить менеджера»)

Специального эндпоинта нет — используются 3 запроса к `/api/auth/clients/`:

```
GET /api/auth/clients/?role=ADMIN
GET /api/auth/clients/?role=RECEPTIONIST
GET /api/auth/clients/?role=SALES_MANAGER
```

Объединить результаты → заполнить dropdown «Менеджер». Кешировать на время сессии.

---

## 8. Управление бронированиями

### 8.1 Расписание по кортам на дату

```
GET /api/bookings/manager/schedule/?date=YYYY-MM-DD
```

**Доступ:** RECEPTIONIST, ADMIN

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

**React-подсказка:** визуализация — таблица или timeline. Колонки: время слота (с шагом 30/60 мин), строки: корты. Цвет ячейки по `status`. Клик по занятому слоту → детали брони.

---

### 8.2 Все брони (список с фильтрами)

```
GET /api/bookings/all/?date=YYYY-MM-DD&status=CONFIRMED&court_id=1&client_id=42
```

| Параметр | Описание |
|----------|----------|
| `date` | Дата |
| `status` | `PENDING`, `CONFIRMED`, `CANCELED`, `COMPLETED` |
| `court_id` | ID корта |
| `client_id` | ID клиента |

**Response 200:** массив броней (те же поля, что в расписании).

---

### 8.3 Создать бронь от имени клиента

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
  "services": [{ "service_id": 1, "quantity": 1 }]
}
```

| Поле | Обязательное | Описание |
|------|:------------:|----------|
| `client_id` | да | Выбирается из поиска клиентов |
| `court` | да | Выбирается из `/api/courts/` |
| `start_time` | да | ISO 8601 |
| `duration` | да | Минуты: 30, 60, 90, 120 |
| `coach` | нет | Из `/api/auth/coaches/` |
| `payment_method` | нет | `KASPI`, `CARD`, `CASH` |
| `promo_code` | нет | Промокод |
| `services` | нет | Из `/api/inventory/services/` |

**React-подсказка:** форма с автокомплитом клиента (поиск по телефону), select кортов (подгрузить список), select тренеров, чекбоксы услуг. Preview стоимости (корт × часы + тренер + услуги). Валидация: бэкенд проверит занятость корта, время работы, выходные.

**Response 201:** объект созданной брони.  
**400:** `{ "detail": "Корт занят..." }` или `{ "field": ["error"] }`.

---

### 8.4 Подтвердить оплату брони

```
POST /api/bookings/{id}/confirm-payment/
```

**Request:** `{ "payment_method": "CASH" }`

Допустимые: `KASPI`, `CARD`, `CASH`, `UNKNOWN`.

**Response 200:**
```json
{ "status": "Оплата подтверждена.", "booking_id": 101, "is_paid": true, "payment_method": "CASH" }
```

---

## 9. Система абонементов

### 9.1 Выдать абонемент клиенту

```
POST /api/memberships/reception/buy/
```

**Доступ:** RECEPTIONIST, ADMIN

**Request:**
```json
{
  "client_id": 42,
  "membership_type_id": 1,
  "payment_method": "CASH"
}
```

**React-подсказка:** поиск клиента (автокомплит) → выбор типа абонемента (карточки с ценой, сроком, часами) → выбор оплаты → «Выдать».

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

---

### 9.2 Все абонементы (список)

```
GET /api/memberships/all/?client_id=42&is_active=true
```

| Параметр | Описание |
|----------|----------|
| `client_id` | Фильтр по клиенту |
| `is_active` | `true` / `false` |

**Response 200:** массив с полями: `id`, `user`, `user_name`, `membership_type_name`, `start_date`, `end_date`, `hours_remaining`, `visits_remaining`, `is_active`, `is_frozen`, `created_at`.

---

### 9.3 Типы абонементов — публичный список

```
GET /api/memberships/types/
```

**Auth:** не требуется

**Response 200:** массив типов: `id`, `name`, `service_type` (`PADEL`/`GYM_UNLIMITED`/`GYM_PACK`), `total_hours`, `total_visits`, `days_valid`, `price`, `description`, `is_active`.

---

### 9.4 Типы абонементов — управление (CRUD)

**Доступ:** RECEPTIONIST, ADMIN

**Список (включая неактивные):**
```
GET /api/memberships/types/manage/
```

**Создать:**
```
POST /api/memberships/types/manage/
```
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

**Детали / обновление / удаление:**
```
GET    /api/memberships/types/manage/{id}/
PATCH  /api/memberships/types/manage/{id}/
DELETE /api/memberships/types/manage/{id}/
```

---

## 10. База тренеров

### 10.1 Список тренеров

```
GET /api/auth/coaches/
```

**Auth:** не требуется (публичный, используется в формах)

**Response 200:**
```json
[
  {
    "id": 3,
    "full_name": "Алексей Тренер",
    "role": "COACH_PADEL",
    "coach_price": 5000.0,
    "coach_price_1_2": 24000,
    "coach_price_3_4": 36000,
    "phone_number": "+77001112233",
    "avatar": null
  }
]
```

| Поле | Описание |
|------|----------|
| `coach_price` | Цена за час по умолчанию (из `price_per_hour`) |
| `coach_price_1_2` | Цена за час при 1–2 игроках (тариф по документу); может быть `null` |
| `coach_price_3_4` | Цена за час при 3–4 игроках; может быть `null` |

Для превью стоимости тренера: при 1–2 игроках использовать `coach_price_1_2 ?? coach_price`, при 3–4 — `coach_price_3_4 ?? coach_price`. Подробнее: **`docs/FRONTEND_COACH_PRICE_1_2_3_4.md`**.

### 10.2 Фильтр по роли

Можно получить список тренеров через клиентский эндпоинт:

```
GET /api/auth/clients/?role=COACH_PADEL
GET /api/auth/clients/?role=COACH_FITNESS
```

**React-подсказка:** таблица тренеров с колонками: Аватар, Имя, Специализация (PADEL/FITNESS), Цена/час, ELO, Статус. Клик → карточка.

---

## 11. Управление кортами

**Доступ: только ADMIN.**

### 11.1 Список всех кортов (включая неактивные)

```
GET /api/courts/manage/
```

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Корт 1",
    "court_type": "INDOOR",
    "description": "Основной корт",
    "price_per_hour": "8000.00",
    "image": "http://.../courts/photo.jpg",
    "gallery": [{ "id": 1, "image": "http://..." }],
    "is_active": true
  }
]
```

`court_type`: `INDOOR` (крытый), `OUTDOOR` (открытый), `PANORAMIC` (панорамный).

### 11.2 Создать корт

```
POST /api/courts/manage/
```
```json
{ "name": "Корт 1", "court_type": "INDOOR", "description": "...", "price_per_hour": "8000.00", "is_active": true }
```

`image` — загрузка файла (`multipart/form-data`).

### 11.3 Детали / обновление / удаление

```
GET    /api/courts/manage/{id}/
PATCH  /api/courts/manage/{id}/
DELETE /api/courts/manage/{id}/
```

### 11.4 Публичный список активных кортов (для форм)

```
GET /api/courts/
```

---

## 12. Услуги и инвентарь

**Доступ: только ADMIN.**

### 12.1 Список всех услуг

```
GET /api/inventory/services/manage/
```

**Response 200:**
```json
[{ "id": 1, "name": "Аренда ракетки", "price": "2000.00", "is_active": true }]
```

### 12.2 Создать услугу

```
POST /api/inventory/services/manage/
```
```json
{ "name": "Мячи (3 шт)", "price": "1500.00", "is_active": true }
```

### 12.3 Детали / обновление / удаление

```
GET    /api/inventory/services/manage/{id}/
PATCH  /api/inventory/services/manage/{id}/
DELETE /api/inventory/services/manage/{id}/
```

### 12.4 Публичный список активных услуг

```
GET /api/inventory/services/
```

---

## 13. Финансовый модуль

### 13.1 Все транзакции (с фильтрами)

```
GET /api/finance/transactions/?date=2026-03-25&type=BOOKING&method=KASPI&user_id=42
```

**Доступ:** RECEPTIONIST, ADMIN

| Параметр | Описание |
|----------|----------|
| `date` | `YYYY-MM-DD` |
| `type` | `BOOKING`, `MEMBERSHIP`, `REFUND`, `SALARY`, `OTHER` |
| `method` | `KASPI`, `CARD`, `CASH`, `BONUS`, `UNKNOWN` |
| `user_id` | ID пользователя |

**Response 200:**
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

### 13.2 Финансовая сводка

```
GET /api/finance/summary/?period=today
```

**Параметры:** `period` = `today` | `month` | `all`

**Response 200:**
```json
{
  "period": "today",
  "total": 150000.0,
  "by_payment_method": { "Kaspi / QR": 100000.0, "Наличные": 50000.0 },
  "by_type": { "Оплата бронирования": 120000.0, "Покупка абонемента": 30000.0 }
}
```

---

## 14. QR-сканер (вход в клуб)

```
POST /api/gym/qr/scan/
```

**Доступ:** RECEPTIONIST, ADMIN

**Request:**
```json
{ "qr_content": "2:1vuUZi:zvrSNipTTJ5...", "location": "PADEL" }
```

`location`: `GYM`, `PADEL`, `ALL`

**Response 200 (доступ разрешён):**
```json
{ "status": "SUCCESS", "user_id": 42, "user": "Азамат Есимханулы", "phone": "+77001234567", "details": "Бронь: Корт 1 (14:00–15:30)" }
```

**403:** `{ "status": "DENIED", "error": "QR-код устарел..." }` или `{ "status": "BLOCKED", "error": "QR-доступ заблокирован..." }`

---

## 15. Маркетинг (акции и промокоды)

**Доступ: только ADMIN.**

### Список

```
GET /api/marketing/manage/
```

**Response:** массив: `id`, `title`, `description`, `image_url`, `priority`, `promo_code`, `discount_type` (`PERCENT`/`FIXED`), `discount_value`, `start_date`, `end_date`, `is_active`.

### Создать

```
POST /api/marketing/manage/
```
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
GET/PATCH/DELETE /api/marketing/manage/{id}/
```

---

## 16. Новости и объявления

**Доступ: только ADMIN.**

### Список

```
GET /api/news/manage/
```

**Response:** массив: `id`, `title`, `content`, `category` (`NEWS`/`EVENT`/`PROMO`/`ANNOUNCEMENT`), `category_label`, `image_url`, `is_pinned`, `created_at`, `created_at_formatted`.

### Создать

```
POST /api/news/manage/
```
```json
{ "title": "Открытие нового корта", "content": "...", "category": "NEWS", "image_url": "https://...", "is_published": true, "is_pinned": false }
```

### Детали / обновление / удаление

```
GET/PATCH/DELETE /api/news/manage/{id}/
```

---

## 17. Уведомления

Система in-app уведомлений. Типы: `BOOKING`, `MEMBERSHIP`, `FRIEND`, `MATCH`, `LOBBY`, `PROMO`, `NEWS`, `PAYMENT`, `SYSTEM`.

### 17.1 Список уведомлений

```
GET /api/notifications/
```

**Response 200:** массив: `id`, `notification_type`, `title`, `body`, `is_read`, `data` (JSON), `created_at`.

### 17.2 Количество непрочитанных

```
GET /api/notifications/unread-count/
```

**Response:** `{ "unread_count": 5 }`

### 17.3 Отметить прочитанным

```
POST /api/notifications/{id}/mark-read/
```

### 17.4 Отметить все прочитанными

```
POST /api/notifications/mark-all-read/
```

### 17.5 Удалить

```
DELETE /api/notifications/{id}/
```

**React-подсказка:** иконка колокольчика в header с badge (`unread_count`). Dropdown/панель со списком уведомлений. Клик → отметить прочитанным.

---

## 18. Настройки клуба

### 18.1 Список настроек

```
GET /api/core/settings/
```

**Response 200:**
```json
[
  { "key": "OPEN_TIME", "value": "07:00", "description": "Время открытия" },
  { "key": "CLOSE_TIME", "value": "23:00", "description": "Время закрытия" },
  { "key": "CANCELLATION_HOURS", "value": "2", "description": "Часы до начала для отмены" }
]
```

### 18.2 Выходные / закрытые дни

```
GET /api/core/closed-days/
```

**Response 200:**
```json
[
  { "date": "2026-03-08", "reason": "Международный женский день" },
  { "date": "2026-03-22", "reason": "Наурыз" }
]
```

**Примечание:** управление настройками и выходными днями пока через Django Admin (`/admin/`). В будущем можно добавить CRUD-эндпоинты для CRM.

---

## 19. Турниры и мероприятия (планируется)

> **Статус: в разработке.** В бэкенде есть модель `Match` (геймификация: матчи 1v1 и 2v2, ELO рейтинг), но полноценного модуля турниров ещё нет.

**Существующие эндпоинты (матчи):**

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/gamification/matches/` | Auth | Список матчей |
| POST | `/api/gamification/matches/create/` | Тренер | Создать матч + пересчёт ELO |
| GET | `/api/gamification/leaderboard/` | Публичный | Таблица лидеров |

**Планируемое (по ТЗ):** создание турниров, управление участниками, сетка матчей, результаты, анонсы в приложении.

---

## 20. Аналитика и отчетность (планируется)

> **Статус: частично реализовано.** Дашборды (разделы 5.1 и 5.2) покрывают базовые KPI. Расширенная аналитика планируется.

**Реализовано:**
- KPI: выручка (день/неделя/месяц/всего), загрузка кортов, кол-во броней, новые клиенты
- Структура выручки по типам транзакций
- Статистика воронки лидов (конверсия, кол-во по стадиям)
- Финансовая сводка по периодам

**Планируемое (по ТЗ):**
- Графики: посещаемость по дням недели, загрузка по часам, сезонность
- Экспорт отчётов (CSV/Excel/PDF)
- Автоматическая еженедельная отчётность (OpenAI API + Telegram-бот)
- Конверсия лидов → клиентов (расширенная)
- Средний чек, LTV клиента

---

## 21. Управление пользователями CRM

Создание сотрудников CRM (RECEPTIONIST, SALES_MANAGER, ADMIN) — через Django Admin (`/admin/`).

**Для создания CRM-пользователя:**
1. Зайти в `/admin/` под суперпользователем
2. Users → Add User
3. Указать: username, password, role = `RECEPTIONIST` / `SALES_MANAGER` / `ADMIN`
4. Указать first_name, last_name

**Планируемое:** CRUD-эндпоинты для управления сотрудниками прямо из CRM.

---

## 22. Справочники для форм

Эндпоинты для заполнения select/dropdown при создании брони, выдаче абонемента и т.д.

| Метод | URL | Auth | Назначение |
|-------|-----|------|------------|
| GET | `/api/courts/` | нет | Активные корты |
| GET | `/api/auth/coaches/` | нет | Тренеры |
| GET | `/api/inventory/services/` | нет | Активные услуги |
| GET | `/api/memberships/types/` | нет | Типы абонементов |
| GET | `/api/auth/clients/?role=ADMIN` | да | Сотрудники (для выбора менеджера) |
| GET | `/api/core/settings/` | нет | Настройки клуба (рабочие часы) |
| GET | `/api/core/closed-days/` | нет | Выходные дни |

---

## 23. Обработка ошибок

| Код | Описание | Действие фронтенда |
|-----|----------|-------------------|
| **401** | Не авторизован / токен истёк | Попробовать refresh → если 401, перенаправить на логин |
| **403** | Нет прав | Показать «Недостаточно прав» / спрятать элемент |
| **404** | Ресурс не найден | Показать «Не найдено» |
| **400** | Ошибка валидации | Показать ошибки полей: `{ "field": ["сообщение"] }` |
| **429** | Превышен лимит запросов | Показать «Слишком много запросов, подождите» |
| **500** | Ошибка сервера | Показать «Ошибка сервера» |

Формат тела ошибки: `{ "field_name": ["сообщение"] }` или `{ "detail": "сообщение" }` или `{ "error": "сообщение" }`.

---

## 24. Рекомендации для React

### Авторизация и токены
- После `POST /api/auth/crm/login/` сохранять `access` и `refresh` (например, в памяти + localStorage)
- Для каждого запроса добавлять `Authorization: Bearer ${accessToken}`
- При 401 → автоматически вызвать `/api/auth/jwt/refresh/` → повторить запрос с новым access
- При неудачном refresh → перенаправить на логин

### Конфигурация
- Base URL: `process.env.REACT_APP_API_URL` или константа, по умолчанию `http://213.155.23.227/api`
- Все даты в формах (`datetime-local`) → преобразовывать в ISO 8601 перед отправкой

### Роутинг по ролям
- После логина сохранить `role` → показывать только разрешённые разделы (матрица в разделе 2.2)
- При попытке открыть запрещённый маршрут → redirect на главную

### Работа с ID
- Пользователь **никогда не вводит ID руками** — все ID берутся из выбора в интерфейсе
- Клиент → из списка/поиска (таблица, автокомплит)
- Бронь → из расписания/списка (клик по строке)
- Корт/тренер/услуга → из select (подгружается из справочников)
- Менеджер → из select (подгружается из `/api/auth/clients/?role=...`)

### UX рекомендации
- Для канбан-доски лидов: React DnD или @hello-pangea/dnd
- Для расписания: react-big-calendar или кастомная сетка
- Для таблиц: TanStack Table / AG Grid
- Для графиков (будущее): Recharts / Chart.js

---

## 25. Сводная таблица всех эндпоинтов

### Авторизация

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| POST | `/api/auth/crm/login/` | — | Вход в CRM |
| POST | `/api/auth/jwt/refresh/` | — | Обновить токен |
| POST | `/api/auth/jwt/verify/` | — | Проверить токен |

### Дашборды

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/analytics/reception/` | Ресепшн, Админ | Дашборд ресепшн |
| GET | `/api/analytics/dashboard/` | Только Админ | Дашборд директора |

### Клиенты

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/auth/clients/?search=&role=` | Все CRM | Список клиентов |
| GET | `/api/auth/reception/search/?phone=` | Ресепшн, Админ | Поиск по телефону |
| GET | `/api/auth/reception/user/{id}/` | Ресепшн, Админ | Карточка клиента |
| POST | `/api/auth/reception/user/{id}/action/` | Ресепшн, Админ | Действия (QR, данные, статус) |

### Лиды / Воронка продаж

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/leads/kanban/` | Все CRM | Канбан-доска |
| GET | `/api/leads/stats/` | Все CRM | Статистика воронки |
| GET/POST | `/api/leads/` | Все CRM | Список / создать |
| GET/PATCH/DELETE | `/api/leads/{id}/` | Все CRM | Детали / ред. / удалить |
| POST | `/api/leads/{id}/move/` | Все CRM | Смена стадии (drag & drop) |
| GET/POST | `/api/leads/{id}/comments/` | Все CRM | Комментарии |
| DELETE | `/api/leads/{id}/comments/{cid}/` | Все CRM | Удалить комментарий |
| GET/POST | `/api/leads/{id}/tasks/` | Все CRM | Задачи |
| PATCH/DELETE | `/api/leads/{id}/tasks/{tid}/` | Все CRM | Обновить / удалить задачу |

### Бронирования

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/bookings/manager/schedule/?date=` | Ресепшн, Админ | Расписание |
| GET | `/api/bookings/all/?date=&status=&court_id=&client_id=` | Ресепшн, Админ | Все брони |
| POST | `/api/bookings/reception/create/` | Ресепшн, Админ | Создать бронь |
| POST | `/api/bookings/{id}/confirm-payment/` | Ресепшн, Админ | Подтвердить оплату |

### Абонементы

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| POST | `/api/memberships/reception/buy/` | Ресепшн, Админ | Выдать абонемент |
| GET | `/api/memberships/all/?client_id=&is_active=` | Ресепшн, Админ | Все абонементы |
| GET | `/api/memberships/types/` | — | Типы (для форм) |
| GET/POST | `/api/memberships/types/manage/` | Ресепшн, Админ | Типы CRUD |
| GET/PATCH/DELETE | `/api/memberships/types/manage/{id}/` | Ресепшн, Админ | Тип по ID |

### Финансы

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/finance/transactions/?date=&type=&method=&user_id=` | Ресепшн, Админ | Транзакции |
| GET | `/api/finance/summary/?period=` | Ресепшн, Админ | Сводка |

### QR-сканер

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| POST | `/api/gym/qr/scan/` | Ресепшн, Админ | Сканировать QR |

### Управление (только ADMIN)

| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | `/api/courts/manage/` | Корты |
| GET/PATCH/DELETE | `/api/courts/manage/{id}/` | Корт по ID |
| GET/POST | `/api/inventory/services/manage/` | Услуги |
| GET/PATCH/DELETE | `/api/inventory/services/manage/{id}/` | Услуга по ID |
| GET/POST | `/api/marketing/manage/` | Акции |
| GET/PATCH/DELETE | `/api/marketing/manage/{id}/` | Акция по ID |
| GET/POST | `/api/news/manage/` | Новости |
| GET/PATCH/DELETE | `/api/news/manage/{id}/` | Новость по ID |

### Уведомления

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/notifications/` | Auth | Список уведомлений |
| GET | `/api/notifications/unread-count/` | Auth | Непрочитанные |
| POST | `/api/notifications/{id}/mark-read/` | Auth | Отметить прочитанным |
| POST | `/api/notifications/mark-all-read/` | Auth | Прочитать все |
| DELETE | `/api/notifications/{id}/` | Auth | Удалить |

### Справочники

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/courts/` | Активные корты |
| GET | `/api/auth/coaches/` | Тренеры |
| GET | `/api/inventory/services/` | Активные услуги |
| GET | `/api/memberships/types/` | Типы абонементов |
| GET | `/api/core/settings/` | Настройки клуба |
| GET | `/api/core/closed-days/` | Выходные дни |

### Матчи / Геймификация

| Метод | URL | Доступ | Описание |
|-------|-----|--------|----------|
| GET | `/api/gamification/matches/` | Auth | Список матчей |
| POST | `/api/gamification/matches/create/` | Тренер | Создать матч |
| GET | `/api/gamification/leaderboard/` | — | Лидерборд ELO |
