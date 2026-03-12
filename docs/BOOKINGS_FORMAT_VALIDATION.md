# Bookings — Валидация формата и ценообразование по слотам

Документация по изменениям в бронировании: **валидация числа игроков по формату корта** и **расчёт цены по временным слотам**.

---

## 1. Валидация числа игроков по play_format

### Правило

При создании брони (`POST /api/bookings/create/`) поле `friends_ids` проверяется относительно формата выбранного корта:

| `court.play_format` | Макс. `friends_ids` | Всего игроков |
|---------------------|---------------------|---------------|
| `TWO_VS_TWO` | 3 | 4 |
| `ONE_VS_ONE` | 1 | 2 |

### Ошибки

```json
// Попытка добавить 2+ друзей на ONE_VS_ONE корт
{
  "non_field_errors": ["Этот корт только для формата 1x1. Максимум 1 дополнительный игрок."]
}

// Попытка добавить 4+ друзей на TWO_VS_TWO корт
{
  "non_field_errors": ["Максимум 3 дополнительных участника для формата 2x2."]
}
```

### Пример корректного запроса для ONE_VS_ONE

```json
POST /api/bookings/create/
{
  "court": 9,
  "start_time": "2026-03-28T10:00:00Z",
  "duration": 60,
  "friends_ids": [15]
}
```

### Пример корректного запроса для TWO_VS_TWO

```json
POST /api/bookings/create/
{
  "court": 1,
  "start_time": "2026-03-28T14:00:00Z",
  "duration": 60,
  "friends_ids": [15, 22, 33]
}
```

---

## 2. Расчёт цены брони по ценовым слотам

### Что изменилось

Раньше цена считалась как:
```
base_court_price = court.price_per_hour × hours
```

Теперь:
```
base_court_price = court.get_price_for_slot(start_time, end_time)
```

Метод учитывает `price_slots` корта и автоматически разбивает бронирование по временным диапазонам.

### Примеры расчёта

**Panoramic корт, 07:00–09:00 (пересекает два слота):**
```
06:00–08:00 = 10 000 ₸/ч → 07:00–08:00: 1ч × 10 000 = 10 000 ₸
08:00–00:00 = 18 000 ₸/ч → 08:00–09:00: 1ч × 18 000 = 18 000 ₸
Итого: 28 000 ₸
```

**Panoramic корт, 09:00–10:00 (один слот):**
```
08:00–00:00 = 18 000 ₸/ч → 09:00–10:00: 1ч × 18 000 = 18 000 ₸
Итого: 18 000 ₸
```

**Single корт, 08:00–09:30 (один слот):**
```
06:00–00:00 = 16 000 ₸/ч → 08:00–09:30: 1.5ч × 16 000 = 24 000 ₸
Итого: 24 000 ₸
```

### Если price_slots не заданы

Система откатывается на `court.price_per_hour`:
```
price = court.price_per_hour × hours
```

---

## 3. Price Preview

Вызов `POST /api/bookings/price-preview/` тоже использует `get_price_for_slot()`.
Нужно вызывать **до** создания брони, чтобы показать пользователю точную стоимость.

**Запрос:**
```json
{
  "court_id": 1,
  "start_time": "2026-03-28T07:00:00Z",
  "duration": 120
}
```

**Ответ:**
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

---

## 4. Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `bookings/serializers.py` | + валидация `friends_ids` по `court.play_format` |
| `bookings/serializers.py` | расчёт `base_court_price` через `court.get_price_for_slot()` |
| `bookings/views.py` | `BookingPricePreviewView` — расчёт через `court.get_price_for_slot()` |
