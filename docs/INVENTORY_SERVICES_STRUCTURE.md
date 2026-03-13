## Inventory / Services — структура, группы и фото

Этот документ описывает обновлённую модель инвентаря и услуг, а также новые возможности API для фронтенда.

---

### 1. Модель `Service`

Модель находится в `inventory/models.py` и используется для всего:

- инвентарь для падела;
- услуги (функциональная подготовка, турниры);
- Recovery/массажи;
- в будущем — спорт-бар (еда, напитки).

Ключевые поля:

- `id` — идентификатор.
- `name` — название (например, «Аренда ракетки (за игру)»).
- `description` — описание/комментарий для клиента (опционально).
- `price` — цена, `decimal`.
- `group` — **группа**, где используется услуга/инвентарь.
- `category` — **категория**, что это за тип позиции.
- `image` — фото (опционально).
- `is_active` — активна ли позиция для выбора.

#### 1.1. Значения `group`

- `PADEL` — падел (инвентарь, функциональная подготовка, турниры).
- `GYM` — фитнес/зал (можно использовать для будущих услуг зала).
- `RECOVERY` — recovery/массажи/диагностика.
- `SPORT_BAR` — спорт-бар (еда и напитки).
- `OTHER` — прочее.

#### 1.2. Значения `category`

- `INVENTORY` — инвентарь / аренда (ракетки, мячи и т.п.).
- `SERVICE` — услуга (функционалка, консультация, массаж).
- `FOOD` — еда (спорт-бар).
- `DRINK` — напиток (спорт-бар).
- `EVENT` — турнир / мероприятие.

#### 1.3. Фото (`image`)

- `ImageField(upload_to='inventory/')`.
- Может быть `null` / `blank`.
- В API отдаётся как URL (или `null`).

---

### 2. API эндпоинты

#### 2.1. Публичный список для фронта

```http
GET /api/inventory/services/
```

Авторизация: **не требуется**.

По умолчанию возвращает только активные позиции (`is_active = true`), отсортированные по `name`.

**Фильтры (query-параметры):**

- `group` — `PADEL | GYM | RECOVERY | SPORT_BAR | OTHER`.
- `category` — `INVENTORY | SERVICE | FOOD | DRINK | EVENT`.

Примеры:

- Инвентарь падела:

  ```http
  GET /api/inventory/services/?group=PADEL&category=INVENTORY
  ```

- Услуги Recovery:

  ```http
  GET /api/inventory/services/?group=RECOVERY&category=SERVICE
  ```

- Меню спорт-бара:

  ```http
  GET /api/inventory/services/?group=SPORT_BAR&category=FOOD
  GET /api/inventory/services/?group=SPORT_BAR&category=DRINK
  ```

**Формат ответа:**

```json
[
  {
    "id": 1,
    "name": "Аренда ракетки (за игру)",
    "description": "Прокат ракетки для падела на время игры.",
    "price": "3000.00",
    "group": "PADEL",
    "category": "INVENTORY",
    "image": "http://.../media/inventory/racket.jpg",
    "is_active": true
  }
]
```

#### 2.2. Управление (CRM / админка)

```http
GET  /api/inventory/services/manage/
POST /api/inventory/services/manage/

GET    /api/inventory/services/manage/{id}/
PATCH  /api/inventory/services/manage/{id}/
DELETE /api/inventory/services/manage/{id}/
```

Авторизация: `IsAdminRole`.

**Создание/редактирование с фото:**

- Тело запроса — `multipart/form-data`.
- Поля:
  - `name` (string, required),
  - `description` (string, optional),
  - `price` (number, required),
  - `group` (string, required),
  - `category` (string, required),
  - `image` (file, optional),
  - `is_active` (bool).

Пример `curl`:

```bash
curl -X POST "$API" \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -F "name=Аренда ракетки (за игру)" \
  -F "description=Прокат ракетки для падела на время игры." \
  -F "price=3000" \
  -F "group=PADEL" \
  -F "category=INVENTORY" \
  -F "image=@racket.jpg" \
  -F "is_active=true"
```

---

### 3. Скрипт первичного наполнения (`add_all_inventory_services.sh`)

Скрипт `scripts/add_all_inventory_services.sh` добавляет базовый набор позиций из тарифной таблицы клуба.

Запуск:

```bash
export BASE_URL="http://213.155.23.227"   # или свой
export TOKEN="your-admin-jwt-token"      # ADMIN JWT
bash scripts/add_all_inventory_services.sh
```

Добавляются группы:

- **PADEL / INVENTORY**:
  - Аренда ракетки (за игру)
  - Мячи (упаковка, за игру)
- **PADEL / SERVICE**:
  - Функциональная подготовка падел — индивидуальная, 1 час
  - Функциональная подготовка падел — группа до 6 чел, 1 час
- **PADEL / EVENT**:
  - Участие в турнире (1 человек)
- **RECOVERY / SERVICE**:
  - Recovery — первичная консультация
  - Recovery — функциональная диагностика (от 15 000)
  - Лечебный массаж — 1 час
  - Спортивный массаж — 1 час

> Фото по умолчанию скрипт не загружает — их можно добавить вручную через админку или отдельными `PATCH` запросами.

---

### 4. Рекомендации для фронтенда

- **Экран бронирования падела:**
  - Загружать инвентарь через `group=PADEL&category=INVENTORY`.
  - Отображать `image` и `description` в карточке.

- **Раздел Recovery:**
  - Использовать `group=RECOVERY&category=SERVICE`.

- **Спорт-бар (будущее):**
  - Еда: `group=SPORT_BAR&category=FOOD`.
  - Напитки: `group=SPORT_BAR&category=DRINK`.

