## Courts — новые типы и API для Flutter

Этот документ дополняет `API_MOBILE.md` и `COURTS_PRICING_AND_FORMATS.md` и описывает последние изменения по кортам.

---

### 1. Новые типы кортов (`court_type`)

В модели `Court` добавлены новые значения `court_type`:

- `SQUASH` — сквош-корты.
- `PING_PONG` — столы для настольного тенниса (ping-pong).

Текущий список значений:

- `INDOOR` — крытый падел-корт.
- `OUTDOOR` — открытый падел-корт.
- `PANORAMIC` — панорамный падел-корт.
- `SQUASH` — сквош.
- `PING_PONG` — настольный теннис.

Эти значения приходят в тех же эндпоинтах, что и раньше:

```http
GET /api/courts/
GET /api/courts/{id}/
GET /api/courts/manage/
GET /api/courts/manage/{id}/
```

**Фронт:** нужно только обновить маппинг `court_type` → лейбл и фильтры.

Пример ответа:

```json
{
  "id": 21,
  "name": "Squash 1",
  "court_type": "SQUASH",
  "play_format": "ONE_VS_ONE",
  "price_per_hour": "10000.00",
  "price_slots": [],
  "is_active": true
}
```

```json
{
  "id": 31,
  "name": "Ping-pong 1",
  "court_type": "PING_PONG",
  "play_format": "ONE_VS_ONE",
  "price_per_hour": "5000.00",
  "price_slots": [],
  "is_active": true
}
```

---

### 2. Связь с системой бронирования

Логика бронирования и расчёта цены **не менялась**:

- `price_per_hour` и `price_slots` работают одинаково для всех типов кортов.
- Эндпоинты бронирований не изменились:
  - `GET /api/bookings/check-availability/`
  - `POST /api/bookings/price-preview/`
  - `POST /api/bookings/create/`

Особенности:

- Для падела по-прежнему действует логика `play_format` (`TWO_VS_TWO` / `ONE_VS_ONE`) и валидации количества участников (см. `BOOKINGS_FORMAT_VALIDATION.md`).
- Для `SQUASH` и `PING_PONG` формат сейчас такой же, как у тренировочного корта — `ONE_VS_ONE` (2 участника).

---

### 3. Рекомендации для фронтенда

- **Фильтры по спорту:**
  - Падел: `court_type in [INDOOR, OUTDOOR, PANORAMIC]`.
  - Сквош: `court_type == SQUASH`.
  - Пинг-понг: `court_type == PING_PONG`.

- **Отображение:**
  - Показывать бейдж типа корта (Pádel / Squash / Ping-pong).
  - При необходимости — отдельные вкладки/табы на экране выбора корта/спорта.

- **Бронирование:**
  - Для падела — использовать текущий UX (выбор корта, количество игроков, инвентарь).
  - Для сквоша/пинг-понга — можно использовать упрощённый флоу бронирования, но через те же эндпоинты.

