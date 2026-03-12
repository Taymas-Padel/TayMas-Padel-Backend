# Padel Club — API Documentation for Flutter Mobile App

**Base URL:** `http://213.155.23.227/api`  
**Swagger UI:** `http://213.155.23.227/swagger/`

Документ описывает **всю логику API для мобильного приложения**: общие эндпоинты для **клиентов** и отдельно — эндпоинты и сценарии для **приложения тренеров** (вход тот же по SMS, роль `COACH_PADEL` / `COACH_FITNESS`). Итоговый чеклист по тренерам и что в бэкенде не реализовано — в **`docs/TRAINER_APP_STATUS.md`**.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [User Profile & Settings](#2-user-profile--settings)
3. [Home Dashboard](#3-home-dashboard)
4. [Courts](#4-courts)
5. [Bookings](#5-bookings)
6. [Memberships](#6-memberships)
7. [Lobby (Partner Search)](#7-lobby-partner-search)
8. [Gamification (Matches & Leaderboard)](#8-gamification)
9. [Friends](#9-friends)
10. [Notifications](#10-notifications)
11. [News](#11-news)
12. [Marketing & Promo Codes](#12-marketing--promo-codes)
13. [Services / Inventory](#13-services--inventory)
14. [Gym](#14-gym)
15. [Finance (Transaction History)](#15-finance)
16. [Payments](#16-payments)
17. [Club Settings](#17-club-settings)
18. [Error Handling](#18-error-handling)
19. [Flutter Integration Tips](#19-flutter-integration-tips)
20. [Client app vs Trainer app](#20-client-app-vs-trainer-app)

---

## General Info

### Authorization

All authenticated endpoints require the header:

```
Authorization: Bearer <access_token>
```

### Token Lifetime

| Token   | Lifetime |
|---------|----------|
| Access  | 1 day    |
| Refresh | 90 days  |

When access token expires, use the refresh endpoint to get a new one without re-login.

### Date/Time Format

All datetime fields use **ISO 8601**: `2026-03-15T14:00:00Z`

### Pagination

List endpoints return arrays directly (no pagination wrapper by default).

### Errors

All errors return JSON:
```json
{
  "detail": "Error message"
}
```
or field-specific:
```json
{
  "field_name": ["Error message"]
}
```

---

## 1. Authentication

### 1.1 Send SMS Code

Sends a 6-digit verification code to the phone number.

```
POST /api/auth/mobile/send-code/
```

**Auth:** None

**Body:**
```json
{
  "phone_number": "+77001234567"
}
```

**Response 200:**
```json
{
  "message": "Код отправлен",
  "phone": "+77001234567"
}
```

**Response 429** (throttled — max 3 requests/min):
```json
{
  "error": "Слишком много попыток. Попробуйте через 10 минут."
}
```

**Notes:**
- Phone format: `+7XXXXXXXXXX` (Kazakhstan) or any valid international format
- Throttle: 3 SMS per minute per IP

---

### 1.2 Verify Code & Login

Verifies the SMS code and returns JWT tokens. Auto-creates user if first login.

```
POST /api/auth/mobile/login/
```

**Auth:** None

**Body:**
```json
{
  "phone_number": "+77001234567",
  "code": "123456",
  "device_id": "unique-device-uuid"
}
```

**Response 200:**
```json
{
  "refresh": "eyJ...",
  "access": "eyJ...",
  "is_new_user": true,
  "is_profile_complete": false,
  "role": "CLIENT",
  "user_id": 42,
  "is_qr_blocked": false
}
```

**Fields explained:**
- `is_new_user` — `true` if account was just created (show onboarding)
- `is_profile_complete` — `false` if first_name or last_name is empty (prompt to fill profile)
- `is_qr_blocked` — `true` if device changed (QR entry disabled until reception unblocks)
- `role` — `CLIENT` | `COACH_PADEL` | `COACH_FITNESS`

**Errors:**
- `400` — "Неверный код" or "Код истёк"
- `403` — "Для вашей роли используйте CRM" (admin/receptionist can't login via SMS)
- `429` — "Слишком много неудачных попыток"

---

### 1.3 Refresh Token

```
POST /api/auth/jwt/refresh/
```

**Auth:** None

**Body:**
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

**Note:** Old refresh token is blacklisted after rotation. Store the NEW refresh token.

---

### 1.4 Get Current User Profile

```
GET /api/auth/users/me/
```

**Auth:** Required

**Response 200:**
```json
{
  "id": 42,
  "email": "",
  "username": "+77001234567",
  "first_name": "Азамат",
  "last_name": "Есимханулы",
  "role": "CLIENT",
  "phone_number": "+77001234567",
  "rating_elo": 1200,
  "avatar": "http://213.155.23.227/media/avatars/photo.jpg",
  "price_per_hour": "0.00",
  "is_qr_blocked": false,
  "is_profile_complete": true
}
```

---

### 1.5 Update Profile

```
PATCH /api/auth/users/me/
```

**Auth:** Required

**Body (JSON or multipart/form-data for avatar):**
```json
{
  "first_name": "Азамат",
  "last_name": "Есимханулы",
  "avatar": "<file>"
}
```

**Rules:**
- `first_name` and `last_name` can only be set once. After that, changes are blocked ("Изменение имени запрещено. Обратитесь к администратору.")
- `avatar` — upload as `multipart/form-data`
- Fields `phone_number`, `role`, `rating_elo`, `email` are **read-only**

**Response 200:** Returns updated user object (same structure as GET).

---

### 1.6 Save FCM Token (Push Notifications)

Call this after login to enable push notifications.

```
POST /api/auth/me/fcm/
```

**Auth:** Required

**Body:**
```json
{
  "fcm_token": "fMCtoken123..."
}
```

To clear: `{ "fcm_token": null }`

**Response 200:**
```json
{
  "status": "ok",
  "fcm_token_saved": true
}
```

---

### 1.7 Delete Account

```
DELETE /api/auth/me/delete/
```

**Auth:** Required

**Body:**
```json
{
  "confirm": true
}
```

**Response 204:** Account deleted.

---

## 2. User Profile & Settings

### 2.1 My Statistics

```
GET /api/auth/me/stats/
```

**Auth:** Required

**Response 200:**
```json
{
  "user": {
    "id": 42,
    "full_name": "Азамат Есимханулы",
    "phone": "+77001234567",
    "role": "CLIENT",
    "rating_elo": 1200,
    "avatar": "http://.../photo.jpg",
    "is_profile_complete": true
  },
  "stats": {
    "total_bookings": 15,
    "completed_bookings": 12,
    "total_hours_on_court": 18.5,
    "matches_played": 8,
    "matches_won": 5,
    "gym_visits": 3
  },
  "active_membership": {
    "id": 1,
    "name": "Padel Unlimited",
    "type": "PADEL",
    "end_date": "15.06.2026",
    "hours_remaining": 20.0,
    "visits_remaining": null,
    "is_frozen": false
  },
  "upcoming_bookings": [
    {
      "id": 101,
      "court": "Корт 1",
      "start_time": "28.03.2026 14:00",
      "end_time": "15:30",
      "status": "CONFIRMED",
      "coach": "Алексей"
    }
  ]
}
```

---

### 2.2 My League / Rank

```
GET /api/auth/me/league/
```

**Auth:** Required

**Response 200:**
```json
{
  "rating_elo": 1200,
  "current_league": {
    "name": "Серебро",
    "min_elo": 1200,
    "max_elo": 1399,
    "color": "#9e9e9e"
  },
  "next_league": {
    "name": "Золото",
    "min_elo": 1400,
    "max_elo": 1599
  },
  "progress_to_next": 0,
  "elo_needed": 200
}
```

**League tiers:**

| League  | ELO Range   | Color     |
|---------|-------------|-----------|
| Новичок | 0–999       | `#78909c` |
| Бронза  | 1000–1199   | `#cd7f32` |
| Серебро | 1200–1399   | `#9e9e9e` |
| Золото  | 1400–1599   | `#ffd700` |
| Платина | 1600–1799   | `#00bcd4` |
| Элита   | 1800+       | `#e91e63` |

---

### 2.3 Public User Profile

View another user's profile (for friends, lobby participants, etc).

```
GET /api/auth/users/{id}/profile/
```

**Auth:** Required

**Response 200:**
```json
{
  "id": 15,
  "username": "+77009876543",
  "first_name": "Данияр",
  "last_name": "Сабит",
  "avatar": null,
  "rating_elo": 1350,
  "league": { "name": "Серебро", "color": "#9e9e9e" },
  "matches_played": 12,
  "matches_won": 7,
  "joint_matches": [
    {
      "id": 5,
      "date": "15.02.2026",
      "score": "6:4",
      "winner_team": "A",
      "same_team": true
    }
  ]
}
```

---

### 2.4 Search Users

```
GET /api/auth/search/?search=Азамат
```

**Auth:** Required

**Response 200:**
```json
[
  {
    "id": 15,
    "username": "+77009876543",
    "first_name": "Азамат",
    "last_name": "К.",
    "avatar": null
  }
]
```

Searches by: username, first_name, last_name, phone_number. Returns max 20 results.

---

### 2.5 List Coaches

```
GET /api/auth/coaches/
```

**Auth:** None (public)

**Response 200:**
```json
[
  {
    "id": 3,
    "full_name": "Алексей Тренер",
    "role": "COACH_PADEL",
    "coach_price": "5000.00",
    "phone_number": "+77001111111",
    "avatar": null
  }
]
```

---

## 3. Home Dashboard

The main screen of the mobile app. Returns all data for the home page in one request.

```
GET /api/auth/home/
```

**Auth:** Required

**Response 200:**
```json
{
  "greeting": "Привет, Азамат!",
  "user": {
    "id": 42,
    "full_name": "Азамат Есимханулы",
    "phone": "+77001234567",
    "rating_elo": 1200,
    "league": {
      "name": "Серебро",
      "min_elo": 1200,
      "max_elo": 1399,
      "color": "#9e9e9e"
    },
    "avatar": null,
    "is_profile_complete": true
  },
  "next_booking": {
    "id": 101,
    "court": "Корт 1",
    "date": "28.03.2026",
    "start_time": "14:00",
    "end_time": "15:30",
    "status": "CONFIRMED"
  },
  "active_membership": {
    "name": "Padel Pro",
    "type": "PADEL",
    "end_date": "15.06.2026",
    "days_left": 79,
    "hours_remaining": 20.0,
    "visits_remaining": null,
    "is_frozen": false
  },
  "promotions": [
    {
      "id": 1,
      "title": "Скидка 20%",
      "description": "На утренние часы",
      "image_url": "https://...",
      "promo_code": "MORNING20"
    }
  ],
  "news": [
    {
      "id": 5,
      "title": "Новый корт открыт!",
      "preview": "Мы рады сообщить...",
      "category": "CLUB",
      "image_url": "https://...",
      "created_at": "20.03.2026"
    }
  ]
}
```

---

## 4. Courts

### 4.1 List Courts

```
GET /api/courts/
```

**Auth:** None (public)

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Panoramic 1",
    "court_type": "PANORAMIC",
    "play_format": "TWO_VS_TWO",
    "description": "Панорамный корт для игры 2x2",
    "price_per_hour": "18000.00",
    "price_slots": [
      { "id": 1, "start_time": "06:00:00", "end_time": "08:00:00", "price_per_hour": "10000.00" },
      { "id": 2, "start_time": "08:00:00", "end_time": "00:00:00", "price_per_hour": "18000.00" }
    ],
    "image": "http://.../court1.jpg",
    "gallery": [
      { "id": 1, "image": "http://.../gallery1.jpg" }
    ],
    "is_active": true
  },
  {
    "id": 9,
    "name": "Single 1",
    "court_type": "INDOOR",
    "play_format": "ONE_VS_ONE",
    "description": "Тренировочный корт 1x1",
    "price_per_hour": "16000.00",
    "price_slots": [
      { "id": 3, "start_time": "06:00:00", "end_time": "00:00:00", "price_per_hour": "16000.00" }
    ],
    "image": null,
    "gallery": [],
    "is_active": true
  }
]
```

#### Поля корта

| Поле | Тип | Описание |
|------|-----|----------|
| `play_format` | string | `TWO_VS_TWO` — формат 2x2 (Panoramic корты, до 4 игроков) / `ONE_VS_ONE` — формат 1x1 (Single корт, до 2 игроков) |
| `price_per_hour` | string | Базовая цена/час (резерв, если `price_slots` пустой) |
| `price_slots` | array | Временные ценовые слоты. `end_time: "00:00:00"` означает полночь (конец суток) |

#### Значения `play_format`

| Значение | Описание | Макс. игроков |
|----------|----------|---------------|
| `TWO_VS_TWO` | Panoramic корты (2x2) | 4 (1 хозяин + 3 друга) |
| `ONE_VS_ONE` | Single корт (1x1) | 2 (1 хозяин + 1 друг) |

#### Логика price_slots

`price_slots` — массив временных слотов с ценой. Каждый слот:
- `start_time` — начало слота (HH:MM:SS)
- `end_time` — конец слота. **Важно:** `"00:00:00"` = полночь (конец суток)
- `price_per_hour` — цена за час в этом слоте

**Пример расчёта** для Panoramic корта, бронирование 07:00–09:00 (2 часа):
- 07:00–08:00 (слот 1): 1 час × 10 000 ₸ = 10 000 ₸
- 08:00–09:00 (слот 2): 1 час × 18 000 ₸ = 18 000 ₸
- **Итого: 28 000 ₸**

### 4.2 Court Detail

```
GET /api/courts/{id}/
```

Same response structure as list item.

---

## 5. Bookings

### 5.1 Check Availability (Free Slots)

```
GET /api/bookings/check-availability/?court_id=1&date=2026-03-28
```

**Auth:** None (public)

**Response 200:**
```json
{
  "court_id": 1,
  "date": "2026-03-28",
  "work_hours": "7:00 – 23:00",
  "is_holiday": false,
  "busy_slots": [
    { "start": "10:00", "end": "11:30", "booking_id": 55 },
    { "start": "14:00", "end": "15:00", "booking_id": 58 }
  ]
}
```

If holiday:
```json
{
  "court_id": 1,
  "date": "2026-01-01",
  "is_holiday": true,
  "reason": "Новогодний выходной",
  "busy_slots": []
}
```

---

### 5.2 Available Coaches for Time Slot

```
GET /api/bookings/available-coaches/?datetime=2026-03-28T14:00:00Z&duration=60
```

**Auth:** None

**Response 200:**
```json
[
  {
    "id": 3,
    "full_name": "Алексей Тренер",
    "role": "COACH_PADEL",
    "coach_price": "5000.00",
    "phone_number": "+77001111111",
    "avatar": null
  }
]
```

---

### 5.3 Price Preview (Before Booking)

Calculate the exact price considering **time-based pricing slots**, membership, coach, services.
Call this **before** creating a booking to show the user the total cost.

```
POST /api/bookings/price-preview/
```

**Auth:** Required

**Body:**
```json
{
  "court_id": 1,
  "start_time": "2026-03-28T07:00:00Z",
  "duration": 120,
  "coach_id": null,
  "service_ids": [],
  "friends_ids": [15, 22]
}
```

**Response 200:**
```json
{
  "total": 28000.0,
  "breakdown": {
    "court": 28000.0,
    "coach": 0.0,
    "services": 0.0,
    "prime_time_surcharge": 0.0
  },
  "membership_applied": false,
  "membership_name": null,
  "hours_remaining_after": null,
  "coach_covered_by_membership": false
}
```

> Здесь 28 000 ₸ = 07:00–08:00 (10 000) + 08:00–09:00 (18 000). Цена автоматически рассчитана по `price_slots` корта.

---

### 5.4 Create Booking

```
POST /api/bookings/create/
```

**Auth:** Required

**Body:**
```json
{
  "court": 1,
  "start_time": "2026-03-28T14:00:00Z",
  "duration": 60,
  "coach": 3,
  "promo_code": "MORNING20",
  "payment_method": "KASPI",
  "services": [
    { "service_id": 1, "quantity": 1 },
    { "service_id": 2, "quantity": 2 }
  ],
  "friends_ids": [15, 22]
}
```

**Field details:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `court` | int | Yes | Court ID |
| `start_time` | ISO datetime | Yes | Booking start (must be in the future, within work hours) |
| `duration` | int | Yes | Duration in minutes (30–240) |
| `coach` | int | No | Coach user ID |
| `promo_code` | string | No | Promotional code for discount |
| `payment_method` | string | No | `KASPI` (default), `CARD`, `CASH` |
| `services` | array | No | Extra services (racket rental etc.) |
| `friends_ids` | array[int] | No | Friend IDs to add as participants (see format rules below) |

**`friends_ids` rules by court play_format:**

| Court `play_format` | Max friends | Total players |
|---------------------|-------------|---------------|
| `TWO_VS_TWO` | 3 | 4 (хозяин + 3 друга) |
| `ONE_VS_ONE` | 1 | 2 (хозяин + 1 друг) |

> Если добавить больше друзей, чем разрешено форматом корта, вернётся ошибка 400.

**Response 201:**
```json
{
  "id": 101,
  "court": 1,
  "court_name": "Panoramic 1",
  "user": 42,
  "client_name": "Азамат Есимханулы",
  "start_time": "2026-03-28T07:00:00Z",
  "end_time": "2026-03-28T09:00:00Z",
  "duration_hours": 2.0,
  "price": "28000.00",
  "status": "PENDING",
  "is_paid": false,
  "coach": null,
  "coach_name": null,
  "services": [],
  "participants_names": ["daniyar"],
  "created_at": "2026-03-25T10:00:00Z"
}
```

> **Цена 28 000 ₸** = 07:00–08:00 (1ч × 10 000) + 08:00–09:00 (1ч × 18 000) — расчёт по ценовым слотам.

**Validation rules:**
- Cannot book in the past
- Cannot book on closed/holiday days
- Must be within club working hours (default 7:00–23:00)
- Court must be free for the requested slot
- Duration: min 30, max 240 minutes
- **`TWO_VS_TWO` court:** max 3 friends. **`ONE_VS_ONE` court:** max 1 friend
- If user has active PADEL membership with enough hours, court fee is covered automatically
- Price is calculated per time-price-slots (see court `price_slots`)

---

### 5.5 My Bookings (Upcoming)

```
GET /api/bookings/
```

**Auth:** Required

Returns upcoming bookings (not cancelled, `end_time >= now`), ordered by `start_time`.

---

### 5.6 Booking History

```
GET /api/bookings/history/
```

**Auth:** Required

Returns all bookings including past and cancelled, ordered by `-start_time`.

---

### 5.7 Booking Detail

```
GET /api/bookings/{id}/
```

**Auth:** Required (own bookings, participant, or **coach of this booking**)

**Note for trainer app:** A coach sees and can open detail for any booking where they are assigned (`coach`).

---

### 5.8 Cancel Booking

```
POST /api/bookings/{id}/cancel/
```

**Auth:** Required

**Response 200:**
```json
{
  "status": "Бронирование отменено."
}
```

**Rules:**
- Cannot cancel past bookings
- Must cancel at least 24 hours before start time (configurable via club settings)
- If booking was paid, a refund transaction is created automatically
- **Trainer:** the coach assigned to the booking can also cancel (same rules).

---

### 5.9 Confirm Booking (Client)

```
POST /api/bookings/{id}/client-confirm/
```

**Auth:** Required

Confirms a PENDING booking to CONFIRMED (useful when paying at reception).

**Response 200:**
```json
{
  "status": "Бронь подтверждена.",
  "booking_id": 101
}
```

---

### 5.10 Coach Schedule (Trainer app only)

**Для приложения тренеров:** расписание броней, в которых тренер назначен (кто забронировал, корт, время, участники). Используется для экрана «Моё расписание» у тренера.

```
GET /api/bookings/coach/schedule/?from=YYYY-MM-DD&to=YYYY-MM-DD
```

**Auth:** Required (role `COACH_PADEL` or `COACH_FITNESS`; `ADMIN` also allowed)

**Query params:**
| Param | Description |
|-------|-------------|
| `from` | Start date (default: today) |
| `to` | End date (default: from + 14 days) |

**Response 200:** Array of booking objects (same structure as Booking Detail). Key fields:
- `id`, `court`, `court_name`, `user`, `client_name`, `start_time`, `end_time`, `duration_hours`
- `coach`, `coach_name`, `participants_names`
- **`players_for_match`** — `[{id, name}, ...]` (client + participants) for pre-filling match creation
- `services`, `price`, `status`, `is_paid`, `created_at`

If user is not a coach, returns empty list.

---

### Booking Statuses

| Status | Description |
|--------|-------------|
| `PENDING` | Created, awaiting confirmation/payment |
| `CONFIRMED` | Confirmed (paid or will pay at reception) |
| `CANCELED` | Cancelled |
| `COMPLETED` | Past booking that was completed |

---

## 6. Memberships

### 6.1 List Membership Types (Store)

```
GET /api/memberships/types/
```

**Auth:** None (public)

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Padel Pro",
    "service_type": "PADEL",
    "total_hours": 30.0,
    "total_visits": null,
    "days_valid": 30,
    "price": "50000.00",
    "description": "30 часов падела за месяц",
    "is_active": true
  },
  {
    "id": 2,
    "name": "Gym Unlimited",
    "service_type": "GYM_UNLIMITED",
    "total_hours": 0,
    "total_visits": null,
    "days_valid": 30,
    "price": "25000.00",
    "description": "Безлимитный доступ в зал",
    "is_active": true
  }
]
```

**Service types:** `PADEL`, `GYM_UNLIMITED`, `GYM_PACK`

---

### 6.2 Buy Membership

```
POST /api/memberships/buy/{type_id}/
```

**Auth:** Required

**Response 201:**
```json
{
  "status": "Абонемент успешно куплен!"
}
```

---

### 6.3 My Memberships

```
GET /api/memberships/my/
```

**Auth:** Required

**Response 200:**
```json
[
  {
    "id": 5,
    "user": 42,
    "user_name": "Азамат Есимханулы",
    "membership_type_name": "Padel Pro",
    "type_name": "Padel Pro",
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-03-31T00:00:00Z",
    "hours_remaining": "20.00",
    "visits_remaining": null,
    "is_active": true,
    "is_frozen": false,
    "freeze_start_date": null,
    "created_at": "2026-03-01T10:00:00Z"
  }
]
```

---

### 6.4 Freeze Membership

```
POST /api/memberships/my/{id}/freeze/
```

**Auth:** Required

**Response 200:**
```json
{
  "status": "Абонемент заморожен. Срок действия приостановлен."
}
```

### 6.5 Unfreeze Membership

```
POST /api/memberships/my/{id}/unfreeze/
```

**Auth:** Required

**Response 200:**
```json
{
  "status": "Абонемент разморожен.",
  "new_end_date": "2026-04-15"
}
```

### 6.6 Membership Transaction History

```
GET /api/memberships/my/{id}/history/
```

**Auth:** Required

Returns transactions linked to this membership.

---

## 7. Lobby (Partner Search)

The lobby system allows players to find partners, negotiate time/court, split costs, and book together.

### Lobby Flow

```
1. CREATE lobby (set format, ELO range)
2. Other players JOIN (ELO check)
3. When full → status = NEGOTIATING
4. Players PROPOSE time/court
5. Players VOTE on proposals (auto-accept if all vote)
6. Creator can ACCEPT proposal → status = READY
7. Creator ASSIGNS TEAMS (A/B)
8. Creator creates BOOK → status = BOOKED
9. Each player adds MY-EXTRAS (optional services)
10. Each player PAY-SHARE → when all paid → CONFIRMED
```

### Lobby Statuses

| Status | Description |
|--------|-------------|
| `OPEN` | Looking for players (1 player) |
| `WAITING` | Partially filled (2-3 players for DOUBLE) |
| `NEGOTIATING` | All players joined, negotiating time/court |
| `READY` | Time/court agreed, waiting for teams & booking |
| `BOOKED` | Booking created, waiting for payments |
| `PAID` | All paid, booking confirmed |
| `CLOSED` | Cancelled/closed |

### Game Formats

| Format | Players |
|--------|---------|
| `SINGLE` | 2 (1v1) |
| `DOUBLE` | 4 (2v2) |

---

### 7.1 List Lobbies

```
GET /api/lobby/
```

**Auth:** None for GET (public), Required for POST

**Query params:**
| Param | Description |
|-------|-------------|
| `status` | Filter by status: `OPEN`, `WAITING`, `NEGOTIATING` etc. |
| `format` | Filter by format: `SINGLE` or `DOUBLE` |
| `elo` | Filter by ELO value (shows lobbies accepting this ELO) |

By default, if authenticated, filters lobbies matching user's ELO.

**Response 200:** Array of lobby objects (see 7.3 for structure).

---

### 7.2 Create Lobby

```
POST /api/lobby/
```

**Auth:** Required

**Body:**
```json
{
  "title": "Вечерняя игра",
  "game_format": "DOUBLE",
  "elo_min": 1000,
  "elo_max": 1400,
  "comment": "Ищу партнёров на вечер"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Lobby name (max 100 chars) |
| `game_format` | string | Yes | `SINGLE` or `DOUBLE` |
| `elo_min` | int | No | Min ELO (default: user_elo - 200) |
| `elo_max` | int | No | Max ELO (default: user_elo + 200) |
| `comment` | string | No | Additional info |

Creator is automatically added as first participant (Team A).

---

### 7.3 Lobby Detail

```
GET /api/lobby/{id}/
```

**Auth:** Required

**Response 200:**
```json
{
  "id": 10,
  "creator": 42,
  "creator_name": "Азамат Есимханулы",
  "title": "Вечерняя игра",
  "game_format": "DOUBLE",
  "elo_min": 1000,
  "elo_max": 1400,
  "elo_label": "1000–1400 ELO",
  "status": "NEGOTIATING",
  "court": null,
  "court_name": null,
  "court_price": null,
  "scheduled_time": null,
  "duration_minutes": 90,
  "comment": "Ищу партнёров",
  "players_count": 4,
  "max_players": 4,
  "estimated_share": null,
  "booking_id": null,
  "booking_status": null,
  "booking_price": null,
  "paid_count": 0,
  "participants": [
    {
      "id": 1,
      "user": 42,
      "user_name": "Азамат Есимханулы",
      "rating_elo": 1200,
      "team": "A",
      "court_share": "0.00",
      "membership_used": false,
      "extras": [],
      "extras_total": "0",
      "share_amount": null,
      "total_to_pay": "0",
      "is_paid": false,
      "joined_at": "2026-03-25T10:00:00Z"
    }
  ],
  "proposals": [],
  "created_at": "2026-03-25T10:00:00Z"
}
```

---

### 7.4 Join Lobby

```
POST /api/lobby/{id}/join/
```

**Auth:** Required

**Response 200:**
```json
{
  "status": "Вы вступили в лобби. Все собрались! Любой участник может предложить время и корт.",
  "lobby_status": "NEGOTIATING",
  "players_count": 4,
  "max_players": 4
}
```

**Errors:**
- `400` — ELO out of range, lobby full, already joined, or lobby closed

---

### 7.5 Leave Lobby

```
POST /api/lobby/{id}/leave/
```

**Auth:** Required

If creator leaves, lobby is closed.

---

### 7.6 My Lobbies

```
GET /api/lobby/my/
```

**Auth:** Required

Returns lobbies where user is a participant (excludes CLOSED).

---

### 7.7 Propose Time & Court

Available when status = `NEGOTIATING`.

```
POST /api/lobby/{id}/proposals/
```

**Auth:** Required (participant only)

**Body:**
```json
{
  "court": 1,
  "scheduled_time": "2026-03-28T18:00:00Z",
  "duration_minutes": 90
}
```

**Response 201:**
```json
{
  "id": 5,
  "lobby": 10,
  "proposed_by": 42,
  "proposed_by_name": "Азамат",
  "court": 1,
  "court_name": "Корт 1",
  "court_price": "5000.00",
  "scheduled_time": "2026-03-28T18:00:00Z",
  "duration_minutes": 90,
  "votes_count": 1,
  "i_voted": true,
  "is_accepted": false,
  "estimated_share": "1875.00",
  "created_at": "2026-03-25T10:00:00Z"
}
```

Proposer auto-votes "yes".

### 7.8 List Proposals

```
GET /api/lobby/{id}/proposals/
```

**Auth:** Required (participant only)

---

### 7.9 Vote on Proposal

```
POST /api/lobby/{id}/proposals/{proposal_id}/vote/
```

**Auth:** Required (participant only)

Toggle vote. If already voted, removes vote. If all players vote "yes", proposal is **auto-accepted** (lobby → READY).

**Response 200:**
```json
{
  "voted": true,
  "votes_count": 3,
  "max_players": 4,
  "auto_accepted": false,
  "lobby_status": "NEGOTIATING"
}
```

---

### 7.10 Accept Proposal (Creator Only)

```
POST /api/lobby/{id}/proposals/{proposal_id}/accept/
```

**Auth:** Required (creator only)

Creator can manually accept a proposal regardless of votes.

**Response 200:**
```json
{
  "status": "✅ Предложение принято! Назначьте команды и создайте бронь.",
  "court": "Корт 1",
  "scheduled_time": "2026-03-28T18:00:00Z",
  "duration_minutes": 90,
  "lobby_status": "READY"
}
```

---

### 7.11 Assign Teams (Creator Only)

```
POST /api/lobby/{id}/assign-teams/
```

**Auth:** Required (creator only)

**Body:**
```json
{
  "teams": {
    "42": "A",
    "15": "A",
    "22": "B",
    "33": "B"
  }
}
```

Keys are user IDs (as strings), values are `"A"` or `"B"`.

For SINGLE: 1 per team. For DOUBLE: 2 per team.

**Response 200:**
```json
{
  "status": "Команды назначены.",
  "team_a": ["42", "15"],
  "team_b": ["22", "33"]
}
```

---

### 7.12 Create Booking from Lobby (Creator Only)

```
POST /api/lobby/{id}/book/
```

**Auth:** Required (creator only)

Requires: status = READY, all teams assigned.

**Response 200:**
```json
{
  "status": "✅ Бронь создана!",
  "booking_id": 120,
  "booking_status": "PENDING",
  "court_total": "7500.00",
  "base_court_share": "1875.00",
  "players": [
    {
      "user_id": 42,
      "user_name": "Азамат",
      "team": "A",
      "court_share": "0.00",
      "membership_used": true,
      "is_paid": true
    },
    {
      "user_id": 15,
      "user_name": "Данияр",
      "team": "A",
      "court_share": "1875.00",
      "membership_used": false,
      "is_paid": false
    }
  ],
  "note": "Каждый участник добавляет личные услуги (/my-extras/) и оплачивает свою долю (/pay-share/)."
}
```

Membership holders get `court_share = 0` and `is_paid = true` automatically.

---

### 7.13 Add Personal Services (Each Player)

```
GET /api/lobby/{id}/my-extras/
```

Returns your current extras and share.

```
POST /api/lobby/{id}/my-extras/
```

**Body:**
```json
{
  "services": [
    { "service_id": 1, "quantity": 1 },
    { "service_id": 2, "quantity": 2 }
  ]
}
```

**Response 200:**
```json
{
  "status": "Услуги добавлены.",
  "added": [
    { "service_id": 1, "service_name": "Ракетка", "quantity": 1, "subtotal": "2000.00" }
  ],
  "extras_total": "2000.00",
  "court_share": "1875.00",
  "total_to_pay": "3875.00"
}
```

```
DELETE /api/lobby/{id}/my-extras/{extra_id}/
```

Removes a specific extra service.

---

### 7.14 Pay Your Share

```
POST /api/lobby/{id}/pay-share/
```

**Auth:** Required

**Body:**
```json
{
  "payment_method": "KASPI"
}
```

Options: `KASPI`, `CARD`, `CASH`

**Response 200:**
```json
{
  "status": "✅ Ваша доля оплачена!",
  "court_share": "1875.00",
  "membership_used": false,
  "extras_total": "2000.00",
  "total_paid": "3875.00",
  "payment_method": "KASPI",
  "all_paid": false,
  "booking_confirmed": false,
  "paid_count": 2,
  "total_count": 4
}
```

When all players pay → lobby status = `PAID`, booking status = `CONFIRMED`.

---

### 7.15 Payment Status (Overview)

```
GET /api/lobby/{id}/payment-status/
```

**Auth:** Required (participant or creator)

**Response 200:**
```json
{
  "lobby_id": 10,
  "lobby_status": "BOOKED",
  "booking_id": 120,
  "court_total": "7500.00",
  "paid_count": 2,
  "total_count": 4,
  "all_paid": false,
  "participants": [
    {
      "user_id": 42,
      "user_name": "Азамат",
      "team": "A",
      "court_share": "0.00",
      "membership_used": true,
      "extras_total": "0",
      "total_to_pay": "0",
      "extras": [],
      "is_paid": true,
      "paid_at": "2026-03-25T10:05:00Z"
    },
    {
      "user_id": 15,
      "user_name": "Данияр",
      "team": "A",
      "court_share": "1875.00",
      "membership_used": false,
      "extras_total": "2000.00",
      "total_to_pay": "3875.00",
      "extras": [
        { "service_name": "Ракетка", "quantity": 1, "subtotal": "2000.00" }
      ],
      "is_paid": false,
      "paid_at": null
    }
  ]
}
```

---

### 7.16 Close Lobby (Creator Only)

```
POST /api/lobby/{id}/close/
```

**Auth:** Required (creator only)

Cannot close if booking already created (status BOOKED or PAID).

---

## 8. Gamification

### 8.1 Create Match (Trainer / Admin only)

**Для приложения тренеров:** создание матча с указанием команд, счёта и победителя. ELO начисляется автоматически. Судья (`judge`) — текущий пользователь (тренер).

```
POST /api/gamification/matches/create/
```

**Auth:** Required — only `COACH_PADEL`, `COACH_FITNESS`, or `ADMIN`

**Body:**
```json
{
  "team_a": [42, 15],
  "team_b": [22, 33],
  "score": "6:4",
  "winner_team": "A",
  "court": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `team_a` | array[int] | Yes | User IDs — team A (1 or 2 players) |
| `team_b` | array[int] | Yes | User IDs — team B (1 or 2 players) |
| `score` | string | Yes | Game score, e.g. `"6:4"` or `"6:4, 6:3"` |
| `winner_team` | string | Yes | `"A"`, `"B"`, or `"DRAW"` |
| `court` | int | No | Court ID (can be null) |

**Rules:**
- No user can be in both `team_a` and `team_b`.
- `judge` is set automatically to the current user (the coach).
- After save, ELO is updated: winners +25, losers −25 (minimum 0). `elo_changes` stored on the match.

**Response 201:** Created match object (same structure as in Match History), including `elo_changes`.

**Errors:** `403` if not coach/admin; `400` if validation fails (e.g. same player in both teams).

---

### 8.2 Match History

```
GET /api/gamification/matches/
```

**Auth:** Required

Returns matches where the current user participated. **Trainer app:** add `?all=true` to get all matches (not only where the coach played); useful for "all matches I judged" or admin view.

**Response 200:**
```json
[
  {
    "id": 5,
    "team_a": [42, 15],
    "team_b": [22, 33],
    "score": "6:4",
    "winner_team": "A",
    "court": 1,
    "team_a_names": [
      { "id": 42, "name": "Азамат" },
      { "id": 15, "name": "Данияр" }
    ],
    "team_b_names": [
      { "id": 22, "name": "Серик" },
      { "id": 33, "name": "Мурат" }
    ],
    "judge_name": "Алексей Тренер",
    "date": "2026-03-20T18:00:00Z",
    "date_formatted": "20.03.2026 18:00",
    "is_rated": true,
    "elo_changes": { "42": 25, "15": 25, "22": -25, "33": -25 },
    "my_elo_change": 25
  }
]
```

---

### 8.3 Leaderboard

```
GET /api/gamification/leaderboard/?limit=50
```

**Auth:** None (public)

**Response 200:**
```json
[
  {
    "id": 42,
    "username": "+77001234567",
    "full_name": "Азамат Есимханулы",
    "avatar": null,
    "rating_elo": 1350,
    "matches_played": 15,
    "matches_won": 10
  }
]
```

Max limit: 100.

---

## 9. Friends

### 9.1 My Friends List

```
GET /api/friends/
```

**Auth:** Required

**Response 200:**
```json
[
  {
    "id": 15,
    "username": "+77009876543",
    "first_name": "Данияр",
    "last_name": "Сабит",
    "avatar": null
  }
]
```

---

### 9.2 Send Friend Request

```
POST /api/friends/send/
```

**Auth:** Required

**Body:**
```json
{
  "to_user_id": 15
}
```

**Response 201:**
```json
{
  "id": 8,
  "from_user": { "id": 42, "username": "+77001234567", "first_name": "Азамат", "last_name": "Е.", "avatar": null },
  "to_user": { "id": 15, "username": "+77009876543", "first_name": "Данияр", "last_name": "С.", "avatar": null },
  "status": "PENDING",
  "created_at": "2026-03-25T10:00:00Z"
}
```

**Errors:**
- "Нельзя добавить себя"
- "Заявка уже отправлена"
- "Вы уже друзья"

---

### 9.3 Incoming Requests

```
GET /api/friends/requests/
```

**Auth:** Required

Returns pending friend requests where you are `to_user`.

---

### 9.4 Outgoing Requests

```
GET /api/friends/requests/outgoing/
```

**Auth:** Required

Returns pending requests you sent.

---

### 9.5 Respond to Request

```
POST /api/friends/respond/
```

**Auth:** Required

**Body:**
```json
{
  "request_id": 8,
  "action": "accept"
}
```

Actions: `accept` | `reject`

---

### 9.6 Cancel Outgoing Request

```
POST /api/friends/cancel/
```

**Body:**
```json
{
  "request_id": 8
}
```

---

### 9.7 Remove Friend

```
POST /api/friends/remove/
```

**Body:**
```json
{
  "user_id": 15
}
```

---

### 9.8 Friends Activity Feed

```
GET /api/friends/feed/?limit=20
```

**Auth:** Required

**Response 200:**
```json
[
  {
    "type": "MATCH",
    "user_id": 15,
    "user_name": "Данияр Сабит",
    "description": "🏆 Победил матч 6:4 ELO: +25",
    "date": "2026-03-20T18:00:00Z",
    "data": {
      "match_id": 5,
      "score": "6:4",
      "won": true,
      "elo_change": 25
    }
  }
]
```

Shows friends' match results from the last 30 days.

---

## 10. Notifications

### 10.1 List Notifications

```
GET /api/notifications/
```

**Auth:** Required

**Query params:**
| Param | Description |
|-------|-------------|
| `unread` | `true` — only unread |
| `type` | Filter: `BOOKING`, `MEMBERSHIP`, `FRIEND`, `MATCH`, `LOBBY`, `PROMO`, `NEWS`, `PAYMENT`, `SYSTEM` |

**Response 200:**
```json
[
  {
    "id": 50,
    "notification_type": "LOBBY",
    "title": "🎾 Лобби «Вечерняя игра» заполнено!",
    "body": "Все игроки собрались. Предложите удобное время и корт для игры.",
    "is_read": false,
    "data": { "lobby_id": 10, "lobby_title": "Вечерняя игра" },
    "created_at": "2026-03-25T10:00:00Z"
  }
]
```

---

### 10.2 Unread Count (for Badge)

```
GET /api/notifications/unread-count/
```

**Auth:** Required

**Response 200:**
```json
{
  "unread_count": 3
}
```

---

### 10.3 Mark as Read

```
POST /api/notifications/{id}/read/
```

---

### 10.4 Mark All as Read

```
POST /api/notifications/read-all/
```

**Response 200:**
```json
{
  "marked_read": 5
}
```

---

### 10.5 Delete Notification

```
DELETE /api/notifications/{id}/
```

**Response 204:** No content.

---

## 11. News

### 11.1 List News

```
GET /api/news/
```

**Auth:** None (public)

**Query params:**
| Param | Description |
|-------|-------------|
| `category` | Filter: `CLUB`, `EVENT`, `TOURNAMENT`, etc. |

**Response 200:**
```json
[
  {
    "id": 5,
    "title": "Новый корт открыт!",
    "content": "Мы рады сообщить о запуске нового корта...",
    "category": "CLUB",
    "image_url": "https://...",
    "is_published": true,
    "created_at": "2026-03-20T12:00:00Z"
  }
]
```

### 11.2 News Detail

```
GET /api/news/{id}/
```

---

## 12. Marketing & Promo Codes

### 12.1 Active Promotions

```
GET /api/marketing/promos/
```

**Auth:** None (public)

**Response 200:**
```json
[
  {
    "id": 1,
    "title": "Утренняя скидка 20%",
    "description": "Скидка на бронирование с 7:00 до 12:00",
    "discount_type": "PERCENT",
    "discount_value": "20.00",
    "promo_code": "MORNING20",
    "start_date": "2026-03-01T00:00:00Z",
    "end_date": "2026-04-01T00:00:00Z",
    "image_url": "https://...",
    "is_active": true
  }
]
```

### 12.2 Validate Promo Code

```
GET /api/marketing/validate-promo/?code=MORNING20
```

**Auth:** None

**Response 200 (valid):**
```json
{
  "valid": true,
  "title": "Утренняя скидка 20%",
  "discount_type": "PERCENT",
  "discount_value": 20.0,
  "description": "Скидка на бронирование с 7:00 до 12:00"
}
```

**Response 200 (invalid):**
```json
{
  "valid": false,
  "error": "Промокод не найден или недействителен"
}
```

---

## 13. Services / Inventory

### 13.1 List Available Services

```
GET /api/inventory/services/
```

**Auth:** None (public)

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Аренда ракетки",
    "category": "RENTAL",
    "price": "2000.00",
    "description": "Профессиональная ракетка для падела",
    "is_active": true
  },
  {
    "id": 2,
    "name": "Мячи (3 шт)",
    "category": "CONSUMABLE",
    "price": "1500.00",
    "description": "Набор падел-мячей",
    "is_active": true
  }
]
```

Used when creating bookings (`services` field) and in lobby extras.

---

## 14. Gym

### 14.1 Generate QR Code for Entry

```
GET /api/gym/qr/generate/
```

**Auth:** Required

**Response 200:**
```json
{
  "qr_content": "signed-token-string:timestamp",
  "valid_seconds": 60,
  "message": "Покажите этот QR сканеру на входе"
}
```

Display this as a QR code. Valid for 60 seconds.

---

### 14.2 Gym Check-In

```
POST /api/gym/checkin/
```

**Auth:** Required

Checks gym membership status and records visit.

**Response 200 (with membership):**
```json
{
  "status": "ACCESS_GRANTED",
  "type": "SUBSCRIPTION",
  "message": "Вход по абонементу: Gym Unlimited",
  "valid_until": "31.03.2026"
}
```

**Response 200 (one-time payment):**
```json
{
  "status": "ONE_TIME_PAYMENT",
  "type": "ONE_TIME",
  "message": "Абонемент не найден. Оформлен разовый визит.",
  "price": 3000
}
```

---

### 14.3 My Gym Visits

```
GET /api/gym/visits/
```

**Auth:** Required

Returns visit history.

---

### 14.4 Personal Training

```
GET /api/gym/personal-training/
```

**Auth:** Required

Returns personal training sessions: **client** — own sessions; **coach** — sessions where they are the coach.

```
POST /api/gym/personal-training/
```

**Auth:** Required

Create a personal training session. **Client** sends `coach` (trainer user ID); **coach** can create for a client (body includes `client` and `coach`).

**Body (example):**
```json
{
  "client": 42,
  "coach": 3,
  "start_time": "2026-03-28T14:00:00Z",
  "price": "5000.00"
}
```

**Response 201:** Object with `id`, `client`, `client_name`, `coach`, `coach_name`, `start_time`, `price`, `is_paid`, `created_at`.

```
GET /api/gym/personal-training/{id}/
PATCH /api/gym/personal-training/{id}/
DELETE /api/gym/personal-training/{id}/
```

**Auth:** Required (client — own; coach — sessions where they are coach; admin — any).

---

## 15. Finance

### 15.1 My Transaction History

```
GET /api/finance/history/
```

**Auth:** Required

**Response 200:**
```json
[
  {
    "id": 20,
    "user": 42,
    "booking": 101,
    "amount": "5000.00",
    "transaction_type": "BOOKING",
    "payment_method": "KASPI",
    "description": "Оплата брони #101",
    "created_at": "2026-03-25T10:00:00Z"
  }
]
```

**Transaction types:** `BOOKING`, `MEMBERSHIP_PURCHASE`, `REFUND`, `OTHER`
**Payment methods:** `KASPI`, `CARD`, `CASH`, `UNKNOWN`

---

## 16. Payments

### 16.1 Payment Session Status

```
GET /api/payments/session/{session_id}/status/
```

**Auth:** Required

**Response 200:**
```json
{
  "session_id": "uuid-string",
  "status": "PENDING",
  "amount": "5000.00",
  "provider": "stub",
  "payment_url": null,
  "transaction_id": "TX12345",
  "created_at": "2026-03-25T10:00:00Z"
}
```

**Payment session statuses:** `PENDING`, `SUCCESS`, `FAILED`

---

## 17. Club Settings

### 17.1 Club Settings

```
GET /api/core/settings/
```

**Auth:** None (public)

**Response 200:**
```json
[
  { "key": "OPEN_TIME", "value": "07:00", "description": "Время открытия" },
  { "key": "CLOSE_TIME", "value": "23:00", "description": "Время закрытия" },
  { "key": "CANCELLATION_HOURS", "value": "24", "description": "За сколько часов можно отменить бронь" }
]
```

### 17.2 Closed Days (Holidays)

```
GET /api/core/closed-days/?from=2026-03-01&to=2026-12-31
```

**Auth:** None (public)

**Response 200:**
```json
[
  {
    "date": "2026-03-08",
    "reason": "Международный женский день"
  },
  {
    "date": "2026-03-22",
    "reason": "Наурыз"
  }
]
```

Without params: returns from today to +1 year.

---

## 18. Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | Deleted (no content) |
| `400` | Validation error (check field errors) |
| `401` | Unauthorized (token expired or missing) |
| `403` | Forbidden (wrong role or blocked) |
| `404` | Not found |
| `429` | Too many requests (throttled) |

### Token Expiry Handling

When you get `401`, try refreshing the token:

```
POST /api/auth/jwt/refresh/
Body: { "refresh": "<saved_refresh_token>" }
```

If refresh also fails with `401` — redirect to login screen.

---

## 19. Flutter Integration Tips

### Recommended Dart Packages

```yaml
dependencies:
  dio: ^5.0.0          # HTTP client with interceptors
  flutter_secure_storage: ^9.0.0  # Store tokens securely
  json_annotation: ^4.8.0
  json_serializable: ^6.7.0
```

### Auth Interceptor Pattern

```dart
class AuthInterceptor extends Interceptor {
  final FlutterSecureStorage _storage;

  AuthInterceptor(this._storage);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _storage.read(key: 'access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken != null) {
        try {
          final response = await Dio().post(
            '${AppConfig.baseUrl}/api/auth/jwt/refresh/',
            data: {'refresh': refreshToken},
          );
          final newAccess = response.data['access'];
          final newRefresh = response.data['refresh'];
          await _storage.write(key: 'access_token', value: newAccess);
          await _storage.write(key: 'refresh_token', value: newRefresh);

          // Retry the failed request
          err.requestOptions.headers['Authorization'] = 'Bearer $newAccess';
          final retryResponse = await Dio().fetch(err.requestOptions);
          return handler.resolve(retryResponse);
        } catch (_) {
          // Refresh failed — go to login
        }
      }
    }
    handler.next(err);
  }
}
```

### Login Flow

```dart
// Step 1: Send SMS code
await dio.post('/api/auth/mobile/send-code/', data: {
  'phone_number': '+77001234567',
});

// Step 2: Verify code and get tokens
final response = await dio.post('/api/auth/mobile/login/', data: {
  'phone_number': '+77001234567',
  'code': '123456',
  'device_id': await getDeviceId(), // unique per device
});

final accessToken = response.data['access'];
final refreshToken = response.data['refresh'];
final isNewUser = response.data['is_new_user'];
final isProfileComplete = response.data['is_profile_complete'];

// Store tokens securely
await storage.write(key: 'access_token', value: accessToken);
await storage.write(key: 'refresh_token', value: refreshToken);

// Step 3: Save FCM token for push notifications
await dio.post('/api/auth/me/fcm/', data: {
  'fcm_token': await FirebaseMessaging.instance.getToken(),
});

// Step 4: Navigate — check role for Client vs Trainer app
final role = response.data['role']; // CLIENT | COACH_PADEL | COACH_FITNESS
final isCoach = role == 'COACH_PADEL' || role == 'COACH_FITNESS';
if (isNewUser || !isProfileComplete) {
  // Go to profile setup screen
} else if (isCoach) {
  // Go to trainer home (e.g. coach schedule tab)
} else {
  // Go to client home screen
}
```

### Home Screen Data Loading

```dart
// Single request for the entire home screen
final response = await dio.get('/api/auth/home/');
final data = response.data;

// data['greeting']          — "Привет, Азамат!"
// data['user']              — user info with league
// data['next_booking']      — nearest booking or null
// data['active_membership'] — active membership or null
// data['promotions']        — top 3 promotions
// data['news']              — top 5 news items
```

### Booking Flow

```dart
// 1. Show available courts
final courts = await dio.get('/api/courts/');

// 2. Check availability for selected court and date
final slots = await dio.get('/api/bookings/check-availability/', queryParameters: {
  'court_id': 1,
  'date': '2026-03-28',
});
// slots.data['busy_slots'] — occupied time ranges
// slots.data['work_hours'] — "7:00 – 23:00"

// 3. Show available coaches (optional)
final coaches = await dio.get('/api/bookings/available-coaches/', queryParameters: {
  'datetime': '2026-03-28T14:00:00Z',
  'duration': 60,
});

// 4. Preview price (with membership check)
final preview = await dio.post('/api/bookings/price-preview/', data: {
  'court_id': 1,
  'start_time': '2026-03-28T14:00:00Z',
  'duration': 60,
  'coach_id': 3,  // optional
});
// preview.data['total'] — final price
// preview.data['membership_applied'] — true if membership covers court

// 5. Create booking
final booking = await dio.post('/api/bookings/create/', data: {
  'court': 1,
  'start_time': '2026-03-28T14:00:00Z',
  'duration': 60,
  'coach': 3,
  'promo_code': 'MORNING20',
});
```

### Lobby Flow

```dart
// 1. Browse open lobbies
final lobbies = await dio.get('/api/lobby/', queryParameters: {'status': 'OPEN'});

// 2. Create lobby (or join existing)
final lobby = await dio.post('/api/lobby/', data: {
  'title': 'Вечерняя игра',
  'game_format': 'DOUBLE',
});

// 3. Join a lobby
await dio.post('/api/lobby/10/join/');

// 4. When NEGOTIATING — propose time
await dio.post('/api/lobby/10/proposals/', data: {
  'court': 1,
  'scheduled_time': '2026-03-28T18:00:00Z',
  'duration_minutes': 90,
});

// 5. Vote on proposals
await dio.post('/api/lobby/10/proposals/5/vote/');

// 6. Creator assigns teams
await dio.post('/api/lobby/10/assign-teams/', data: {
  'teams': {'42': 'A', '15': 'A', '22': 'B', '33': 'B'},
});

// 7. Creator creates booking
await dio.post('/api/lobby/10/book/');

// 8. Each player adds extras (optional)
await dio.post('/api/lobby/10/my-extras/', data: {
  'services': [{'service_id': 1, 'quantity': 1}],
});

// 9. Each player pays
await dio.post('/api/lobby/10/pay-share/', data: {
  'payment_method': 'KASPI',
});

// 10. Check payment status
final status = await dio.get('/api/lobby/10/payment-status/');
```

### Trainer app: schedule and create match

```dart
// Coach schedule (my bookings as coach)
final schedule = await dio.get(
  '/api/bookings/coach/schedule/',
  queryParameters: {
    'from': '2026-03-01',
    'to': '2026-03-31',
  },
);
// schedule.data — list of bookings with client_name, players_for_match, etc.

// Create match (trainer only)
final match = await dio.post('/api/gamification/matches/create/', data: {
  'team_a': [42, 15],
  'team_b': [22, 33],
  'score': '6:4',
  'winner_team': 'A',
  'court': 1,
});
// ELO is updated automatically; match.data contains elo_changes.

// All matches (for coach: not only where he played, but all)
final allMatches = await dio.get('/api/gamification/matches/?all=true');
```

### Notification Badge

```dart
// Poll for unread count (e.g., every 30 seconds or on app focus)
final count = await dio.get('/api/notifications/unread-count/');
// count.data['unread_count'] — show as badge number
```

---

## 20. Client app vs Trainer app

Один бэкенд и один вход по SMS. Роль приходит в ответе логина: `CLIENT`, `COACH_PADEL`, `COACH_FITNESS`. По `role` показываем разный UI и разрешаем разные действия.

### 20.1 Кто что использует

| Функция | Клиент | Тренер (COACH_PADEL / COACH_FITNESS) |
|--------|--------|--------------------------------------|
| Вход | SMS `mobile/login` | То же (role в ответе) |
| Профиль, лига, статистика | ✅ | ✅ |
| Home dashboard | ✅ | ✅ (можно скрыть или упростить) |
| Корты, брони: мои / создать / отмена | ✅ | ✅ (свои как клиент) |
| **Расписание «где я тренер»** | — | ✅ `GET /api/bookings/coach/schedule/` |
| **Детали брони / отмена как тренер** | — | ✅ те же эндпоинты (доступ к брони, где он coach) |
| **Создать матч (счёт игры, ELO)** | — | ✅ `POST /api/gamification/matches/create/` |
| Матчи: история | ✅ свои | ✅ свои; с `?all=true` — все матчи |
| Лидерборд | ✅ | ✅ |
| Друзья, лобби, уведомления, новости, акции | ✅ | ✅ (по желанию) |
| Абонементы (покупка, мои, заморозка) | ✅ | ✅ |
| Услуги (список для брони/лобби) | ✅ | ✅ |
| Зал: QR, check-in, визиты | ✅ | ✅ |
| **Персональные тренировки** | ✅ свои | ✅ свои как coach (список, создание, PATCH/DELETE) |
| Финансы (история транзакций) | ✅ | ✅ |
| Платежи (статус сессии) | ✅ | ✅ |
| Настройки клуба, закрытые дни | ✅ | ✅ |

### 20.2 Тренер: обязательные экраны и логика

- **Вход** — тот же `POST /api/auth/mobile/login/`. После входа проверять `role`: если `COACH_PADEL` или `COACH_FITNESS`, показывать версию «для тренера» (или дополнительные разделы).
- **Моё расписание** — `GET /api/bookings/coach/schedule/?from=...&to=...`. Список броней с полями: корт, время, клиент (`client_name`), участники (`participants_names`), **`players_for_match`** (для подстановки в матч).
- **Детали брони** — `GET /api/bookings/{id}/` (тренер видит брони, где он coach). **Отмена** — `POST /api/bookings/{id}/cancel/` (разрешена тренеру этой брони, те же 24 ч).
- **Создать матч** — `POST /api/gamification/matches/create/`: `team_a`, `team_b`, `score`, `winner_team`, `court`. Игроков можно брать из `players_for_match` в ответе расписания/брони. ELO считается автоматически.
- **История матчей** — `GET /api/gamification/matches/` (свои); с `?all=true` — все матчи (для тренера/админа).
- **Персональные тренировки** — `GET /api/gym/personal-training/` (тренер видит сессии, где он coach), создание/редактирование/удаление по необходимости.
- **Уведомления** — те же `GET /api/notifications/`, `unread-count`, mark read (в т.ч. о новых бронях с тренером, если бэкенд их шлёт).

Подробный статус по приложению тренеров и что в API не реализовано (оплата за матч, связь матча с бронированием) — в **`docs/TRAINER_APP_STATUS.md`**.

---

## API Endpoints Summary Table

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| **AUTH** | | | |
| POST | `/api/auth/mobile/send-code/` | No | Send SMS code |
| POST | `/api/auth/mobile/login/` | No | Verify code & login |
| POST | `/api/auth/jwt/refresh/` | No | Refresh access token |
| GET | `/api/auth/users/me/` | Yes | Get my profile |
| PATCH | `/api/auth/users/me/` | Yes | Update profile |
| POST | `/api/auth/me/fcm/` | Yes | Save FCM token |
| GET | `/api/auth/me/stats/` | Yes | My statistics |
| GET | `/api/auth/me/league/` | Yes | My league/rank |
| DELETE | `/api/auth/me/delete/` | Yes | Delete account |
| GET | `/api/auth/home/` | Yes | Home dashboard |
| GET | `/api/auth/search/?search=` | Yes | Search users |
| GET | `/api/auth/users/{id}/profile/` | Yes | Public profile |
| GET | `/api/auth/coaches/` | No | List coaches |
| **COURTS** | | | |
| GET | `/api/courts/` | No | List courts |
| GET | `/api/courts/{id}/` | No | Court detail |
| **BOOKINGS** | | | |
| GET | `/api/bookings/` | Yes | My upcoming bookings |
| GET | `/api/bookings/history/` | Yes | Booking history |
| GET | `/api/bookings/{id}/` | Yes | Booking detail |
| POST | `/api/bookings/create/` | Yes | Create booking |
| POST | `/api/bookings/{id}/cancel/` | Yes | Cancel booking |
| POST | `/api/bookings/{id}/client-confirm/` | Yes | Confirm booking |
| GET | `/api/bookings/check-availability/` | No | Check free slots |
| GET | `/api/bookings/available-coaches/` | No | Free coaches for slot |
| POST | `/api/bookings/price-preview/` | Yes | Preview booking price |
| **MEMBERSHIPS** | | | |
| GET | `/api/memberships/types/` | No | Membership types (store) |
| POST | `/api/memberships/buy/{id}/` | Yes | Buy membership |
| GET | `/api/memberships/my/` | Yes | My memberships |
| POST | `/api/memberships/my/{id}/freeze/` | Yes | Freeze membership |
| POST | `/api/memberships/my/{id}/unfreeze/` | Yes | Unfreeze membership |
| GET | `/api/memberships/my/{id}/history/` | Yes | Membership transactions |
| **LOBBY** | | | |
| GET | `/api/lobby/` | No | List lobbies |
| POST | `/api/lobby/` | Yes | Create lobby |
| GET | `/api/lobby/{id}/` | Yes | Lobby detail |
| POST | `/api/lobby/{id}/join/` | Yes | Join lobby |
| POST | `/api/lobby/{id}/leave/` | Yes | Leave lobby |
| GET | `/api/lobby/my/` | Yes | My lobbies |
| GET | `/api/lobby/{id}/proposals/` | Yes | List proposals |
| POST | `/api/lobby/{id}/proposals/` | Yes | Propose time/court |
| POST | `/api/lobby/{id}/proposals/{pid}/vote/` | Yes | Vote on proposal |
| POST | `/api/lobby/{id}/proposals/{pid}/accept/` | Yes | Accept proposal (creator) |
| POST | `/api/lobby/{id}/assign-teams/` | Yes | Assign teams (creator) |
| POST | `/api/lobby/{id}/book/` | Yes | Create booking (creator) |
| GET | `/api/lobby/{id}/my-extras/` | Yes | My extras |
| POST | `/api/lobby/{id}/my-extras/` | Yes | Add extras |
| DELETE | `/api/lobby/{id}/my-extras/{eid}/` | Yes | Remove extra |
| POST | `/api/lobby/{id}/pay-share/` | Yes | Pay your share |
| GET | `/api/lobby/{id}/payment-status/` | Yes | Payment overview |
| POST | `/api/lobby/{id}/close/` | Yes | Close lobby (creator) |
| **GAMIFICATION** | | | |
| GET | `/api/gamification/matches/` | Yes | My matches |
| GET | `/api/gamification/leaderboard/` | No | Leaderboard |
| **FRIENDS** | | | |
| GET | `/api/friends/` | Yes | My friends |
| POST | `/api/friends/send/` | Yes | Send request |
| GET | `/api/friends/requests/` | Yes | Incoming requests |
| GET | `/api/friends/requests/outgoing/` | Yes | Outgoing requests |
| POST | `/api/friends/respond/` | Yes | Accept/reject |
| POST | `/api/friends/cancel/` | Yes | Cancel request |
| POST | `/api/friends/remove/` | Yes | Remove friend |
| GET | `/api/friends/feed/` | Yes | Friends activity |
| **NOTIFICATIONS** | | | |
| GET | `/api/notifications/` | Yes | List notifications |
| GET | `/api/notifications/unread-count/` | Yes | Unread count |
| POST | `/api/notifications/{id}/read/` | Yes | Mark read |
| POST | `/api/notifications/read-all/` | Yes | Mark all read |
| DELETE | `/api/notifications/{id}/` | Yes | Delete |
| **NEWS** | | | |
| GET | `/api/news/` | No | List news |
| GET | `/api/news/{id}/` | No | News detail |
| **MARKETING** | | | |
| GET | `/api/marketing/promos/` | No | Active promotions |
| GET | `/api/marketing/validate-promo/?code=` | No | Validate promo code |
| **SERVICES** | | | |
| GET | `/api/inventory/services/` | No | Available services |
| **GYM** | | | |
| GET | `/api/gym/qr/generate/` | Yes | Generate QR |
| POST | `/api/gym/checkin/` | Yes | Gym check-in |
| GET | `/api/gym/visits/` | Yes | Visit history |
| GET | `/api/gym/personal-training/` | Yes | Training sessions |
| POST | `/api/gym/personal-training/` | Yes | Create training |
| **FINANCE** | | | |
| GET | `/api/finance/history/` | Yes | My transactions |
| **PAYMENTS** | | | |
| GET | `/api/payments/session/{sid}/status/` | Yes | Payment status |
| **SETTINGS** | | | |
| GET | `/api/core/settings/` | No | Club settings |
| GET | `/api/core/closed-days/` | No | Closed days |
| **TRAINER ONLY** | | | |
| GET | `/api/bookings/coach/schedule/` | Yes | Coach schedule (my bookings as coach) |
| POST | `/api/gamification/matches/create/` | Yes | Create match (coach/admin only) |
| GET | `/api/gym/personal-training/{id}/` | Yes | Get training |
| PATCH | `/api/gym/personal-training/{id}/` | Yes | Update training |
| DELETE | `/api/gym/personal-training/{id}/` | Yes | Delete training |

---

## 21. Court Play Formats & Time-Based Pricing — Flutter Guide

### 21.1 Обзор

В системе два типа кортов с разными форматами игры:

| Тип корта | `play_format` | `court_type` | Макс. игроков | Ценообразование |
|-----------|---------------|--------------|---------------|-----------------|
| Panoramic (9 шт: 5 Indoor + 4 Outdoor) | `TWO_VS_TWO` | `PANORAMIC` / `OUTDOOR` | 4 | Слоты: 06:00–08:00 = 10 000 ₸/ч, 08:00–00:00 = 18 000 ₸/ч |
| Single (1 шт: Indoor) | `ONE_VS_ONE` | `INDOOR` | 2 | Один слот: 06:00–00:00 = 16 000 ₸/ч |

### 21.2 Правила бронирования по формату

#### TWO_VS_TWO (Panoramic)
- Максимум 3 друга (итого 4 игрока)
- Если передать `friends_ids` с 4+ ID → ошибка 400

#### ONE_VS_ONE (Single)
- Максимум 1 друг (итого 2 игрока)
- Если передать `friends_ids` с 2+ ID → ошибка 400

**Ошибки валидации:**
```json
// Слишком много друзей для 1x1 корта
{ "non_field_errors": ["Этот корт только для формата 1x1. Максимум 1 дополнительный игрок."] }

// Слишком много друзей для 2x2 корта
{ "non_field_errors": ["Максимум 3 дополнительных участника для формата 2x2."] }
```

### 21.3 Расчёт цены по ценовым слотам

Цена рассчитывается **автоматически** на бэкенде на основе `price_slots` корта. Flutter показывает пользователю итог.

#### Как Flutter должен отображать ценовые слоты

При показе экрана выбора времени — отображать актуальную цену слота:

```dart
// Пример: получить цену для выбранного времени
CourtPriceSlot? getSlotForTime(List<CourtPriceSlot> slots, TimeOfDay time) {
  for (final slot in slots) {
    final start = slot.startTime;  // "06:00:00"
    final end = slot.endTime;      // "08:00:00" or "00:00:00" (midnight)

    final startMinutes = _toMinutes(start);
    final endMinutes = end == "00:00:00" ? 1440 : _toMinutes(end); // 00:00 = 1440 (midnight)
    final currentMinutes = time.hour * 60 + time.minute;

    if (currentMinutes >= startMinutes && currentMinutes < endMinutes) {
      return slot;
    }
  }
  return null;
}

int _toMinutes(String timeStr) {
  final parts = timeStr.split(':');
  return int.parse(parts[0]) * 60 + int.parse(parts[1]);
}
```

#### Алгоритм расчёта итоговой цены для отображения

```dart
double calculateDisplayPrice(Court court, DateTime start, DateTime end) {
  final slots = court.priceSlots;
  if (slots.isEmpty) {
    final hours = end.difference(start).inMinutes / 60.0;
    return double.parse(court.pricePerHour) * hours;
  }

  double total = 0;
  DateTime current = start;

  while (current.isBefore(end)) {
    final slot = getSlotForTime(slots, TimeOfDay.fromDateTime(current));
    if (slot == null) break;

    // определяем конец текущего слота
    final endStr = slot.endTime;
    DateTime slotEnd;
    if (endStr == "00:00:00") {
      slotEnd = DateTime(current.year, current.month, current.day + 1, 0, 0);
    } else {
      final parts = endStr.split(':');
      slotEnd = DateTime(current.year, current.month, current.day,
          int.parse(parts[0]), int.parse(parts[1]));
    }

    final periodEnd = slotEnd.isBefore(end) ? slotEnd : end;
    final hoursInSlot = periodEnd.difference(current).inMinutes / 60.0;
    total += double.parse(slot.pricePerHour) * hoursInSlot;
    current = periodEnd;
  }

  return total;
}
```

### 21.4 UX-рекомендации для Flutter

#### Экран списка кортов
- Показывать `play_format` бейджем: **"2x2"** или **"1x1"**
- Если у корта несколько `price_slots` — показывать диапазон цен: `10 000 – 18 000 ₸/ч`
- Если один слот — просто `16 000 ₸/ч`

#### Экран выбора времени
- При выборе временного слота динамически показывать актуальную цену
- Отображать легенду слотов: "06:00–08:00: 10 000 ₸/ч | 08:00–00:00: 18 000 ₸/ч"

#### Экран деталей бронирования
- Перед созданием брони — вызвать `POST /api/bookings/price-preview/` и показать итоговую цену
- Это важно, если бронирование пересекает два ценовых слота (например 07:00–09:00)

#### Ограничение добавления друзей
```dart
int maxFriends(String playFormat) {
  return playFormat == 'TWO_VS_TWO' ? 3 : 1;
}
```

### 21.5 Полный сценарий бронирования Panoramic корта (07:00–09:00)

```
1. GET /api/courts/ → получить список кортов, найти Panoramic с play_format=TWO_VS_TWO
2. Пользователь выбирает корт, видит слоты цен:
   - 06:00–08:00: 10 000 ₸/ч
   - 08:00–00:00: 18 000 ₸/ч
3. Пользователь выбирает 07:00, duration=120 мин
4. GET /api/bookings/check-availability/?court_id=1&date=2026-03-28 → убедиться, что слот свободен
5. POST /api/bookings/price-preview/ → { total: 28000.0, breakdown: { court: 28000 } }
6. Показать итог: "Стоимость: 28 000 ₸ (10 000 + 18 000)"
7. POST /api/bookings/create/ → создать бронь
```

### 21.6 Модели данных (Dart)

```dart
class CourtPriceSlot {
  final int id;
  final String startTime;  // "06:00:00"
  final String endTime;    // "08:00:00" or "00:00:00" (midnight = end of day)
  final String pricePerHour;

  CourtPriceSlot.fromJson(Map<String, dynamic> json)
      : id = json['id'],
        startTime = json['start_time'],
        endTime = json['end_time'],
        pricePerHour = json['price_per_hour'];
}

class Court {
  final int id;
  final String name;
  final String courtType;   // "INDOOR", "OUTDOOR", "PANORAMIC"
  final String playFormat;  // "TWO_VS_TWO" or "ONE_VS_ONE"
  final String description;
  final String pricePerHour;         // fallback price
  final List<CourtPriceSlot> priceSlots;
  final String? image;
  final List<CourtImage> gallery;
  final bool isActive;

  Court.fromJson(Map<String, dynamic> json)
      : id = json['id'],
        name = json['name'],
        courtType = json['court_type'],
        playFormat = json['play_format'],
        description = json['description'],
        pricePerHour = json['price_per_hour'],
        priceSlots = (json['price_slots'] as List)
            .map((s) => CourtPriceSlot.fromJson(s))
            .toList(),
        image = json['image'],
        gallery = (json['gallery'] as List)
            .map((g) => CourtImage.fromJson(g))
            .toList(),
        isActive = json['is_active'];
}
```
