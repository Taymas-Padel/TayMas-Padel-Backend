# Турниры — документация для CRM (менеджмент / ресепшн)

**Base URL:** `/api/tournaments/`
**Auth:** все manage-эндпоинты требуют роль `ADMIN` или `RECEPTIONIST`

---

## Оглавление

1. [Модели и статусы](#1-модели-и-статусы)
2. [Список турниров](#2-список-турниров)
3. [Создать турнир](#3-создать-турнир)
4. [Детали / обновление турнира](#4-детали--обновление-турнира)
5. [Смена статуса турнира](#5-смена-статуса-турнира)
6. [Управление командами / участниками](#6-управление-командами--участниками)
7. [Оплата и возврат взносов](#7-оплата-и-возврат-взносов)
8. [Генерация сетки](#8-генерация-сетки)
9. [Просмотр сетки](#9-просмотр-сетки)
10. [Матчи — список и управление](#10-матчи--список-и-управление)
11. [Отчёт по турниру](#11-отчёт-по-турниру)
12. [Бизнес-правила и ограничения](#12-бизнес-правила-и-ограничения)

---

## 1. Модели и статусы

### Статусы турнира

| Статус | Код | Переходы |
|--------|-----|---------|
| Черновик | `DRAFT` | → REGISTRATION, CANCELED |
| Открыта регистрация | `REGISTRATION` | → IN_PROGRESS, CANCELED |
| Идёт турнир | `IN_PROGRESS` | → COMPLETED, CANCELED |
| Завершён | `COMPLETED` | — |
| Отменён | `CANCELED` | — |

### Форматы турнира

| Формат | Код | Команда |
|--------|-----|---------|
| Парный падел | `DOUBLES` | 2 игрока |
| Одиночный | `SINGLES` | 1 игрок |

### Статусы команды

| Статус | Код | Описание |
|--------|-----|----------|
| Заявка | `PENDING` | Зарегистрирован, ждёт подтверждения |
| Подтверждён | `CONFIRMED` | Организатор подтвердил участие |
| Оплачен | `PAID` | Взнос оплачен, попадает в сетку |
| Снят | `WITHDRAWN` | Отказался от участия |
| Возврат | `REFUNDED` | Взнос возвращён |

### Статусы матча

| Статус | Код |
|--------|-----|
| Запланирован | `SCHEDULED` |
| Идёт | `IN_PROGRESS` |
| Завершён | `COMPLETED` |
| Перенесён | `POSTPONED` |
| Тех. выигрыш | `WALKOVER` |

---

## 2. Список турниров

```
GET /api/tournaments/manage/
```

**Auth:** RECEPTIONIST+

**Query params:**
- `?status=REGISTRATION` — фильтр по статусу
- `?format=DOUBLES` — фильтр по формату

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Grand Padel Cup 2026",
    "start_date": "2026-04-15T10:00:00Z",
    "end_date": "2026-04-15T20:00:00Z",
    "registration_deadline": "2026-04-10T23:59:00Z",
    "status": "REGISTRATION",
    "format": "DOUBLES",
    "is_paid": true,
    "entry_fee": "12000.00",
    "max_teams": 16,
    "teams_count": 8,
    "paid_teams_count": 5,
    "created_at": "2026-03-01T10:00:00Z"
  }
]
```

---

## 3. Создать турнир

```
POST /api/tournaments/manage/create/
```

**Auth:** ADMIN

**Body:**
```json
{
  "name": "Grand Padel Cup 2026",
  "description": "Открытый турнир клуба по падел. Одиночное выбывание.",
  "start_date": "2026-04-15T10:00:00Z",
  "end_date": "2026-04-15T20:00:00Z",
  "registration_deadline": "2026-04-10T23:59:00Z",
  "format": "DOUBLES",
  "is_paid": true,
  "entry_fee": 12000,
  "max_teams": 16,
  "prize_info": "1 место — 100 000₸, 2 место — 50 000₸"
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `name` | string | ✅ | Название |
| `description` | string | ❌ | Описание |
| `start_date` | datetime | ✅ | Начало |
| `end_date` | datetime | ✅ | Конец |
| `registration_deadline` | datetime | ❌ | Дедлайн заявок |
| `format` | `DOUBLES` / `SINGLES` | ✅ | Формат |
| `is_paid` | bool | ✅ | Платный ли |
| `entry_fee` | decimal | ✅ если paid | Взнос ₸ |
| `max_teams` | int | ❌ | Лимит команд |
| `prize_info` | string | ❌ | Призы |

**Response 201:** объект турнира.

---

## 4. Детали / обновление турнира

```
GET   /api/tournaments/<id>/
PATCH /api/tournaments/manage/<id>/
```

**PATCH** — в статусе `DRAFT` можно изменить всё.
В `REGISTRATION` и выше допустимы только: `name`, `description`, `prize_info`, `registration_deadline`.

**Response 200:**
```json
{
  "id": 1,
  "name": "Grand Padel Cup 2026",
  "description": "...",
  "start_date": "2026-04-15T10:00:00Z",
  "end_date": "2026-04-15T20:00:00Z",
  "registration_deadline": "2026-04-10T23:59:00Z",
  "status": "REGISTRATION",
  "format": "DOUBLES",
  "is_paid": true,
  "entry_fee": "12000.00",
  "max_teams": 16,
  "prize_info": "1 место — 100 000₸",
  "teams_count": 8,
  "paid_teams_count": 5,
  "created_by": 1,
  "created_by_info": { "id": 1, "name": "Азамат Admin", "phone": "+77001234567" },
  "created_at": "2026-03-01T10:00:00Z",
  "updated_at": "2026-03-10T15:00:00Z"
}
```

---

## 5. Смена статуса турнира

```
POST /api/tournaments/manage/<id>/status/
```

**Auth:** ADMIN

**Body:**
```json
{ "status": "REGISTRATION" }
```

**Допустимые переходы:**
```
DRAFT → REGISTRATION → IN_PROGRESS → COMPLETED
                    ↓              ↓
                 CANCELED       CANCELED
```

**Response 200:**
```json
{ "id": 1, "status": "REGISTRATION", "status_display": "Открыта регистрация" }
```

**Ошибка 400:**
```json
{ "status": ["Нельзя перейти из статуса «Завершён» в «Черновик»."] }
```

---

## 6. Управление командами / участниками

### Список команд

```
GET /api/tournaments/<id>/teams/
```

**Auth:** Any

**Response 200:**
```json
[
  {
    "id": 3,
    "tournament": 1,
    "display_name": "Азамат / Данияр",
    "team_name": "",
    "player1": 42,
    "player1_info": { "id": 42, "name": "Азамат Есимханулы", "phone": "+77001234567" },
    "player2": 15,
    "player2_info": { "id": 15, "name": "Данияр Сейткали", "phone": "+77009876543" },
    "status": "PAID",
    "seed": 1,
    "registered_at": "2026-03-05T10:00:00Z",
    "confirmed_at": "2026-03-06T09:00:00Z",
    "paid_at": "2026-03-06T09:05:00Z",
    "paid_by_info": { "id": 1, "name": "Ресепшн Менеджер", "phone": null },
    "payment_method": "KASPI",
    "notes": ""
  }
]
```

### Добавить команду (CRM от лица менеджера)

```
POST /api/tournaments/<id>/teams/
```

Доступно только если статус турнира `REGISTRATION`.

**Body:**
```json
{
  "player1_id": 42,
  "player2_id": 15,
  "team_name": "Dream Team"
}
```

> Для `SINGLES` — передавать только `player1_id`.

### Обновить статус команды

```
PATCH /api/tournaments/<tid>/teams/<team_id>/
```

**Auth:** RECEPTIONIST+

**Body:**
```json
{ "status": "CONFIRMED", "notes": "Подтверждено лично" }
```

---

## 7. Оплата и возврат взносов

### Подтвердить оплату

```
POST /api/tournaments/manage/<tid>/teams/<team_id>/confirm-payment/
```

**Auth:** RECEPTIONIST+

**Body:**
```json
{ "payment_method": "KASPI" }
```

> Только для платных турниров (`is_paid=true`).
> Статус команды → `PAID`. Фиксируется: время, менеджер, способ оплаты.

**Response 200:** обновлённый объект команды.

### Возврат взноса

```
POST /api/tournaments/manage/<tid>/teams/<team_id>/refund/
```

> Доступно для команд со статусом `PAID` или `WITHDRAWN`.
> Статус → `REFUNDED`.

**Response 200:**
```json
{ "detail": "Возврат отмечен.", "team_id": 3 }
```

---

## 8. Генерация сетки

```
POST /api/tournaments/manage/<id>/generate-bracket/
```

**Auth:** ADMIN

> Берёт все команды со статусом `CONFIRMED` или `PAID`.
> Строит Single Elimination сетку (следующая степень двойки от числа команд).
> При повторном вызове — **пересоздаёт** сетку с нуля (старые матчи удаляются).

**Важно:** минимум **2 команды** должны быть в статусе `CONFIRMED`/`PAID`.

**Response 200:**
```json
{
  "detail": "Сетка сгенерирована: 7 матчей.",
  "bracket": { ... }
}
```

**Ошибка 400:**
```json
{ "detail": "Нужно минимум 2 подтверждённые команды для генерации сетки." }
```

**Сид (посев):**
Команды с меньшим `seed` получают лучшую позицию в сетке.
Установить seed: `PATCH /api/tournaments/<tid>/teams/<team_id>/` с `{ "seed": 1 }`.

---

## 9. Просмотр сетки

```
GET /api/tournaments/<id>/bracket/
```

**Auth:** Any

**Response 200:**
```json
{
  "tournament_id": 1,
  "total_rounds": 3,
  "rounds": [
    {
      "round_number": 1,
      "round_name": "1/4 финала",
      "matches": [
        {
          "id": 1,
          "round_number": 1,
          "round_name": "1/4 финала",
          "match_number": 1,
          "team1": 3,
          "team1_info": { "id": 3, "display_name": "Азамат / Данияр", "status": "PAID", "seed": 1, "player1_info": {...}, "player2_info": {...} },
          "team2": 5,
          "team2_info": { "id": 5, "display_name": "Серик / Асхат", "status": "PAID", "seed": 4, ... },
          "winner": null,
          "winner_info": null,
          "court": null,
          "court_name": null,
          "scheduled_at": null,
          "status": "SCHEDULED",
          "score_team1": "",
          "score_team2": "",
          "next_match": 5,
          "notes": ""
        }
      ]
    },
    {
      "round_number": 2,
      "round_name": "Полуфинал",
      "matches": [ ... ]
    },
    {
      "round_number": 3,
      "round_name": "Финал",
      "matches": [ ... ]
    }
  ]
}
```

---

## 10. Матчи — список и управление

### Список матчей

```
GET /api/tournaments/<id>/matches/
```

**Query params:**
- `?date=2026-04-15` — по дате
- `?court_id=2` — по корту
- `?status=SCHEDULED` — по статусу

### Управление матчем (назначить время, корт, результат)

```
PATCH /api/tournaments/manage/<tid>/matches/<match_id>/
```

**Auth:** RECEPTIONIST+

**Body (все поля необязательны):**
```json
{
  "scheduled_at": "2026-04-15T11:00:00Z",
  "court": 2,
  "status": "IN_PROGRESS",
  "score_team1": "6-3",
  "score_team2": "4-6",
  "winner": 3,
  "notes": "Переигровка по жеребьёвке"
}
```

| Поле | Описание |
|------|----------|
| `scheduled_at` | Время матча |
| `court` | ID корта |
| `status` | Новый статус матча |
| `score_team1` | Счёт команды 1 (текст, напр. "6-3, 6-4") |
| `score_team2` | Счёт команды 2 |
| `winner` | ID победившей команды — **автоматически продвигает победителя** в следующий матч сетки |
| `notes` | Примечания |

**При указании `winner`:**
- Статус матча → `COMPLETED`
- Победитель автоматически попадает в `team1` или `team2` следующего матча

**Конфликты при назначении:**
- Если корт уже занят другим матчем в это время → ошибка 400
- Если одна из команд уже играет в это время → ошибка 400

**Ошибки:**
```json
{ "detail": "Корт «Panoramic Indoor 1» уже занят в это время (матч #3)." }
{ "detail": "Команда «Азамат / Данияр» уже играет в это время (матч #7)." }
```

---

## 11. Отчёт по турниру

```
GET /api/tournaments/manage/<id>/report/
```

**Auth:** RECEPTIONIST+

**Response 200:**
```json
{
  "tournament": { ... },
  "total_teams": 8,
  "paid_teams": 7,
  "withdrawn_teams": 1,
  "revenue": 84000.0,
  "winner": {
    "id": 3,
    "display_name": "Азамат / Данияр",
    "status": "PAID",
    "seed": 1,
    "player1_info": { ... },
    "player2_info": { ... }
  },
  "teams": [
    {
      "team": { ... },
      "matches_played": 3,
      "won": 3
    }
  ]
}
```

---

## 12. Бизнес-правила и ограничения

| Правило | Детали |
|---------|--------|
| Регистрация открыта | Только пока статус = `REGISTRATION` |
| В сетку попадают | Только команды `CONFIRMED` или `PAID` |
| Для платного турнира | Только `PAID` команды считаются |
| Дубликат игрока | Один игрок не может быть в двух командах одного турнира |
| Лимит команд | Если задан `max_teams` — при достижении лимита регистрация закрывается |
| Bye (пропуск) | Если число команд не кратно степени двойки — некоторые команды получают автоматический проход |
| Конфликт корта | Система проверяет пересечение по времени при назначении матча |
| Авто-продвижение | При вводе победителя — система сама заполняет следующий матч |
| Пересоздание сетки | `generate-bracket` полностью удаляет и создаёт сетку заново |
