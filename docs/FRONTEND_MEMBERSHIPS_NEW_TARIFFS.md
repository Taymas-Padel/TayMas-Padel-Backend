# Новая система абонементов — Документация для фронтенда

## Что изменилось

Модель абонементов полностью переработана под тарифную систему клуба:

| Старый `service_type` | Новый `service_type` | Описание |
|---|---|---|
| `PADEL` | `PADEL_HOURS` | Пакет часов (8ч / 12ч) с приоритетным временем |
| `GYM_UNLIMITED` | `GYM` | Фитнес — безлимит (3/6/12 мес) |
| `GYM_PACK` | `GYM` | Фитнес — пакет (через `total_visits`) |
| — | `TRAINING_HOURS` | Тренировки с тренером — пакет часов (включает тренера) |
| — | `VIP` | VIP — комбо пакет (фитнес + падел + VIP-зона) |

### Новые поля `MembershipType`

| Поле | Тип | Описание |
|---|---|---|
| `description` | string | Описание / комментарий к абонементу |
| `priority_time_start` | time / null | Начало приоритетного окна (напр. `"06:00"`) |
| `priority_time_end` | time / null | Конец приоритетного окна (напр. `"15:00"`) |
| `prime_time_surcharge` | decimal | Доплата за прайм-тайм (₸/час). Если бронь вне приоритетного окна |
| `min_participants` | int | Минимум участников |
| `max_participants` | int | Максимум участников |
| `includes_coach` | boolean | Включён ли тренер в пакет |
| `court_type_restriction` | string | `""` = любой, `"PANORAMIC"`, `"INDOOR"`, `"OUTDOOR"` |
| `service_type_display` | string | Человеко-читаемое название типа |

---

## API Эндпоинты

### 1. Каталог типов абонементов (публичный)

