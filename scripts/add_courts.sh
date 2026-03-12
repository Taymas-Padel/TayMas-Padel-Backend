#!/usr/bin/env bash
# Создаёт все корты GRAND PADEL TAYMAS по тарифной системе клуба.
#
# Корты:
#   Panoramic Indoor  x5  (TWO_VS_TWO) — 06:00-08:00: 10000 / 08:00-00:00: 18000
#   Panoramic Outdoor x4  (TWO_VS_TWO) — 06:00-08:00: 10000 / 08:00-00:00: 18000
#   Single Indoor     x1  (ONE_VS_ONE) — 06:00-00:00: 16000
#
# Использование:
#   export BASE_URL="http://localhost:8000"   # или http://213.155.23.227
#   export TOKEN="your-admin-jwt-token"
#   bash scripts/add_courts.sh

set -e

BASE_URL="${BASE_URL:-http://213.155.23.227}"
COURTS_API="${BASE_URL}/api/courts/manage/"

if [ -z "$TOKEN" ]; then
  echo "❌ Укажите JWT администратора: export TOKEN=\"...\""
  exit 1
fi

H_AUTH="Authorization: Bearer $TOKEN"
H_JSON="Content-Type: application/json"
TMPFILE=$(mktemp)

echo "🎾 Создаём корты GRAND PADEL TAYMAS → ${COURTS_API}"
echo "=================================================="

# ──────────────────────────────────────────────────────────────
# create_court name court_type play_format base_price description
# Выводит ID созданного корта в stdout (последняя строка).
# ──────────────────────────────────────────────────────────────
create_court(){
  local name="$1" court_type="$2" play_format="$3" base_price="$4" description="$5"

  echo ""
  echo "▶ Создаём: ${name} [${play_format}]"

  HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TMPFILE" \
    -X POST "$COURTS_API" \
    -H "$H_AUTH" -H "$H_JSON" \
    -d "{
      \"name\": \"${name}\",
      \"court_type\": \"${court_type}\",
      \"play_format\": \"${play_format}\",
      \"price_per_hour\": ${base_price},
      \"description\": \"${description}\",
      \"is_active\": true
    }")

  BODY=$(cat "$TMPFILE")

  if [ "$HTTP_CODE" -ne 201 ]; then
    echo "  ⚠️  Статус ${HTTP_CODE}: ${BODY}"
    echo ""
    return 1
  fi

  COURT_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  echo "  ✅ Создан ID=${COURT_ID}"
  echo "$COURT_ID"
}

add_price_slot(){
  local court_id="$1" start_time="$2" end_time="$3" price="$4"

  HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TMPFILE" \
    -X POST "${BASE_URL}/api/courts/manage/${court_id}/price-slots/" \
    -H "$H_AUTH" -H "$H_JSON" \
    -d "{
      \"start_time\": \"${start_time}\",
      \"end_time\": \"${end_time}\",
      \"price_per_hour\": ${price}
    }")

  BODY=$(cat "$TMPFILE")

  if [ "$HTTP_CODE" -ne 201 ]; then
    echo "    ⚠️  Слот ${start_time}–${end_time}: статус ${HTTP_CODE}: ${BODY}"
  else
    SLOT_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    echo "    💰 Слот ${start_time}–${end_time} = ${price}₸/ч (ID=${SLOT_ID})"
  fi
}

# ══════════════════════════════════════════════════════════════
# PANORAMIC INDOOR (5 штук)
# ══════════════════════════════════════════════════════════════
echo ""
echo "━━━ Panoramic Indoor (5 шт.) ━━━"
for i in 1 2 3 4 5; do
  OUTPUT=$(create_court \
    "Panoramic Indoor ${i}" \
    "PANORAMIC" \
    "TWO_VS_TWO" \
    "18000" \
    "Панорамный крытый корт. Формат 2x2. Утренняя скидка 06:00–08:00.")

  echo "$OUTPUT"
  ID=$(echo "$OUTPUT" | tail -1)

  if echo "$ID" | grep -qE '^[0-9]+$'; then
    add_price_slot "$ID" "06:00:00" "08:00:00" 10000
    add_price_slot "$ID" "08:00:00" "00:00:00" 18000
  fi
done

# ══════════════════════════════════════════════════════════════
# PANORAMIC OUTDOOR (4 штуки)
# ══════════════════════════════════════════════════════════════
echo ""
echo "━━━ Panoramic Outdoor (4 шт.) ━━━"
for i in 1 2 3 4; do
  OUTPUT=$(create_court \
    "Panoramic Outdoor ${i}" \
    "OUTDOOR" \
    "TWO_VS_TWO" \
    "18000" \
    "Панорамный открытый корт. Формат 2x2. Утренняя скидка 06:00–08:00.")

  echo "$OUTPUT"
  ID=$(echo "$OUTPUT" | tail -1)

  if echo "$ID" | grep -qE '^[0-9]+$'; then
    add_price_slot "$ID" "06:00:00" "08:00:00" 10000
    add_price_slot "$ID" "08:00:00" "00:00:00" 18000
  fi
done

# ══════════════════════════════════════════════════════════════
# SINGLE INDOOR (1 штука)
# ══════════════════════════════════════════════════════════════
echo ""
echo "━━━ Single Indoor (1 шт.) ━━━"
OUTPUT=$(create_court \
  "Single Indoor 1" \
  "INDOOR" \
  "ONE_VS_ONE" \
  "16000" \
  "Тренировочный корт. Формат 1x1. Услуги тренера оплачиваются отдельно.")

echo "$OUTPUT"
ID=$(echo "$OUTPUT" | tail -1)

if echo "$ID" | grep -qE '^[0-9]+$'; then
  add_price_slot "$ID" "06:00:00" "00:00:00" 16000
fi

rm -f "$TMPFILE"

echo ""
echo "=================================================="
echo "✅ Готово! Создано 10 кортов с ценовыми слотами."
echo ""
echo "Проверить: GET ${BASE_URL}/api/courts/"
