#!/usr/bin/env python3
"""
Настройка chat-тикетов в Linear:
- выставляет зависимости между тикетами,
- переводит стартовые задачи в Todo,
- назначает ответственного.

Примеры:
  export LINEAR_API_TOKEN="lin_api_..."
  python scripts/linear_chat_setup.py --team TAY --assignee "aarhat144" --dry-run
  python scripts/linear_chat_setup.py --team TAY --assignee "aarhat144"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

LINEAR_URL = "https://api.linear.app/graphql"

# Созданные задачи из прошлого шага
CHAT_IDS = [f"TAY-{i}" for i in range(6, 20)]

# Порядок и зависимости: A -> B (B блокируется A)
DEPENDENCIES = [
    ("TAY-6", "TAY-7"),
    ("TAY-7", "TAY-8"),
    ("TAY-8", "TAY-9"),
    ("TAY-9", "TAY-10"),
    ("TAY-10", "TAY-11"),
    ("TAY-11", "TAY-16"),
    ("TAY-16", "TAY-15"),
    ("TAY-15", "TAY-14"),
    ("TAY-14", "TAY-12"),
    ("TAY-12", "TAY-13"),
    ("TAY-13", "TAY-18"),
    ("TAY-18", "TAY-17"),
    ("TAY-17", "TAY-19"),
]

# Первые тикеты, которые должны попасть в Todo
START_TODOS = ["TAY-6", "TAY-7", "TAY-8", "TAY-16"]


def gql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        LINEAR_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": token},
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


def resolve_team(token: str, team_ref: str) -> dict[str, str]:
    if "-" in team_ref and len(team_ref) > 30:
        q = """
        query TeamById($id: String!) {
          team(id: $id) { id key name states { nodes { id name type } } }
        }
        """
        d = gql(token, q, {"id": team_ref})["team"]
        return {"id": d["id"], "key": d["key"], "name": d["name"]}
    q = """
    query TeamByKey($key: String!) {
      teams(filter: { key: { eq: $key } }, first: 1) {
        nodes { id key name states { nodes { id name type } } }
      }
    }
    """
    nodes = gql(token, q, {"key": team_ref})["teams"]["nodes"]
    if not nodes:
        raise RuntimeError(f"Team not found: {team_ref}")
    t = nodes[0]
    return {"id": t["id"], "key": t["key"], "name": t["name"], "states": t["states"]["nodes"]}


def resolve_assignee(token: str, query_text: str) -> str:
    q = """
    query FindUser($term: String!) {
      users(
        first: 20,
        filter: {
          or: [
            { name: { containsIgnoreCase: $term } },
            { displayName: { containsIgnoreCase: $term } },
            { email: { containsIgnoreCase: $term } }
          ]
        }
      ) {
        nodes { id name displayName email active }
      }
    }
    """
    nodes = gql(token, q, {"term": query_text})["users"]["nodes"]
    active = [u for u in nodes if u.get("active")]
    if not active:
        raise RuntimeError(f"Active user not found by query: {query_text}")
    # берем наиболее релевантного первого
    return active[0]["id"]


def resolve_issue_ids(token: str, identifiers: list[str]) -> dict[str, str]:
    q = """
    query IssueByIdentifier($id: String!) {
      issue(id: $id) { id identifier title state { name type } }
    }
    """
    mapping: dict[str, str] = {}
    missing: list[str] = []
    for ident in identifiers:
        issue = gql(token, q, {"id": ident}).get("issue")
        if not issue:
            missing.append(ident)
            continue
        mapping[ident] = issue["id"]
    if missing:
        raise RuntimeError(f"Issues not found: {missing}")
    return mapping


def resolve_todo_state_id(token: str, team_id: str) -> str:
    q = """
    query TeamStates($teamId: String!) {
      team(id: $teamId) {
        states { nodes { id name type } }
      }
    }
    """
    states = gql(token, q, {"teamId": team_id})["team"]["states"]["nodes"]
    # Сначала пробуем type=unstarted (обычно это Todo)
    for s in states:
        if s["type"] == "unstarted":
            return s["id"]
    # fallback по имени
    for s in states:
        if s["name"].strip().lower() in {"todo", "to do", "backlog"}:
            return s["id"]
    raise RuntimeError("Could not resolve Todo state id")


def create_dependency(token: str, blocker_id: str, blocked_id: str, dry_run: bool) -> None:
    if dry_run:
        print(f"DRY dependency: {blocker_id} blocks {blocked_id}")
        return
    m = """
    mutation LinkDep($input: IssueRelationCreateInput!) {
      issueRelationCreate(input: $input) { success }
    }
    """
    gql(
        token,
        m,
        {
            "input": {
                "type": "blocks",
                "issueId": blocker_id,
                "relatedIssueId": blocked_id,
            }
        },
    )
    print(f"Dependency created: {blocker_id} -> {blocked_id}")


def update_issue(
    token: str,
    issue_id: str,
    assignee_id: str,
    state_id: str,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"DRY update issue: {issue_id}, assignee={assignee_id}, state={state_id}")
        return
    m = """
    mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) { success }
    }
    """
    gql(
        token,
        m,
        {"id": issue_id, "input": {"assigneeId": assignee_id, "stateId": state_id}},
    )
    print(f"Issue updated: {issue_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Настроить chat-тикеты в Linear")
    parser.add_argument("--team", required=True, help="Team key/id, например TAY")
    parser.add_argument("--assignee", required=True, help="Имя/ник/email исполнителя")
    parser.add_argument("--token", default=os.getenv("LINEAR_API_TOKEN"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.token:
        print("Передайте --token или LINEAR_API_TOKEN", file=sys.stderr)
        return 1

    team = resolve_team(args.token, args.team)
    assignee_id = resolve_assignee(args.token, args.assignee)
    issue_ids = resolve_issue_ids(args.token, CHAT_IDS)
    todo_state_id = resolve_todo_state_id(args.token, team["id"])

    print(f"Team: {team['key']} ({team['id']}), dry_run={args.dry_run}")
    print(f"Issues found: {len(issue_ids)}")
    print(f"Todo state: {todo_state_id}")
    print(f"Assignee resolved: {assignee_id}")

    # 1) dependencies
    for blocker, blocked in DEPENDENCIES:
        create_dependency(args.token, issue_ids[blocker], issue_ids[blocked], args.dry_run)

    # 2) set first tasks to Todo + assignee
    for ident in START_TODOS:
        update_issue(args.token, issue_ids[ident], assignee_id, todo_state_id, args.dry_run)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
