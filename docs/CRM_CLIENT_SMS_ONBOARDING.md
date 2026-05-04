# CRM: Добавление клиента по номеру через SMS

Документ для CRM-фронта (Web), чтобы реализовать сценарий:

1. Ввести номер клиента  
2. Отправить SMS-код  
3. Подтвердить код  
4. Получить `user_id` нового клиента и продолжить работу в CRM

---

## Базовые условия

- Base URL: `http://213.155.23.227/api`
- Формат: `application/json`
- CRM токен нужен для CRM-эндпоинтов (`/api/auth/reception/...`, `/api/auth/clients/...`)
- Для SMS шагов используются мобильные auth-эндпоинты:
  - `POST /api/auth/mobile/send-code/`
  - `POST /api/auth/mobile/login/`

---

## Полный flow

## Шаг 1. Проверить, есть ли клиент в базе

### Endpoint
`GET /api/auth/reception/search/?phone=<номер_или_часть>`

### Headers
`Authorization: Bearer <crm_access_token>`

### Пример
`GET /api/auth/reception/search/?phone=77001234567`

### Успех (200)
```json
[
  {
    "id": 42,
    "phone_number": "+77001234567",
    "first_name": "Азамат",
    "last_name": "Есимханулы",
    "role": "CLIENT"
  }
]
```

### Логика фронта
- Если массив **не пустой**: клиент уже существует, использовать его `id`.
- Если массив **пустой**: запускать SMS flow (шаг 2).

---

## Шаг 2. Отправить SMS-код

### Endpoint
`POST /api/auth/mobile/send-code/`

### Body
```json
{
  "phone_number": "+77001234567"
}
```

### Успех (200)
```json
{
  "message": "Код отправлен",
  "phone": "+77001234567"
}
```

### Ошибки
- `400`: неверный формат номера
- `429`: слишком много попыток, временная блокировка

---

## Шаг 3. Подтвердить код и создать клиента

### Endpoint
`POST /api/auth/mobile/login/`

### Body
```json
{
  "phone_number": "+77001234567",
  "code": "123456",
  "device_id": "crm-reception-web-v1"
}
```

### Успех (200)
```json
{
  "refresh": "eyJ...",
  "access": "eyJ...",
  "is_new_user": true,
  "is_profile_complete": false,
  "role": "CLIENT",
  "user_id": 123,
  "is_qr_blocked": false
}
```

### Что важно
- Если `is_new_user=true`, клиент создан только что.
- Всегда использовать `user_id` из ответа как ID клиента для CRM операций.
- `device_id` обязателен.

### Ошибки
- `400`: код неверный/истек/данные невалидны
- `429`: превышен лимит попыток
- `403`: у пользователя роль, которой запрещен SMS логин

---

## Шаг 4. Открыть карточку клиента в CRM

После успешного шага 3:

### Endpoint
`GET /api/auth/reception/user/<user_id>/`

### Headers
`Authorization: Bearer <crm_access_token>`

### Пример
`GET /api/auth/reception/user/123/`

---

## Рекомендуемый UX для CRM

1. Поле ввода номера
2. Кнопка "Найти"
3. Если клиент не найден:
   - показать кнопку "Отправить код"
4. После отправки:
   - показать поле "Введите код"
5. После успешной верификации:
   - показать "Клиент добавлен"
   - открыть карточку клиента
   - подставить клиента в текущий бизнес-процесс (бронь, абонемент и т.д.)

---

## Готовая схема интеграции (псевдологика)

```text
search(phone) ->
  if found:
    select existing client
  else:
    send-code(phone) ->
    verify-code(phone, code, device_id) ->
      user_id ->
      open CRM user card ->
      continue with booking/membership flow
```

---

## Важные замечания

- CRM-фронт продолжает работать со своим CRM токеном.
- Токены из `mobile/login` не обязательны для хранения в CRM, если нужен только факт создания клиента.
- Для номера использовать единый формат (`+7700...`) на фронте до отправки.
- Если пришел `429`, показывать понятный текст: "Слишком много попыток, попробуйте позже".

