#!/usr/bin/env python3
"""
Создает backlog по чату в Linear.

Примеры:
  export LINEAR_API_TOKEN="lin_api_..."
  python scripts/create_linear_chat_backlog.py --team TAY --dry-run
  python scripts/create_linear_chat_backlog.py --team TAY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

LINEAR_URL = "https://api.linear.app/graphql"


@dataclass(frozen=True)
class Ticket:
    title: str
    priority: int  # 1 urgent, 2 high, 3 normal, 4 low
    estimate: int
    labels: tuple[str, ...]
    description: str


TICKETS: list[Ticket] = [
    Ticket(
        title="[CHAT] Перевести чат на архитектуру REST + WebSocket",
        priority=1,
        estimate=5,
        labels=("чат", "backend", "realtime", "p0", "архитектура"),
        description="""## Цель
Сделать production-ready realtime чат вместо polling-only.

## Scope
- REST: список диалогов, история сообщений, создание диалога.
- WebSocket: message.new, message.read, typing.start/stop.
- Redis как channel layer для масштабирования.

## Acceptance Criteria
- Сообщение доходит в realtime (<1с в локальной сети).
- При разрыве WS клиент восстанавливает состояние через REST.
- Документирован WS flow и точки интеграции.""",
    ),
    Ticket(
        title="[CHAT] JWT-аутентификация и ACL для WebSocket",
        priority=1,
        estimate=2,
        labels=("чат", "backend", "security", "p0", "auth"),
        description="""## Цель
Закрыть несанкционированный доступ к сокетам и чужим диалогам.

## Scope
- JWT-проверка в handshake.
- Проверка, что пользователь участник conversation.
- Отказ в подписке на чужой диалог.

## Acceptance Criteria
- Неавторизованный клиент получает отказ.
- Подписка на чужую комнату невозможна.
- Логи содержат причину отказа без утечки секретов.""",
    ),
    Ticket(
        title="[CHAT] Единый контракт WS-событий (v1)",
        priority=1,
        estimate=1,
        labels=("чат", "backend", "api-contract", "p0"),
        description="""## Цель
Зафиксировать единый формат payload для мобильной/веб команды.

## Scope
- События: message.send, message.new, message.read, typing.start, typing.stop, ack, error.
- Версионирование протокола v1.
- Валидация payload и единый error-ответ.

## Acceptance Criteria
- В документации есть примеры request/response по всем событиям.
- Невалидные payload всегда получают единый формат ошибки.""",
    ),
    Ticket(
        title="[CHAT] Идемпотентная отправка сообщений (client_message_id)",
        priority=1,
        estimate=2,
        labels=("чат", "backend", "reliability", "p0"),
        description="""## Цель
Исключить дубли сообщений при retry/reconnect.

## Scope
- Добавить client_message_id в send flow.
- Уникальность (conversation, sender, client_message_id).
- Повторный send возвращает существующее сообщение.

## Acceptance Criteria
- Повторная отправка не создает новую запись.
- Для retry возвращается тот же message_id.""",
    ),
    Ticket(
        title="[CHAT] Убрать N+1 в списке диалогов",
        priority=1,
        estimate=2,
        labels=("чат", "backend", "performance", "p0", "db"),
        description="""## Цель
Сделать список диалогов быстрым на больших данных.

## Scope
- Оптимизировать last_message/unread_count через annotate/subquery/prefetch.
- Убрать per-row запросы из serializer.
- Проверить нужные индексы в БД.

## Acceptance Criteria
- Количество SQL не растет линейно с числом диалогов.
- p95 latency эндпоинта заметно снижен.""",
    ),
    Ticket(
        title="[CHAT] Read receipts и консистентный unread_count",
        priority=1,
        estimate=2,
        labels=("чат", "backend", "realtime", "p0", "consistency"),
        description="""## Цель
Сделать корректную синхронизацию прочитанных сообщений.

## Scope
- Реализовать событие message.read.
- Атомарно помечать сообщения прочитанными.
- Мгновенно обновлять unread_count для обоих участников.

## Acceptance Criteria
- Отправитель видит read-status в realtime.
- unread_count совпадает между списком и деталкой.""",
    ),
    Ticket(
        title="[CHAT] Typing indicator с throttle/debounce",
        priority=2,
        estimate=1,
        labels=("чат", "backend", "realtime", "p1", "ux"),
        description="""## Цель
