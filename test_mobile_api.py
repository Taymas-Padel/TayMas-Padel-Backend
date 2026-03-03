"""
Полный тест мобильного API.
Запуск локально: python test_mobile_api.py

По умолчанию тестит http://127.0.0.1:8000.
Для сервера можно передать BASE через переменную окружения:
  API_BASE_URL=http://213.155.23.227 python test_mobile_api.py
"""
import os
import requests
import json
import sys
import time as _time
from datetime import datetime, timedelta

BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

# Уникальные телефоны на каждый запуск (format: +77011XXXXXX, +77022XXXXXX)
_TS = str(int(_time.time()))[-6:]  # последние 6 цифр unix timestamp
PHONE1 = f"+77011{_TS}"   # 12 символов
PHONE2 = f"+77022{_TS}"   # 12 символов

TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
# Случайный час (7–19) чтобы не конфликтовать с прошлыми тестами
_HOUR = (int(_time.time()) % 13) + 7
TOMORROW_DT = f"{TOMORROW}T{_HOUR:02d}:00:00"
# 3 дня вперёд для тестов отмены (> 24ч лимит отмены)
IN3DAYS = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
_HOUR3 = (_HOUR + 1) if _HOUR < 19 else 7
IN3DAYS_DT = f"{IN3DAYS}T{_HOUR3:02d}:00:00"

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []

def check(label, condition, detail=""):
    icon = PASS if condition else FAIL
    msg = f"{icon} {label}"
    if detail:
        msg += f" | {detail}"
    print(msg)
    results.append((condition, label))
    return condition

