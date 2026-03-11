#!/usr/bin/env bash
# Добавляет все тарифы абонементов из прайс-листа GRAND PADEL TAYMAS.
# Использование:
#   export BASE_URL="http://localhost:8000"   # или https://your-api.com
#   export TOKEN="your-jwt-token"             # от ресепшн/админа
#   bash scripts/add_all_membership_tariffs.sh

set -e
BASE_URL="${BASE_URL:-http://213.155.23.227}"
API="${BASE_URL}/api/memberships/types/manage/"

if [ -z "$TOKEN" ]; then
  echo "Укажите JWT: export TOKEN=\"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzczMzIyOTM0LCJpYXQiOjE3NzMyMzY1MzQsImp0aSI6IjgwNjQ0ZmVhMTIwNTQ3ODM4ZGJiZGFlMzZlNjZmZjZmIiwidXNlcl9pZCI6IjEifQ.G50J9WLLdPEM3dk1-p3s__FZQcZIFiqp90yBgyNvOCQ"
  exit 1
fi

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Пакет 8 часов",
  "description": "Пакет 8 часов. Приоритетное время 06:00-15:00. Прайм-тайм (15:00-22:00) +4000₸/час.",
  "service_type": "PADEL_HOURS",
  "price": 128000,
  "days_valid": 30,
  "total_hours": 8,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00",
  "prime_time_surcharge": 4000,
  "min_participants": 1,
  "max_participants": 4,
  "includes_coach": false
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Пакет 12 часов",
  "description": "Пакет 12 часов. Приоритетное время 06:00-15:00. Прайм-тайм (15:00-22:00) +4000₸/час.",
  "service_type": "PADEL_HOURS",
  "price": 192000,
  "days_valid": 30,
  "total_hours": 12,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00",
  "prime_time_surcharge": 4000,
  "min_participants": 1,
  "max_participants": 4,
  "includes_coach": false
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Тренировки 1-2 чел (6 часов)",
  "description": "Пакет тренировок 1-2 человека. Корт и тренер включены.",
  "service_type": "TRAINING_HOURS",
  "price": 120000,
  "days_valid": 30,
  "total_hours": 6,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00",
  "prime_time_surcharge": 0,
  "min_participants": 1,
  "max_participants": 2,
  "includes_coach": true
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Тренировки 1-2 чел (8 часов)",
  "description": "Пакет тренировок 1-2 человека. Корт и тренер включены.",
  "service_type": "TRAINING_HOURS",
  "price": 160000,
  "days_valid": 30,
  "total_hours": 8,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00",
  "prime_time_surcharge": 0,
  "min_participants": 1,
  "max_participants": 2,
  "includes_coach": true
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Тренировки 3-4 чел (6 часов)",
  "description": "Пакет тренировок 3-4 человека. Корт и тренер включены.",
  "service_type": "TRAINING_HOURS",
  "price": 180000,
  "days_valid": 30,
  "total_hours": 6,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00",
  "prime_time_surcharge": 0,
  "min_participants": 3,
  "max_participants": 4,
  "includes_coach": true
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Тренировки 3-4 чел (8 часов)",
  "description": "Пакет тренировок 3-4 человека. Корт и тренер включены.",
  "service_type": "TRAINING_HOURS",
  "price": 240000,
  "days_valid": 30,
  "total_hours": 8,
  "priority_time_start": "06:00",
  "priority_time_end": "15:00",
  "prime_time_surcharge": 0,
  "min_participants": 3,
  "max_participants": 4,
  "includes_coach": true
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Фитнес 3 месяца",
  "description": "Полноценный доступ к фитнес-инфраструктуре клуба на 3 месяца.",
  "service_type": "GYM",
  "price": 150000,
  "days_valid": 90
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Фитнес 6 месяцев",
  "description": "Полноценный доступ к фитнес-инфраструктуре клуба на 6 месяцев.",
  "service_type": "GYM",
  "price": 240000,
  "days_valid": 180
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "Фитнес 12 месяцев",
  "description": "Полноценный доступ к фитнес-инфраструктуре клуба на 12 месяцев.",
  "service_type": "GYM",
  "price": 420000,
  "days_valid": 365
}' && echo ""

curl -s -X POST "$API" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "name": "VIP раздевалка + фитнес 12 месяцев",
  "description": "Фитнес зал + member падела. Индивидуальный шкафчик, зона отдыха, сауна. 12 мес.",
  "service_type": "VIP",
  "price": 1000000,
  "days_valid": 365,
  "discount_on_court": 10
}' && echo ""

echo "Готово: добавлено 10 типов абонементов."