Добавить typing UX без перегрузки канала.

## Scope
- typing.start/typing.stop без сохранения в БД.
- Троттлинг на стороне сервера.
- Автоочистка состояния typing по таймауту/дисконнекту.

## Acceptance Criteria
- События typing не фладят канал.
- Индикатор гаснет автоматически при потере соединения.""",
    ),
    Ticket(
        title="[CHAT] Cursor-пагинация истории сообщений",
        priority=2,
        estimate=2,
        labels=("чат", "backend", "api", "p1", "pagination"),
        description="""## Цель
Стабильная догрузка истории без дыр и дублей.

## Scope
- Перейти на cursor-based пагинацию (before_id/cursor).
- Гарантировать детерминированный порядок сообщений.

## Acceptance Criteria
- Длинная история грузится без пропусков/дублей.
- Пагинация стабильна при одновременных новых сообщениях.""",
    ),
    Ticket(
        title="[CHAT] Статусы доставки sent/delivered/read",
        priority=2,
        estimate=2,
        labels=("чат", "backend", "reliability", "p1", "delivery-status"),
        description="""## Цель
Ввести прозрачный lifecycle сообщений.

## Scope
- Серверные статусы: sent, delivered, read.
- Рассылка переходов статусов отправителю по WS.

## Acceptance Criteria
- Переходы статусов монотонны и не откатываются.
- После reconnect статусы остаются корректными.""",
    ),
    Ticket(
        title="[CHAT] Reconnect + resync без потери сообщений",
        priority=2,
        estimate=2,
        labels=("чат", "backend", "reliability", "p1", "resync"),
        description="""## Цель
Гарантировать восстановление после обрыва сети.

## Scope
- Дельта-синхронизация по last_seen_message_id.
- Heartbeat/ping-pong и cleanup мертвых соединений.

## Acceptance Criteria
- После reconnect клиент получает все пропущенные сообщения.
- Мертвые сокеты удаляются автоматически.""",
    ),
    Ticket(
        title="[CHAT] Лимиты безопасности для WS и валидация payload",
        priority=1,
        estimate=2,
        labels=("чат", "backend", "security", "p0", "rate-limit"),
        description="""## Цель
Защитить чат от флуда и некорректных запросов.

## Scope
- Лимиты по частоте send/read/typing.
- Лимит размера payload.
- Стандартизированная валидация входных данных.

## Acceptance Criteria
- Flood ограничивается, сервис остается стабильным.
- Слишком большие/битые payload отклоняются корректно.""",
    ),
    Ticket(
        title="[CHAT] Тестовое покрытие чата (REST + WebSocket)",
        priority=1,
        estimate=4,
        labels=("чат", "backend", "tests", "p0", "qa"),
        description="""## Цель
Закрыть критичные сценарии автотестами.

## Scope
- Тесты: permissions, send, read/unread, idempotency, чужой диалог.
- Тесты на reconnect/resync и rate-limit.
- Тесты consumer/handlers для WS.

## Acceptance Criteria
- Критичный happy-path и edge-cases покрыты.
- Все тесты green в CI.""",
    ),
    Ticket(
        title="[CHAT] Structured logging + метрики для чата",
        priority=2,
        estimate=2,
        labels=("чат", "backend", "observability", "p1"),
        description="""## Цель
Сделать чат наблюдаемым и удобным для расследования инцидентов.

## Scope
- JSON-логи для connect/disconnect/send/error.
- request_id/connection_id для трассировки.
- Метрики: active connections, error rate, p95 latency.

## Acceptance Criteria
- По логам и метрикам видны узкие места и причины сбоев.""",
    ),
    Ticket(
        title="[CHAT] Обновить техдок для мобильной команды",
        priority=2,
        estimate=1,
        labels=("чат", "backend", "documentation", "p1"),
        description="""## Цель
Дать мобильной команде полный self-service документ.

## Scope
- Обновить docs/API_CHAT_FLUTTER 2.md:
  - WS endpoint и auth flow
  - контракты событий
  - reconnect/resync стратегия
  - коды ошибок