def post(url, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{BASE}{url}", json=data, headers=headers)
    return r

def get(url, token=None, params=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{BASE}{url}", headers=headers, params=params)
    return r

def patch(url, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.patch(f"{BASE}{url}", json=data, headers=headers)
    return r

# ==================================================
print("\n" + "="*50)
print("🔐 БЛОК 1: АВТОРИЗАЦИЯ")
print("="*50)

# 1.1 Отправка кода (проверяем что эндпоинт работает, НЕ тестируем многократно из-за throttle)
r = post("/api/auth/mobile/send-code/", {"phone_number": PHONE1})
send_ok = r.status_code == 200 or r.json().get("detail", "").startswith("Запрос")
check("send-code: эндпоинт отвечает (200 или throttle)", r.status_code in (200, 429) or "Запрос" in str(r.json()), str(r.json())[:60])

# 1.2 Логин с мастер-кодом (мастер-код обходит SMS, send-code не нужен)
r = post("/api/auth/mobile/login/", {"phone_number": PHONE1, "code": "000000", "device_id": "test-dev-1"})
check("login user1: статус 200", r.status_code == 200, f"is_new={r.json().get('is_new_user')}")
T1 = r.json().get("access", "")
U1_ID = r.json().get("user_id")
check("login user1: токен получен", bool(T1))

r2 = post("/api/auth/mobile/login/", {"phone_number": PHONE2, "code": "000000", "device_id": "test-dev-2"})
check("login user2: статус 200", r2.status_code == 200)
T2 = r2.json().get("access", "")
U2_ID = r2.json().get("user_id")
check("login user2: токен получен", bool(T2))

# 1.3 Без токена должен вернуть 401/400
r = get("/api/auth/home/")
check("home без токена: не 200", r.status_code in (400, 401))

# ==================================================
print("\n" + "="*50)
print("🏠 БЛОК 2: ПРОФИЛЬ И ДАШБОРД")
print("="*50)

# 2.1 Home
r = get("/api/auth/home/", T1)
check("home: статус 200", r.status_code == 200)
d = r.json()
check("home: содержит user", "user" in d, f"elo={d.get('user',{}).get('rating_elo')}")
check("home: содержит league", "league" in d.get("user", {}))
check("home: содержит news", "news" in d)

# 2.2 Профиль (Djoser)
r = get("/api/auth/users/me/", T1)
check("profile GET: статус 200", r.status_code == 200)

r = patch("/api/auth/users/me/", {"first_name": "Азамат", "last_name": "Тест"}, T1)
check("profile PATCH: статус 200", r.status_code == 200, r.json().get("first_name",""))

# 2.3 Stats
r = get("/api/auth/me/stats/", T1)
check("me/stats: статус 200", r.status_code == 200)

# 2.4 Лига
r = get("/api/auth/me/league/", T1)
check("me/league: статус 200", r.status_code == 200)

# 2.5 Тренеры
r = get("/api/auth/coaches/", T1)
check("coaches: статус 200", r.status_code == 200)

# ==================================================
print("\n" + "="*50)
print("🏟️  БЛОК 3: КОРТЫ")
print("="*50)

r = get("/api/courts/", T1)
check("courts list: статус 200", r.status_code == 200)
courts = r.json()
check("courts: есть данные", len(courts) > 0, f"count={len(courts)}")
COURT_ID = courts[0]["id"] if courts else None
COURT_NAME = courts[0]["name"] if courts else "?"
print(f"  → Используем корт: #{COURT_ID} {COURT_NAME}")

r = get(f"/api/courts/{COURT_ID}/", T1)
check("court detail: статус 200", r.status_code == 200, r.json().get("name",""))

# Проверка доступности через bookings
r = get("/api/bookings/check-availability/", T1, params={"court_id": COURT_ID, "date": TOMORROW, "duration": 90})
check("check-availability: статус 200", r.status_code == 200, str(r.json())[:80])

# ==================================================
print("\n" + "="*50)
print("📅 БЛОК 4: БРОНИРОВАНИЯ")
print("="*50)

# 4.1 Список броней
r = get("/api/bookings/", T1)
check("my bookings: статус 200", r.status_code == 200)

# 4.2 Создание брони (API поля: start_time, duration)
r = post("/api/bookings/create/", {
    "court": COURT_ID,
    "start_time": TOMORROW_DT,
    "duration": 90,
    "payment_method": "CASH"
}, T1)
check("create booking: статус 201", r.status_code == 201, f"id={r.json().get('id')} status={r.json().get('status')}")
BOOKING_ID = r.json().get("id")

if BOOKING_ID:
    # 4.3 Деталь брони
    r = get(f"/api/bookings/{BOOKING_ID}/", T1)
    check("booking detail: статус 200", r.status_code == 200, f"status={r.json().get('status')}")

    # 4.4 Отмена — создаём отдельную бронь на 3 дня вперёд (> 24ч лимит)
    r_cancel = post("/api/bookings/create/", {
        "court": COURT_ID, "start_time": IN3DAYS_DT, "duration": 90, "payment_method": "CASH"
    }, T1)
    CANCEL_BID = r_cancel.json().get("id")
    r = post(f"/api/bookings/{CANCEL_BID}/cancel/", {}, T1)
    check("cancel booking: статус 200", r.status_code == 200, r.json().get("status",""))

# 4.5 История
r = get("/api/bookings/history/", T1)
check("booking history: статус 200", r.status_code == 200)

# 4.6 Price preview (API поля: court_id, start_time, duration_minutes)
r = post("/api/bookings/price-preview/", {
    "court_id": COURT_ID,
    "start_time": TOMORROW_DT,
    "duration_minutes": 90,
}, T1)
check("price preview: статус 200", r.status_code == 200, f"total={r.json().get('total')}")

# ==================================================
print("\n" + "="*50)
print("🎟️  БЛОК 5: АБОНЕМЕНТЫ")
print("="*50)

r = get("/api/memberships/", T1)
check("memberships list: статус 200", r.status_code == 200, f"count={len(r.json())}")
memberships_data = r.json()
# Типы — по /api/memberships/types/
r_types = get("/api/memberships/types/", T1)
check("membership types: статус 200", r_types.status_code == 200, f"count={len(r_types.json())}")
mem_types = r_types.json()
MEMBERSHIP_TYPE_ID = mem_types[0]["id"] if mem_types else None

r = get("/api/memberships/my/", T1)
check("my memberships: статус 200", r.status_code == 200)

if MEMBERSHIP_TYPE_ID:
    r = post(f"/api/memberships/buy/{MEMBERSHIP_TYPE_ID}/", {"payment_method": "CASH"}, T1)
    check("buy membership: статус in (200,201)", r.status_code in (200, 201), str(r.json())[:80])

# ==================================================
print("\n" + "="*50)
print("🏆 БЛОК 6: ГЕЙМИФИКАЦИЯ")
print("="*50)

r = get("/api/gamification/matches/", T1)
check("matches: статус 200", r.status_code == 200)

r = get("/api/gamification/leaderboard/", T1)
check("leaderboard: статус 200", r.status_code == 200, f"count={len(r.json())}")

# ==================================================
print("\n" + "="*50)
print("👥 БЛОК 7: ДРУЗЬЯ")
print("="*50)

r = get("/api/friends/", T1)
check("friends list: статус 200", r.status_code == 200)

r = get("/api/friends/feed/", T1)
check("friends feed: статус 200", r.status_code == 200)

r = get("/api/friends/requests/", T1)
check("friend requests: статус 200", r.status_code == 200)

# ==================================================
print("\n" + "="*50)
print("🔔 БЛОК 8: УВЕДОМЛЕНИЯ")
print("="*50)

r = get("/api/notifications/", T1)
check("notifications: статус 200", r.status_code == 200)

r = get("/api/notifications/unread-count/", T1)
check("unread count: статус 200", r.status_code == 200, f"count={r.json().get('count',r.json())}")

# ==================================================
print("\n" + "="*50)
print("🎮 БЛОК 9: ЛОББИ (главная фича)")
print("="*50)

# 9.1 Создание лобби без корта и времени
r = post("/api/lobby/", {
    "title": "Тест лобби 2x2",
    "game_format": "DOUBLE",
    "elo_min": 1000,
    "elo_max": 1400,
    "comment": "Test lobby"
}, T1)
check("create lobby: статус 201", r.status_code == 201, f"id={r.json().get('id')} status={r.json().get('status')}")
lb = r.json()
LOBBY_ID = lb.get("id")
check("lobby: нет court при создании", lb.get("court") is None)
check("lobby: нет scheduled_time при создании", lb.get("scheduled_time") is None)
check("lobby: статус OPEN", lb.get("status") == "OPEN")
check("lobby: elo_min/max заданы", lb.get("elo_min") and lb.get("elo_max"))

# 9.2 Список лобби с ELO фильтром
r = get("/api/lobby/", T1, params={"elo": 1200})
check("lobby list с ELO: статус 200", r.status_code == 200, f"count={len(r.json())}")

# 9.3 Присоединение user2
if LOBBY_ID:
    r = post(f"/api/lobby/{LOBBY_ID}/join/", {}, T2)
    check("join lobby user2: статус 200", r.status_code == 200, r.json().get("status",""))

    # 9.4 Мои лобби
    r = get("/api/lobby/my/", T1)
    check("my lobbies: статус 200", r.status_code == 200, f"count={len(r.json())}")

    # 9.5 Деталь лобби
    r = get(f"/api/lobby/{LOBBY_ID}/", T1)
    check("lobby detail: статус 200", r.status_code == 200, f"players={r.json().get('current_players_count')}")

    # 9.6 Попытка предложить время когда лобби неполное
    r = post(f"/api/lobby/{LOBBY_ID}/proposals/", {
        "court": COURT_ID,
        "scheduled_time": TOMORROW_DT,
        "duration_minutes": 90
    }, T1)
    check("propose time при неполном лобби: 400", r.status_code == 400, r.json().get("detail","")[:50])

    # 9.7 Покинуть лобби
    r = post(f"/api/lobby/{LOBBY_ID}/leave/", {}, T2)
    check("leave lobby: статус 200", r.status_code == 200)

# ==================================================
print("\n" + "="*50)
print("💳 БЛОК 10: ПЛАТЁЖНЫЕ СЕССИИ")
print("="*50)

# PaymentStatus view
r = get("/api/payments/session/00000000-0000-0000-0000-000000000000/status/", T1)
check("payment session status: не 500", r.status_code != 500, f"got {r.status_code}")

# ==================================================
print("\n" + "="*50)
print("🔍 БЛОК 11: ПОИСК ПОЛЬЗОВАТЕЛЕЙ")
print("="*50)

r = get("/api/auth/search/", T1, params={"q": "77"})
check("user search: статус 200", r.status_code == 200)

r = get(f"/api/auth/users/{U2_ID}/profile/", T1)
check("public profile: статус 200", r.status_code == 200)

# ==================================================
print("\n" + "="*50)
print("📊 ИТОГ")
print("="*50)
passed = sum(1 for ok, _ in results if ok)
failed = sum(1 for ok, _ in results if not ok)
total = len(results)
print(f"\n{PASS} Прошло: {passed}/{total}")
if failed:
    print(f"{FAIL} Упало: {failed}/{total}")
    print("\nФейлы:")
    for ok, label in results:
        if not ok:
            print(f"  {FAIL} {label}")
else:
    print("Все тесты прошли! 🎉")

sys.exit(0 if failed == 0 else 1)
