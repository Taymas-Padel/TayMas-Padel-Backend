# Courts — Play Formats & Time-Based Pricing

Документация по двум новым фичам: **формат игры** (play_format) и **ценовые слоты по времени** (price_slots).

---

## 1. Форматы игры (play_format)

### Что добавлено

Поле `play_format` на модели `Court`:

| Значение | Описание | Макс. игроков |
|----------|----------|---------------|
| `TWO_VS_TWO` | Panoramic корты — игра 2x2 | 4 (хозяин + 3 друга) |
| `ONE_VS_ONE` | Single корт — игра 1x1 | 2 (хозяин + 1 друг) |

### Реальные данные клуба

| Тип | Кол-во | `play_format` | Описание |
|-----|--------|---------------|----------|
| Panoramic Indoor | 5 | `TWO_VS_TWO` | Крытые панорамные |
| Panoramic Outdoor | 4 | `TWO_VS_TWO` | Открытые панорамные |
| Single Indoor | 1 | `ONE_VS_ONE` | Тренировочный корт |

### В ответе API

```
GET /api/courts/
GET /api/courts/{id}/
```

```json
{
  "id": 1,
  "name": "Panoramic 1",
  "court_type": "PANORAMIC",
  "play_format": "TWO_VS_TWO",
  ...
}
```

---

## 2. Ценовые слоты (CourtPriceSlot)

### Что добавлено

Новая модель `CourtPriceSlot` — ценовые диапазоны по времени суток.

**Поля:**

| Поле | Тип | Описание |
|------|-----|----------|
| `court` | FK | Корт |
| `start_time` | time | Начало слота (HH:MM) |
| `end_time` | time | Конец слота. `00:00` = полночь (конец суток = 24:00) |
| `price_per_hour` | decimal | Цена за час в этом слоте |

### Цены клуба из тарифной системы

**Panoramic корт (TWO_VS_TWO):**

| Слот | Время | Цена |
|------|-------|------|
| Утренний | 06:00 – 08:00 | 10 000 ₸/ч |
| Дневной/вечерний | 08:00 – 00:00 | 18 000 ₸/ч |

**Single корт (ONE_VS_ONE):**

| Слот | Время | Цена |
|------|-------|------|
| Весь день | 06:00 – 00:00 | 16 000 ₸/ч |

### В ответе API

```json
{
  "id": 1,
  "name": "Panoramic 1",
  "play_format": "TWO_VS_TWO",
  "price_per_hour": "18000.00",
  "price_slots": [
    { "id": 1, "start_time": "06:00:00", "end_time": "08:00:00", "price_per_hour": "10000.00" },
    { "id": 2, "start_time": "08:00:00", "end_time": "00:00:00", "price_per_hour": "18000.00" }
  ]
}
```

> `price_per_hour` на корте — резервная цена. Используется только если `price_slots` пустой.

---

## 3. Как настроить в Django Admin

1. Войти в Admin → **Корты**
2. Открыть нужный корт
3. Установить **Формат игры** (`play_format`)
4. В секции **Ценовые слоты** добавить строки:
   - `06:00` → `08:00` → `10000`
   - `08:00` → `00:00` → `18000`
5. Сохранить

> Поле `end_time = 00:00` в форме — это полночь (конец суток).

---

## 4. Расчёт цены

Метод `Court.get_price_for_slot(start_dt, end_dt)` автоматически рассчитывает стоимость по слотам.

**Пример: бронирование 07:00–09:00 (2 часа) на Panoramic корте**

```
Слот 06:00–08:00 (10 000 ₸/ч):
  07:00–08:00 = 1 час × 10 000 = 10 000 ₸

Слот 08:00–00:00 (18 000 ₸/ч):
  08:00–09:00 = 1 час × 18 000 = 18 000 ₸

Итого: 28 000 ₸
```

Если `price_slots` не заданы — используется `price_per_hour × hours`.

---

## 5. Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `courts/models.py` | + поле `play_format`, + модель `CourtPriceSlot`, + метод `get_price_for_slot()` |
| `courts/admin.py` | + `CourtPriceSlotInline`, `play_format` в list_display |
| `courts/serializers.py` | + `play_format`, + `price_slots` в `CourtSerializer` |
| `courts/migrations/0004_add_play_format_and_price_slots.py` | миграция |