## Acceptance Criteria
- Мобильная команда может интегрировать чат без устных пояснений.""",
    ),
]


def gql(token: str, query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        LINEAR_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Linear HTTP {exc.code}: {body}") from exc
    if "errors" in data:
        raise RuntimeError(f"Linear GraphQL errors: {data['errors']}")
    return data["data"]


def resolve_team_uuid(token: str, team_ref: str) -> str:
    # Already UUID-like
    if "-" in team_ref and len(team_ref) >= 30:
        return team_ref
    q = """
    query ResolveTeam($key: String!) {
      teams(filter: { key: { eq: $key } }, first: 1) {
        nodes { id key name }
      }
    }
    """
    d = gql(token, q, {"key": team_ref})
    nodes = d["teams"]["nodes"]
    if not nodes:
        raise RuntimeError(f"Team not found by key/id: {team_ref}")
    return nodes[0]["id"]


def get_or_create_label(token: str, team_id: str, name: str, dry_run: bool) -> str:
    q = """
    query TeamLabels($teamId: String!) {
      team(id: $teamId) {
        labels(first: 200) { nodes { id name } }
      }
    }
    """
    d = gql(token, q, {"teamId": team_id})
    for item in d["team"]["labels"]["nodes"]:
        if item["name"].lower() == name.lower():
            return item["id"]
    if dry_run:
        return f"DRY_{name}"

    m = """
    mutation CreateLabel($input: IssueLabelCreateInput!) {
      issueLabelCreate(input: $input) { success issueLabel { id name } }
    }
    """
    created = gql(
        token,
        m,
        {"input": {"teamId": team_id, "name": name}},
    )["issueLabelCreate"]["issueLabel"]["id"]
    return created


def find_issue_by_title(token: str, team_id: str, title: str) -> str | None:
    q = """
    query TeamIssues($teamId: String!, $term: String!) {
      team(id: $teamId) {
        issues(
          first: 20,
          filter: { title: { containsIgnoreCase: $term } }
        ) {
          nodes { id title identifier url }
        }
      }
    }
    """
    d = gql(token, q, {"teamId": team_id, "term": title})
    for issue in d["team"]["issues"]["nodes"]:
        if issue["title"].strip().lower() == title.strip().lower():
            return issue["id"]
    return None


def create_issue(
    token: str,
    team_id: str,
    ticket: Ticket,
    label_ids: list[str],
    dry_run: bool,
) -> None:
    if find_issue_by_title(token, team_id, ticket.title):
        print(f"SKIP (exists): {ticket.title}")
        return

    if dry_run:
        print(f"DRY RUN -> CREATE: {ticket.title}")
        print(f"  priority={ticket.priority}, estimate={ticket.estimate}, labels={ticket.labels}")
        return

    m = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier title url }
      }
    }
    """
    data = gql(
        token,
        m,
        {
            "input": {
                "teamId": team_id,
                "title": ticket.title,
                "description": ticket.description,
                "priority": ticket.priority,
                "estimate": ticket.estimate,
                "labelIds": label_ids,
            }
        },
    )["issueCreate"]["issue"]
    print(f"CREATED: {data['identifier']} -> {data['url']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Создать backlog чата в Linear")
    parser.add_argument("--team", required=True, help="ID команды Linear, например TAY")
    parser.add_argument("--token", default=os.getenv("LINEAR_API_TOKEN"), help="Linear API token")
    parser.add_argument("--dry-run", action="store_true", help="Показать что будет создано без записи")
    args = parser.parse_args()

    token = args.token
    if not token:
        print("Ошибка: передайте --token или LINEAR_API_TOKEN", file=sys.stderr)
        return 1

    team_id = resolve_team_uuid(token, args.team)
    print(f"Team: {args.team} (resolved: {team_id}), dry_run={args.dry_run}")
    print(f"Tickets planned: {len(TICKETS)}")

    label_cache: dict[str, str] = {}
    for ticket in TICKETS:
        ids = []
        for label in ticket.labels:
            if label not in label_cache:
                label_cache[label] = get_or_create_label(token, team_id, label, args.dry_run)
            ids.append(label_cache[label])
        create_issue(token, team_id, ticket, ids, args.dry_run)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