```
GET /api/memberships/types/
```

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Пакет 8 часов",
    "description": "Инструмент загрузки непиковых часов. Не заменяет прайм-тайм.",
    "service_type": "PADEL_HOURS",
    "service_type_display": "Падел — Пакет часов",
    "price": "128000.00",
    "days_valid": 30,
    "total_hours": "8.0",
    "total_visits": 0,
    "priority_time_start": "06:00:00",
    "priority_time_end": "15:00:00",
    "prime_time_surcharge": "4000.00",
    "min_participants": 1,
    "max_participants": 4,
    "includes_coach": false,
    "court_type_restriction": "",
    "discount_on_court": 0,
    "is_active": true
  },
  {
    "id": 2,
    "name": "Пакет 12 часов",
    "description": "Приоритетное использование 06:00-15:00",
    "service_type": "PADEL_HOURS",
    "service_type_display": "Падел — Пакет часов",
    "price": "192000.00",
    "days_valid": 30,
    "total_hours": "12.0",
    "total_visits": 0,
    "priority_time_start": "06:00:00",
    "priority_time_end": "15:00:00",
    "prime_time_surcharge": "4000.00",
    "min_participants": 1,
    "max_participants": 4,
    "includes_coach": false,
    "court_type_restriction": "",
    "discount_on_court": 0,
    "is_active": true
  },
  {
    "id": 3,
    "name": "Тренировки 1-2 чел (6ч)",
    "description": "Формат регулярной работы с тренером",
    "service_type": "TRAINING_HOURS",
    "service_type_display": "Тренировки с тренером — Пакет часов",
    "price": "120000.00",
    "days_valid": 30,
    "total_hours": "6.0",
    "total_visits": 0,
    "priority_time_start": "06:00:00",
    "priority_time_end": "15:00:00",
    "prime_time_surcharge": "0.00",
    "min_participants": 1,
    "max_participants": 2,
    "includes_coach": true,
    "court_type_restriction": "",
    "discount_on_court": 0,
    "is_active": true
  },
  {
    "id": 5,
    "name": "Фитнес 3 месяца",
    "description": "Полноценный доступ к фитнес-инфраструктуре клуба",
    "service_type": "GYM",
    "service_type_display": "Фитнес — Безлимит",
    "price": "150000.00",
    "days_valid": 90,
    "total_hours": "0.0",
    "total_visits": 0,
    "priority_time_start": null,
    "priority_time_end": null,
    "prime_time_surcharge": "0.00",
    "min_participants": 1,
    "max_participants": 1,
    "includes_coach": false,
    "court_type_restriction": "",
    "discount_on_court": 0,
    "is_active": true
  }
]
```

---

### 2. Управление типами (Admin/Ресепшн)

```
GET    /api/memberships/types/manage/         — список всех (вкл. неактивные)
POST   /api/memberships/types/manage/         — создать новый тип
GET    /api/memberships/types/manage/<id>/    — детали
PATCH  /api/memberships/types/manage/<id>/    — редактировать
DELETE /api/memberships/types/manage/<id>/    — удалить
```

**Создание абонемента «Пакет 8 часов»:**
```json
POST /api/memberships/types/manage/
{
  "name": "Пакет 8 часов",
  "description": "Инструмент загрузки непиковых часов. Прайм-тайм (15:00-22:00) — доплата 4000₸/час",
  "service_type": "PADEL_HOURS",
  "price": 128000,
  "days_valid": 30,
  "total_hours": 8,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00",
  "prime_time_surcharge": 4000
}
```

**Создание «Тренировки 3-4 чел (8ч)»:**
```json
POST /api/memberships/types/manage/
{
  "name": "Тренировки 3-4 чел (8ч)",
  "description": "Абонемент на тренировки. Корт + тренер включены.",
  "service_type": "TRAINING_HOURS",
  "price": 240000,
  "days_valid": 30,
  "total_hours": 8,
  "min_participants": 3,
  "max_participants": 4,
  "includes_coach": true,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00"
}
```

**Создание «Фитнес 12 месяцев»:**
```json
POST /api/memberships/types/manage/
{
  "name": "Фитнес 12 месяцев",
  "description": "Полноценный доступ к фитнес-инфраструктуре клуба",
  "service_type": "GYM",
  "price": 420000,
  "days_valid": 365
}
```

**Создание «VIP Раздевалка»:**
```json
POST /api/memberships/types/manage/
{
  "name": "VIP раздевалка + Фитнес",
  "description": "Фитнес зал + мембера падела. Индивидуальный шкафчик, зона отдыха, сауна.",
  "service_type": "VIP",
  "price": 1000000,
  "days_valid": 365,
  "discount_on_court": 10
}
```

---

### 3. Покупка абонемента

**Клиент сам:**
```
POST /api/memberships/buy/<type_id>/
```

**Ресепшн от имени клиента:**
```
POST /api/memberships/reception/buy/
{
  "client_id": 42,
  "membership_type_id": 1,
  "payment_method": "KASPI"
}
```

**Ответ (ресепшн):**
```json
{
  "status": "Абонемент выдан",
  "membership": {
    "id": 15,
    "user": 42,
    "user_name": "Azamat Yessimkhanuly",
    "membership_type": 1,
    "membership_type_name": "Пакет 8 часов",
    "type_name": "Пакет 8 часов",
    "service_type": "PADEL_HOURS",
    "service_type_display": "Падел — Пакет часов",
    "start_date": "2026-03-11T12:00:00Z",
    "end_date": "2026-04-10T12:00:00Z",
    "hours_remaining": "8.0",
    "visits_remaining": 0,
    "is_active": true,
    "is_frozen": false,
    "priority_time_start": "06:00:00",
    "priority_time_end": "15:00:00",
    "prime_time_surcharge": "4000.00",
    "includes_coach": false,
    "min_participants": 1,
    "max_participants": 4
  }
}
```

---

### 4. Мои абонементы (клиент)

```
GET /api/memberships/my/
```

Каждый абонемент теперь содержит:
- `service_type` / `service_type_display` — тип
- `priority_time_start` / `priority_time_end` — приоритетное окно
- `prime_time_surcharge` — доплата за прайм-тайм
- `includes_coach` — покрывает ли тренера
- `min_participants` / `max_participants` — диапазон участников

---

### 5. Превью цены (с учётом абонемента и прайм-тайма)

```
POST /api/bookings/price-preview/
{
  "court_id": 1,
  "start_time": "2026-03-15T10:00:00Z",
  "duration": 60,
  "coach_id": 5,
  "service_ids": [],
  "friends_ids": [10, 11]
}
```

**Ответ (бронь в приоритетное время, абонемент покрывает):**
```json
{
  "total": 0.0,
  "breakdown": {
    "court": 0.0,
    "coach": 24000.0,
    "services": 0.0,
    "prime_time_surcharge": 0.0
  },
  "membership_applied": true,
  "membership_name": "Пакет 8 часов",
  "hours_remaining_after": 7.0,
  "coach_covered_by_membership": false
}
```

**Ответ (бронь в прайм-тайм 17:00, абонемент есть, доплата 4000₸):**
```json
{
  "total": 4000.0,
  "breakdown": {
    "court": 0.0,
    "coach": 0.0,
    "services": 0.0,
    "prime_time_surcharge": 4000.0
  },
  "membership_applied": true,
  "membership_name": "Пакет 8 часов",
  "hours_remaining_after": 7.0,
  "coach_covered_by_membership": false,
  "prime_time_info": {
    "priority_window": "06:00-15:00",
    "surcharge_per_hour": 4000.0,
    "prime_hours": 1.0,
    "surcharge_total": 4000.0
  }
}
```

**Ответ (тренировочный абонемент покрывает и корт, и тренера):**
```json
{
  "total": 0.0,
  "breakdown": {
    "court": 0.0,
    "coach": 0.0,
    "services": 0.0,
    "prime_time_surcharge": 0.0
  },
  "membership_applied": true,
  "membership_name": "Тренировки 1-2 чел (6ч)",
  "hours_remaining_after": 5.0,
  "coach_covered_by_membership": true
}
```

---

### 6. Создание брони

```
POST /api/bookings/create/
```
Тело без изменений. Логика внутри автоматически:
1. Ищет лучший абонемент (сначала TRAINING_HOURS если есть тренер, потом PADEL_HOURS)
2. Проверяет количество участников (1 + friends_ids) на min/max
3. Проверяет тип корта (court_type_restriction)
4. Списывает часы
5. Считает доплату за прайм-тайм если бронь выходит за приоритетное окно
6. Если `includes_coach` = true — тренер бесплатно

---

## Логика подбора абонемента при брони

```
1. Есть тренер в брони?
   ├── ДА → ищем TRAINING_HOURS с includes_coach=true
   │        ├── нашли → тренер бесплатно, корт бесплатно, проверяем прайм-тайм
   │        └── нет   → ищем PADEL_HOURS (тренер платно)
   └── НЕТ → ищем PADEL_HOURS

