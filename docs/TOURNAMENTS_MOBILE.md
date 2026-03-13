# Турниры — документация для Flutter (мобильное приложение)

**Base URL:** `/api/tournaments/`

---

## Оглавление

1. [Список турниров](#1-список-турниров)
2. [Детали турнира](#2-детали-турнира)
3. [Регистрация на турнир](#3-регистрация-на-турнир)
4. [Просмотр команд](#4-просмотр-команд)
5. [Сетка турнира](#5-сетка-турнира)
6. [Матчи](#6-матчи)
7. [Мои матчи](#7-мои-матчи)
8. [Оплата участия](#8-оплата-участия)
9. [Dart-модели](#9-dart-модели)
10. [Сценарий участника — полный flow](#10-сценарий-участника--полный-flow)
11. [Push-уведомления](#11-push-уведомления)

---

## 1. Список турниров

```
GET /api/tournaments/
```

**Auth:** None (публичный)

**Query params:**
- `?status=REGISTRATION` — только открытые для регистрации
- `?status=IN_PROGRESS` — текущие
- `?status=COMPLETED` — завершённые
- `?format=DOUBLES` — парный

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "Grand Padel Cup 2026",
    "start_date": "2026-04-15T10:00:00Z",
    "end_date": "2026-04-15T20:00:00Z",
    "registration_deadline": "2026-04-10T23:59:00Z",
    "status": "REGISTRATION",
    "format": "DOUBLES",
    "is_paid": true,
    "entry_fee": "12000.00",
    "max_teams": 16,
    "teams_count": 8,
    "paid_teams_count": 5,
    "created_at": "2026-03-01T10:00:00Z"
  }
]
```

### UX-подсказки для Flutter

| `status` | Отображение | Цвет бейджа |
|----------|-------------|-------------|
| `DRAFT` | скрыть от пользователя | — |
| `REGISTRATION` | "Идёт регистрация" | зелёный |
| `IN_PROGRESS` | "Турнир идёт 🔥" | оранжевый |
| `COMPLETED` | "Завершён" | серый |
| `CANCELED` | "Отменён" | красный |

---

## 2. Детали турнира

```
GET /api/tournaments/<id>/
```

**Auth:** None

**Response 200:**
```json
{
  "id": 1,
  "name": "Grand Padel Cup 2026",
  "description": "Открытый турнир клуба. Single Elimination.",
  "start_date": "2026-04-15T10:00:00Z",
  "end_date": "2026-04-15T20:00:00Z",
  "registration_deadline": "2026-04-10T23:59:00Z",
  "status": "REGISTRATION",
  "format": "DOUBLES",
  "is_paid": true,
  "entry_fee": "12000.00",
  "max_teams": 16,
  "prize_info": "1 место — 100 000₸, 2 место — 50 000₸",
  "teams_count": 8,
  "paid_teams_count": 5,
  "created_by": 1,
  "created_by_info": { "id": 1, "name": "Grand Padel Admin", "phone": null },
  "created_at": "2026-03-01T10:00:00Z",
  "updated_at": "2026-03-10T15:00:00Z"
}
```

### Что показывать на экране деталей

```
┌─────────────────────────────────┐
│  Grand Padel Cup 2026           │
│  [Идёт регистрация 🟢]          │
│                                 │
│  📅 15 апреля 2026              │
│  🏆 Парный падел (2x2)          │
│  💰 Взнос: 12 000 ₸             │
│  👥 Команды: 8 / 16             │
│  🏅 Призы: 1 место — 100 000 ₸  │
│                                 │
│  Дедлайн регистрации: 10 апр    │
│                                 │
│  [Зарегистрироваться]           │
└─────────────────────────────────┘
```

**Кнопка "Зарегистрироваться"** показывается только если:
- `status == "REGISTRATION"`
- `teams_count < max_teams` (или max_teams null)

---

## 3. Регистрация на турнир

```
POST /api/tournaments/<id>/teams/
```

**Auth:** Required

### Парный формат (DOUBLES)

```json
{
  "player1_id": 42,
  "player2_id": 15,
  "team_name": "Dream Team"
}
```

> `player1_id` — текущий пользователь (или любой из пары).
> `player2_id` — напарник (выбрать из списка друзей).
> `team_name` — опционально.

### Одиночный формат (SINGLES)

```json
{
  "player1_id": 42
}
```

**Response 201:**
```json
{
  "id": 3,
  "tournament": 1,
  "display_name": "Азамат / Данияр",
  "status": "PENDING",
  "registered_at": "2026-03-13T10:00:00Z",
  ...
}
```

**Ошибки:**
```json
{ "non_field_errors": ["Регистрация на этот турнир закрыта."] }
{ "non_field_errors": ["Достигнут лимит команд в турнире."] }
{ "non_field_errors": ["Игрок 1 уже зарегистрирован в этом турнире."] }
{ "non_field_errors": ["Для парного формата нужен второй игрок."] }
```

### После регистрации

Показать пользователю:
```
✅ Заявка отправлена!

Статус: Ожидает подтверждения

Если турнир платный (12 000 ₸):
→ Оплатите участие на ресепшене клуба,
  чтобы попасть в турнирную сетку.
```

---

## 4. Просмотр команд

```
GET /api/tournaments/<id>/teams/
```

**Auth:** None

Показывает все команды с их статусами — используется для экрана "Участники" и для проверки зарегистрирован ли текущий пользователь.

**Как проверить, участвует ли текущий пользователь:**
```dart
bool isRegistered(List<TournamentTeam> teams, int myUserId) {
  return teams.any((t) =>
    t.player1Info?.id == myUserId || t.player2Info?.id == myUserId
  );
}

TournamentTeam? myTeam(List<TournamentTeam> teams, int myUserId) {
  return teams.firstWhereOrNull((t) =>
    t.player1Info?.id == myUserId || t.player2Info?.id == myUserId
  );
}
```

---

## 5. Сетка турнира

```
GET /api/tournaments/<id>/bracket/
```

**Auth:** None

**Response 200:**
```json
{
  "tournament_id": 1,
  "total_rounds": 3,
  "rounds": [
    {
      "round_number": 1,
      "round_name": "1/4 финала",
      "matches": [
        {
          "id": 1,
          "round_number": 1,
          "round_name": "1/4 финала",
          "match_number": 1,
          "team1_info": {
            "id": 3,
            "display_name": "Азамат / Данияр",
            "status": "PAID",
            "seed": 1,
            "player1_info": { "id": 42, "name": "Азамат Есимханулы", "phone": "+77001234567" },
            "player2_info": { "id": 15, "name": "Данияр Сейткали", "phone": "+77009876543" }
          },
          "team2_info": {
            "id": 5,
            "display_name": "Серик / Асхат",
            "status": "PAID",
            "seed": 4,
            "player1_info": { ... },
            "player2_info": { ... }
          },
          "winner": null,
          "winner_info": null,
          "court": 1,
          "court_name": "Panoramic Indoor 1",
          "scheduled_at": "2026-04-15T10:00:00Z",
          "status": "SCHEDULED",
          "score_team1": "",
          "score_team2": "",
          "next_match": 5
        }
      ]
    },
    {
      "round_number": 2,
      "round_name": "Полуфинал",
      "matches": [ ... ]
    },
    {
      "round_number": 3,
      "round_name": "Финал",
      "matches": [ ... ]
    }
  ]
}
```

### Как рендерить сетку в Flutter

```dart
// Упрощённый подход — горизонтальный скролл по раундам
ListView(
  scrollDirection: Axis.horizontal,
  children: bracket.rounds.map((round) =>
    Column(
      children: [
        Text(round.roundName, style: titleStyle),
        ...round.matches.map((match) => MatchCard(match: match)),
      ],
    )
  ).toList(),
)
```

**Выделение своей команды:**
```dart
bool isMyMatch(TournamentMatch match, int myUserId) {
  final t1ids = [match.team1Info?.player1Info?.id, match.team1Info?.player2Info?.id];
  final t2ids = [match.team2Info?.player1Info?.id, match.team2Info?.player2Info?.id];
  return t1ids.contains(myUserId) || t2ids.contains(myUserId);
}
```

---

## 6. Матчи

```
GET /api/tournaments/<id>/matches/
```

**Auth:** None

**Query params:**
- `?date=2026-04-15`
- `?court_id=1`
- `?status=SCHEDULED`

Используется для экрана "Расписание матчей".

---

## 7. Мои матчи

```
GET /api/tournaments/<id>/my-matches/
```

**Auth:** Required

Возвращает только матчи, в которых участвует текущий пользователь.

**Response 200:** массив объектов `TournamentMatch` (тот же формат что и `/matches/`).

### Что показывать

```
┌─────────────────────────────────┐
│  Мои матчи                      │
├─────────────────────────────────┤
│  1/4 финала                     │
│  📅 15 апр, 10:00               │
│  📍 Panoramic Indoor 1          │
│  🆚 Серик / Асхат               │
│  Статус: Запланирован           │
├─────────────────────────────────┤
│  Полуфинал                      │
│  📅 15 апр, 13:00               │
│  📍 TBD                         │
│  🆚 TBD (победитель матча #3)   │
└─────────────────────────────────┘
```

Для статуса `COMPLETED` — показать счёт и победителя.

---

## 8. Оплата участия

На первом этапе — упрощённая схема (оплата на ресепшене):

```
Если tournament.is_paid == true И team.status != "PAID":
  Показать блок:
  ┌─────────────────────────────────┐
  │  💳 Оплата взноса               │
  │                                 │
  │  Сумма: 12 000 ₸                │
  │  Статус: Ожидает оплаты         │
  │                                 │
  │  Обратитесь на ресепшен клуба   │
  │  для оплаты участия.            │
  │  После оплаты статус изменится  │
  │  на «Оплачен» и вы попадёте     │
  │  в турнирную сетку.             │
  └─────────────────────────────────┘

Если team.status == "PAID":
  ✅ Взнос оплачен — вы в сетке!
```

**Статус команды** нужно периодически проверять (poll или push):
```dart
// Проверить статус своей команды
final teams = await api.getTournamentTeams(tournamentId);
final myTeam = teams.firstWhereOrNull((t) => t.player1Info?.id == currentUserId);
final isPaid = myTeam?.status == 'PAID';
```

---

## 9. Dart-модели

```dart
class TournamentListItem {
  final int id;
  final String name;
  final DateTime startDate;
  final DateTime endDate;
  final DateTime? registrationDeadline;
  final String status;      // DRAFT | REGISTRATION | IN_PROGRESS | COMPLETED | CANCELED
  final String format;      // SINGLES | DOUBLES
  final bool isPaid;
  final double entryFee;
  final int? maxTeams;
  final int teamsCount;
  final int paidTeamsCount;

  TournamentListItem.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        name = j['name'],
        startDate = DateTime.parse(j['start_date']),
        endDate = DateTime.parse(j['end_date']),
        registrationDeadline = j['registration_deadline'] != null
            ? DateTime.parse(j['registration_deadline']) : null,
        status = j['status'],
        format = j['format'],
        isPaid = j['is_paid'],
        entryFee = double.parse(j['entry_fee']),
        maxTeams = j['max_teams'],
        teamsCount = j['teams_count'],
        paidTeamsCount = j['paid_teams_count'];

  bool get canRegister => status == 'REGISTRATION' && (maxTeams == null || teamsCount < maxTeams!);
}

class PlayerInfo {
  final int id;
  final String name;
  final String? phone;

  PlayerInfo.fromJson(Map<String, dynamic> j)
      : id = j['id'], name = j['name'], phone = j['phone'];
}

class TournamentTeam {
  final int id;
  final String displayName;
  final String status;    // PENDING | CONFIRMED | PAID | WITHDRAWN | REFUNDED
  final int? seed;
  final PlayerInfo? player1Info;
  final PlayerInfo? player2Info;
  final DateTime? paidAt;
  final String paymentMethod;

  TournamentTeam.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        displayName = j['display_name'],
        status = j['status'],
        seed = j['seed'],
        player1Info = j['player1_info'] != null ? PlayerInfo.fromJson(j['player1_info']) : null,
        player2Info = j['player2_info'] != null ? PlayerInfo.fromJson(j['player2_info']) : null,
        paidAt = j['paid_at'] != null ? DateTime.parse(j['paid_at']) : null,
        paymentMethod = j['payment_method'] ?? '';
}

class TournamentMatch {
  final int id;
  final int roundNumber;
  final String roundName;
  final int matchNumber;
  final TournamentTeam? team1Info;
  final TournamentTeam? team2Info;
  final TournamentTeam? winnerInfo;
  final int? court;
  final String? courtName;
  final DateTime? scheduledAt;
  final String status;  // SCHEDULED | IN_PROGRESS | COMPLETED | POSTPONED | WALKOVER
  final String scoreTeam1;
  final String scoreTeam2;
  final int? nextMatch;

  TournamentMatch.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        roundNumber = j['round_number'],
        roundName = j['round_name'],
        matchNumber = j['match_number'],
        team1Info = j['team1_info'] != null ? TournamentTeam.fromJson(j['team1_info']) : null,
        team2Info = j['team2_info'] != null ? TournamentTeam.fromJson(j['team2_info']) : null,
        winnerInfo = j['winner_info'] != null ? TournamentTeam.fromJson(j['winner_info']) : null,
        court = j['court'],
        courtName = j['court_name'],
        scheduledAt = j['scheduled_at'] != null ? DateTime.parse(j['scheduled_at']) : null,
        status = j['status'],
        scoreTeam1 = j['score_team1'] ?? '',
        scoreTeam2 = j['score_team2'] ?? '',
        nextMatch = j['next_match'];
}

class TournamentBracket {
  final int tournamentId;
  final int totalRounds;
  final List<BracketRound> rounds;

  TournamentBracket.fromJson(Map<String, dynamic> j)
      : tournamentId = j['tournament_id'],
        totalRounds = j['total_rounds'],
        rounds = (j['rounds'] as List).map((r) => BracketRound.fromJson(r)).toList();
}

class BracketRound {
  final int roundNumber;
  final String roundName;
  final List<TournamentMatch> matches;

  BracketRound.fromJson(Map<String, dynamic> j)
      : roundNumber = j['round_number'],
        roundName = j['round_name'],
        matches = (j['matches'] as List).map((m) => TournamentMatch.fromJson(m)).toList();
}
```

---

## 10. Сценарий участника — полный flow

```
1. GET /api/tournaments/?status=REGISTRATION
   → Показать список открытых турниров

2. GET /api/tournaments/<id>/
   → Открыть детали, проверить is_paid, entry_fee, max_teams

3. GET /api/tournaments/<id>/teams/
   → Проверить, не зарегистрирован ли уже пользователь

4. POST /api/tournaments/<id>/teams/
   Body: { "player1_id": мой ID, "player2_id": ID напарника }
   → Заявка создана (status=PENDING)

5. Показать экран:
   "✅ Заявка отправлена! Ожидайте подтверждения."
   Если платный: "Оплатите 12 000₸ на ресепшене"

6. Периодически опрашивать статус команды:
   GET /api/tournaments/<id>/teams/
   Когда status == PAID → показать "✅ Вы в сетке!"

7. Когда tournament.status == IN_PROGRESS:
   GET /api/tournaments/<id>/my-matches/
   → Показать предстоящие матчи пользователя

8. GET /api/tournaments/<id>/bracket/
   → Показать полную сетку, выделить свою пару
```

---

## 11. Push-уведомления

Список событий, при которых рекомендуется отправлять push:

| Событие | Текст |
|---------|-------|
| Статус команды → `CONFIRMED` | "Ваша заявка на турнир подтверждена 🎾" |
| Статус команды → `PAID` | "Взнос оплачен — вы в сетке! ✅" |
| Матч назначен (scheduled_at появился) | "Ваш матч назначен: 15 апр, 10:00, корт 2" |
| `match.status` → `IN_PROGRESS` | "Ваш матч начался 🎾" |
| `match.status` → `COMPLETED` | "Матч завершён. Результат: 6-3, 6-4" |
| Турнир отменён | "Турнир отменён. Обратитесь для возврата взноса." |

> Push-уведомления отправляются через существующий механизм `notifications` app.
> Реализация на бэкенде — при обновлении статусов в views создавать `Notification` объекты.
