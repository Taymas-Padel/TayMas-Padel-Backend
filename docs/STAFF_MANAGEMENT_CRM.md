# Управление сотрудниками — документация CRM

**Base URL:** `/api/auth/staff/`
**Auth:** все эндпоинты требуют роль `ADMIN`

---

## Оглавление

1. [Роли и доступы](#1-роли-и-доступы)
2. [Список сотрудников](#2-список-сотрудников)
3. [Создать сотрудника](#3-создать-сотрудника)
4. [Детали сотрудника](#4-детали-сотрудника)
5. [Обновить сотрудника](#5-обновить-сотрудника)
6. [Сменить пароль](#6-сменить-пароль)
7. [Активировать / деактивировать](#7-активировать--деактивировать)
8. [Удалить аккаунт](#8-удалить-аккаунт)
9. [Бизнес-правила и ограничения](#9-бизнес-правила-и-ограничения)

---

## 1. Роли и доступы

| Роль | Код | CRM-вход | Мобильный вход |
|------|-----|----------|----------------|
| Супер-администратор | `ADMIN` | ✅ по логину + паролю | ❌ |
| Ресепшн | `RECEPTIONIST` | ✅ по логину + паролю | ❌ |
| Менеджер продаж | `SALES_MANAGER` | ✅ по логину + паролю | ❌ |
| Тренер по паделу | `COACH_PADEL` | ❌ | ✅ по SMS |
| Фитнес-тренер | `COACH_FITNESS` | ❌ | ✅ по SMS |
| Клиент | `CLIENT` | ❌ | ✅ по SMS |

> Клиенты (`CLIENT`) создаются автоматически при первом входе через SMS.
> Сотрудников (`ADMIN`, `RECEPTIONIST`, `SALES_MANAGER`, `COACH_PADEL`, `COACH_FITNESS`) создаёт только администратор через этот API.

### Что может каждая роль в CRM

| Действие | ADMIN | RECEPTIONIST | SALES_MANAGER |
|----------|-------|--------------|---------------|
| Управление сотрудниками | ✅ | ❌ | ❌ |
| Управление клиентами | ✅ | ✅ | ✅ |
| Создать / отменить бронь | ✅ | ✅ | ❌ |
| Создать турнир | ✅ | ❌ | ❌ |
| Управлять командами турнира | ✅ | ✅ | ❌ |
| Подтверждать оплату | ✅ | ✅ | ❌ |
| Просмотр финансов | ✅ | ✅ | ✅ |
| Управлять корными / слотами | ✅ | ❌ | ❌ |

---

## 2. Список сотрудников

```
GET /api/auth/staff/
```

**Auth:** ADMIN

**Query params:**
- `?search=Азамат` — поиск по имени, фамилии, username, телефону
- `?role=RECEPTIONIST` — фильтр по роли
- `?is_active=true` / `?is_active=false` — фильтр по статусу

**Response 200:**
```json
[
  {
    "id": 1,
    "username": "admin",
    "first_name": "Азамат",
    "last_name": "Есимханулы",
    "full_name": "Азамат Есимханулы",
    "phone_number": "+77001234567",
    "email": "admin@grandpadel.kz",
    "role": "ADMIN",
    "role_display": "Super Admin",
    "price_per_hour": "0.00",
    "is_active": true,
    "avatar": null,
    "created_at": "2026-01-01T10:00:00Z",
    "updated_at": "2026-03-01T12:00:00Z"
  },
  {
    "id": 5,
    "username": "reception1",
    "first_name": "Дана",
    "last_name": "Сейткали",
    "full_name": "Дана Сейткали",
    "phone_number": "+77009876543",
    "email": null,
    "role": "RECEPTIONIST",
    "role_display": "Receptionist",
    "price_per_hour": "0.00",
    "is_active": true,
    "avatar": null,
    "created_at": "2026-02-01T09:00:00Z",
    "updated_at": "2026-02-01T09:00:00Z"
  }
]
```

---

## 3. Создать сотрудника

```
POST /api/auth/staff/
```

**Auth:** ADMIN

**Body:**
```json
{
  "username": "reception2",
  "first_name": "Нуржан",
  "last_name": "Абенов",
  "phone_number": "+77771112233",
  "email": "nurzhan@grandpadel.kz",
  "role": "RECEPTIONIST",
  "price_per_hour": 0,
  "password": "SecurePass123",
  "password_confirm": "SecurePass123"
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `username` | string | ✅ | Уникальный логин для входа в CRM |
| `first_name` | string | ❌ | Имя |
| `last_name` | string | ❌ | Фамилия |
| `phone_number` | string | ❌ | Уникальный номер телефона |
| `email` | string | ❌ | Email |
| `role` | string | ✅ | Роль (см. таблицу выше, не CLIENT) |
| `price_per_hour` | decimal | ❌ | Ставка тренера ₸/час по умолчанию (для тренеров) |
| `coach_price_1_2` | decimal \| null | ❌ | Цена тренера ₸/час при 1–2 игроках |
| `coach_price_3_4` | decimal \| null | ❌ | Цена тренера ₸/час при 3–4 игроках |
| `password` | string | ✅ | Минимум 8 символов |
| `password_confirm` | string | ✅ | Должно совпасть с password |

**Response 201:**
```json
{
  "id": 12,
  "username": "reception2",
  "first_name": "Нуржан",
  "last_name": "Абенов",
  "full_name": "Нуржан Абенов",
  "phone_number": "+77771112233",
  "email": "nurzhan@grandpadel.kz",
  "role": "RECEPTIONIST",
  "role_display": "Receptionist",
  "price_per_hour": "0.00",
  "is_active": true,
  "avatar": null,
  "created_at": "2026-03-13T10:00:00Z",
  "updated_at": "2026-03-13T10:00:00Z"
}
```

**Ошибки:**
```json
{ "username": ["Пользователь с таким username уже существует."] }
{ "phone_number": ["Пользователь с таким номером уже существует."] }
{ "password_confirm": ["Пароли не совпадают."] }
{ "role": ["Нельзя создать сотрудника с ролью CLIENT."] }
```

---

## 4. Детали сотрудника

```
GET /api/auth/staff/<id>/
```

**Auth:** ADMIN

**Response 200:** объект сотрудника. Для тренеров дополнительно возвращаются `coach_price_1_2` и `coach_price_3_4` (number или null). Подробный бриф для фронта: **`docs/FRONTEND_COACH_PRICE_1_2_3_4.md`**.

---

## 5. Обновить сотрудника

```
PATCH /api/auth/staff/<id>/
```

**Auth:** ADMIN

Все поля необязательны — передавайте только то, что нужно изменить.

**Body:**
```json
{
  "first_name": "Нуржан",
  "last_name": "Абенов",
  "phone_number": "+77771112233",
  "email": "nurzhan@grandpadel.kz",
  "role": "SALES_MANAGER",
  "price_per_hour": 5000,
  "is_active": true
}
```

| Поле | Описание |
|------|----------|
| `first_name` | Изменить имя |
| `last_name` | Изменить фамилию |
| `phone_number` | Изменить телефон |
| `email` | Изменить email |
| `role` | Изменить роль (не CLIENT) |
| `price_per_hour` | Ставка тренера ₸/час по умолчанию |
| `coach_price_1_2` | Цена тренера ₸/час при 1–2 игроках (null = сбросить) |
| `coach_price_3_4` | Цена тренера ₸/час при 3–4 игроках (null = сбросить) |
| `is_active` | Активен ли аккаунт |

**Response 200:** обновлённый объект сотрудника.

**Ограничения:**
- Нельзя изменять данные другого ADMIN (`403`)
- Нельзя назначить роль `CLIENT`

---

## 6. Сменить пароль

```
POST /api/auth/staff/<id>/set-password/
```

**Auth:** ADMIN

**Body:**
```json
{
  "new_password": "NewSecurePass456",
  "new_password_confirm": "NewSecurePass456"
}
```

**Response 200:**
```json
{ "detail": "Пароль для reception2 успешно изменён." }
```

**Ошибки:**
```json
{ "new_password_confirm": ["Пароли не совпадают."] }
```

> После смены пароля сотрудник должен заново войти в CRM.

---

## 7. Активировать / деактивировать

```
POST /api/auth/staff/<id>/activate/
POST /api/auth/staff/<id>/deactivate/
```

**Auth:** ADMIN
**Body:** не требуется

**Response 200 (activate):**
```json
{ "detail": "Аккаунт reception2 активирован.", "is_active": true }
```

**Response 200 (deactivate):**
```json
{ "detail": "Аккаунт reception2 деактивирован.", "is_active": false }
```

> Деактивированный сотрудник не сможет войти в систему.
> Нельзя деактивировать другого ADMIN или собственный аккаунт.

---

## 8. Удалить аккаунт

```
DELETE /api/auth/staff/<id>/
```

**Auth:** ADMIN

**Response 204:** без тела.

**Ограничения:**
- Нельзя удалить собственный аккаунт (`400`)
- Нельзя удалить аккаунт другого ADMIN (`403`)

> **Внимание:** удаление необратимо. Рекомендуется деактивация (`deactivate`) вместо удаления, чтобы сохранить историю.

---

## 9. Бизнес-правила и ограничения

| Правило | Детали |
|---------|--------|
| Создание CLIENT | Запрещено — клиенты регистрируются сами через SMS |
| Изменение другого ADMIN | Запрещено — только свои данные |
| Удаление другого ADMIN | Запрещено |
| Деактивация своего аккаунта | Запрещено |
| Уникальность username | Проверяется при создании |
| Уникальность phone_number | Проверяется при создании и обновлении |
| Пароль тренеров | Тренеры входят через SMS, но пароль сохраняется (для будущего CRM-доступа) |
| `price_per_hour` | Актуально только для `COACH_PADEL` и `COACH_FITNESS` |

---

## Примеры использования

### Сценарий 1: Нанять нового ресепшниста

```bash
# 1. Создать аккаунт
POST /api/auth/staff/
{
  "username": "dana_r",
  "first_name": "Дана",
  "last_name": "Рахимова",
  "phone_number": "+77055001122",
  "role": "RECEPTIONIST",
  "password": "Dana2026!",
  "password_confirm": "Dana2026!"
}

# 2. Сотрудник входит в CRM
POST /api/auth/crm/login/
{
  "username": "dana_r",
  "password": "Dana2026!"
}
```

### Сценарий 2: Добавить тренера по паделу

```bash
POST /api/auth/staff/
{
  "username": "coach_arman",
  "first_name": "Арман",
  "last_name": "Сейткалиев",
  "phone_number": "+77071234567",
  "role": "COACH_PADEL",
  "price_per_hour": 8000,
  "password": "Arman2026!",
  "password_confirm": "Arman2026!"
}
# Тренер входит в приложение через SMS на +77071234567
```

### Сценарий 3: Временно заблокировать сотрудника

```bash
# Деактивировать
POST /api/auth/staff/12/deactivate/

# Восстановить доступ
POST /api/auth/staff/12/activate/
```

### Сценарий 4: Сменить роль ресепшниста на менеджера

```bash
PATCH /api/auth/staff/12/
{
  "role": "SALES_MANAGER"
}
```
