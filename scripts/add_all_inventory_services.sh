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

# 1. Аренда ракетки
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Аренда ракетки (за игру)",
  "price": 3000,
  "is_active": true
}' && echo ""

# 2. Мячи (упаковка)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Мячи (упаковка, за игру)",
  "price": 3500,
  "is_active": true
}' && echo ""

# 3. Функциональная подготовка — индивидуально
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Функциональная подготовка падел — индивидуальная, 1 час",
  "price": 15000,
  "is_active": true
}' && echo ""

# 4. Функциональная подготовка — группа до 6
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Функциональная подготовка падел — группа до 6 чел, 1 час",
  "price": 45000,
  "is_active": true
}' && echo ""

# 5. Турнир — участие
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Участие в турнире (1 человек)",
  "price": 12000,
  "is_active": true
}' && echo ""

# 6. Сквош — аренда корта 1 час
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Сквош — аренда корта 1 час",
  "price": 10000,
  "is_active": true
}' && echo ""

# 7. Настольный теннис — 1 час
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Настольный теннис — 1 час",
  "price": 5000,
  "is_active": true
}' && echo ""

# 8. Recovery — первичная консультация
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Recovery — первичная консультация",
  "price": 10000,
  "is_active": true
}' && echo ""

# 9. Recovery — диагностика (базовая)
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Recovery — функциональная диагностика (от 15 000)",
  "price": 15000,
  "is_active": true
}' && echo ""

# 10. Лечебный массаж — 1 час
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Лечебный массаж — 1 час",
  "price": 15000,
  "is_active": true
}' && echo ""

# 11. Спортивный массаж — 1 час
curl -s -X POST "$API" -H "$hdr_auth" -H "$hdr_json" -d '{
  "name": "Спортивный массаж — 1 час",
  "price": 18000,
  "is_active": true
}' && echo ""

echo "Готово: добавлены услуги / инвентарь из прайса."