2. Нашли абонемент?
   ├── ДА → списываем часы, корт = 0₸
   │        ├── бронь в приоритетное время (06:00-15:00) → без доплаты
   │        └── бронь в прайм-тайм (15:00-22:00) → + surcharge × часы
   └── НЕТ → обычная цена корта + тренер + инвентарь
```

---

## Примеры абонементов по тарифной таблице

| Название | service_type | price | total_hours | days_valid | priority_time | surcharge | participants | includes_coach |
|---|---|---|---|---|---|---|---|---|
| Пакет 8 часов | PADEL_HOURS | 128000 | 8 | 30 | 06:00-15:00 | 4000 | 1-4 | нет |
| Пакет 12 часов | PADEL_HOURS | 192000 | 12 | 30 | 06:00-15:00 | 4000 | 1-4 | нет |
| Тренировки 1-2 чел (6ч) | TRAINING_HOURS | 120000 | 6 | 30 | 06:00-15:00 | 0 | 1-2 | да |
| Тренировки 1-2 чел (8ч) | TRAINING_HOURS | 160000 | 8 | 30 | 06:00-15:00 | 0 | 1-2 | да |
| Тренировки 3-4 чел (6ч) | TRAINING_HOURS | 180000 | 6 | 30 | 06:00-15:00 | 0 | 3-4 | да |
| Тренировки 3-4 чел (8ч) | TRAINING_HOURS | 240000 | 8 | 30 | 06:00-15:00 | 0 | 3-4 | да |
| Фитнес 3 мес | GYM | 150000 | 0 | 90 | — | — | 1 | нет |
| Фитнес 6 мес | GYM | 240000 | 0 | 180 | — | — | 1 | нет |
| Фитнес 12 мес | GYM | 420000 | 0 | 365 | — | — | 1 | нет |
| VIP Раздевалка | VIP | 1000000 | 0 | 365 | — | — | 1 | нет |

---

## Фронтенд: что показывать пользователю

### На экране «Мои абонементы»

Для каждого абонемента показывать:
- **Название** и **тип** (`service_type_display`)
- **Остаток часов** (`hours_remaining`) — для PADEL_HOURS и TRAINING_HOURS
- **Срок действия** (`end_date`)
- **Статус** (активен/заморожен)
- **Приоритетное время**: `priority_time_start`–`priority_time_end` (если есть)
- **Доплата**: «Прайм-тайм: +{prime_time_surcharge}₸/час» (если > 0)
- **Тренер включён**: плашка если `includes_coach = true`
- **Участники**: «{min_participants}–{max_participants} чел»

### На экране «Оформление брони» (price-preview)

Если `membership_applied = true`:
- Показать «Корт по абонементу ✓»
- Если `coach_covered_by_membership = true` → «Тренер по абонементу ✓»
- Если `prime_time_info` присутствует → показать предупреждение:
  > «Бронь вне приоритетного окна ({priority_window}). Доплата: {surcharge_total}₸»
- Показать `hours_remaining_after` — «После брони останется X.X часов»
