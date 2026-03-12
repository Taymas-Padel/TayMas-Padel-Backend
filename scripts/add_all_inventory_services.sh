#!/usr/bin/env bash
# Добавляет все услуги / инвентарь из прайс-листа GRAND PADEL TAYMAS.
# Использование:
#   export BASE_URL="http://localhost:8000"   # или https://your-api.com
#   export TOKEN="your-admin-jwt-token"       # JWT пользователя с ролью ADMIN
#   bash scripts/add_all_inventory_services.sh

set -e

BASE_URL="${BASE_URL:-http://213.155.23.227}"
API="${BASE_URL}/api/inventory/services/manage/"

if [ -z "$TOKEN" ]; then
  echo "Укажите JWT администратора: export TOKEN=\"...\""
  exit 1
fi

hdr_auth="Authorization: Bearer $TOKEN"
hdr_json="Content-Type: application/json"

echo "Добавляем услуги / инвентарь в ${API}"

# 1. Аренда ракетки (Падел, инвентарь)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Аренда ракетки (за игру)",
  "description": "Прокат ракетки для падела на время игры.",
  "price": 3000,
  "group": "PADEL",
  "category": "INVENTORY",
  "is_active": true
}' && echo ""

# 2. Мячи (упаковка) — Падел, инвентарь
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Мячи (упаковка, за игру)",
  "description": "Набор мячей для падела на одну игровую сессию.",
  "price": 3500,
  "group": "PADEL",
  "category": "INVENTORY",
  "is_active": true
}' && echo ""

# 3. Функциональная подготовка — индивидуально (Падел, услуга)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Функциональная подготовка падел — индивидуальная, 1 час",
  "description": "Индивидуальная нагрузка и ОФП под падел, 1 час.",
  "price": 15000,
  "group": "PADEL",
  "category": "SERVICE",
  "is_active": true
}' && echo ""

# 4. Функциональная подготовка — группа до 6 (Падел, услуга)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Функциональная подготовка падел — группа до 6 чел, 1 час",
  "description": "Групповое занятие по ОФП под падел до 6 человек.",
  "price": 45000,
  "group": "PADEL",
  "category": "SERVICE",
  "is_active": true
}' && echo ""

# 5. Турнир — участие (Падел, событие)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Участие в турнире (1 человек)",
  "description": "Стартовый взнос участника турнира по паделу.",
  "price": 12000,
  "group": "PADEL",
  "category": "EVENT",
  "is_active": true
}' && echo ""

# 6. Recovery — первичная консультация (Recovery, услуга)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Recovery — первичная консультация",
  "description": "Первичный приём специалиста Recovery.",
  "price": 10000,
  "group": "RECOVERY",
  "category": "SERVICE",
  "is_active": true
}' && echo ""

# 7. Recovery — диагностика (базовая) (Recovery, услуга)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Recovery — функциональная диагностика (от 15 000)",
  "description": "Базовая функциональная диагностика, цена может варьироваться.",
  "price": 15000,
  "group": "RECOVERY",
  "category": "SERVICE",
  "is_active": true
}' && echo ""

# 8. Лечебный массаж — 1 час (Recovery, услуга)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Лечебный массаж — 1 час",
  "description": "Лечебный массаж, 1 час.",
  "price": 15000,
  "group": "RECOVERY",
  "category": "SERVICE",
  "is_active": true
}' && echo ""

# 9. Спортивный массаж — 1 час (Recovery, услуга)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Спортивный массаж — 1 час",
  "description": "Спортивный массаж для восстановления после нагрузок.",
  "price": 18000,
  "group": "RECOVERY",
  "category": "SERVICE",
  "is_active": true
}' && echo ""

echo "Готово: добавлены услуги / инвентарь из прайса."

