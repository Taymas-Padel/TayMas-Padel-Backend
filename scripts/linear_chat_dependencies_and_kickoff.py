#!/usr/bin/env python3
"""
Настраивает зависимости и kickoff для chat-тикетов в Linear.

Что делает:
1) Ставит зависимости (IssueRelation type=blocks)
2) Назначает ответственного на стартовые тикеты
3) Переводит стартовые тикеты в состояние Ready (или Todo как fallback)

Пример:
  export LINEAR_API_TOKEN="lin_api_..."
  python scripts/linear_chat_dependencies_and_kickoff.py --team TAY --assignee "aarhat144"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

LINEAR_URL = "https://api.linear.app/graphql"

# Последовательность по нашему chat-roadmap:
# A blocks B  <=> B нельзя начать до A
DEPENDENCIES = [
    ("TAY-6", "TAY-7"),
    ("TAY-7", "TAY-8"),
    ("TAY-8", "TAY-9"),
    ("TAY-9", "TAY-11"),
    ("TAY-11", "TAY-10"),
    ("TAY-10", "TAY-16"),
    ("TAY-16", "TAY-15"),
    ("TAY-15", "TAY-14"),
    ("TAY-14", "TAY-12"),
    ("TAY-12", "TAY-17"),
    ("TAY-17", "TAY-18"),
    ("TAY-18", "TAY-19"),
    ("TAY-8", "TAY-13"),
]

# Первые тикеты для старта (kickoff)
KICKOFF_IDS = ["TAY-6", "TAY-7", "TAY-8"]


def gql(token: str, query: str, variables: dict) -> dict:
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


def resolve_team_uuid(token: str, team_ref: str) -> str:
    if "-" in team_ref and len(team_ref) >= 30:
        return team_ref
    q = """
    query ResolveTeam($key: String!) {
      teams(filter: { key: { eq: $key } }, first: 1) { nodes { id key name } }
    }
    """
    d = gql(token, q, {"key": team_ref})
    nodes = d["teams"]["nodes"]
    if not nodes:
        raise RuntimeError(f"Team not found by key/id: {team_ref}")
    return nodes[0]["id"]


def issue_id_by_identifier(token: str, identifier: str) -> str:
    q = """
    query IssueByIdentifier($id: String!) {
      issue(id: $id) { id identifier title state { name } assignee { id name displayName } }
    }
    """
    d = gql(token, q, {"id": identifier})
    issue = d.get("issue")
    if not issue:
        raise RuntimeError(f"Issue not found: {identifier}")
    return issue["id"]


def resolve_assignee(token: str, team_id: str, needle: str) -> tuple[str, str]:
    q = """
    query TeamMembers($teamId: String!) {
      team(id: $teamId) {
        memberships(first: 200) {
          nodes { user { id name displayName email } }
        }
      }
    }
    """
    d = gql(token, q, {"teamId": team_id})
    members = d["team"]["memberships"]["nodes"]
    n = needle.lower().strip()
    for m in members:
        u = m["user"]
        fields = [
            (u.get("name") or "").lower(),
            (u.get("displayName") or "").lower(),
            (u.get("email") or "").lower(),
        ]
        if any(n in x for x in fields):
            return u["id"], (u.get("displayName") or u.get("name") or u["id"])
    raise RuntimeError(f"Assignee not found in team by: {needle}")


def resolve_ready_state(token: str, team_id: str) -> tuple[str, str]:
    q = """
    query TeamStates($teamId: String!) {
      team(id: $teamId) {
        states { nodes { id name type } }
      }
    }
    """
    d = gql(token, q, {"teamId": team_id})
    states = d["team"]["states"]["nodes"]

    # Предпочитаем Ready, потом Todo/Backlog
    for candidate in ("Ready", "Todo", "Backlog"):
        for st in states:
            if (st["name"] or "").lower() == candidate.lower():
                return st["id"], st["name"]
    # fallback: первый unstarted
    for st in states:
        if (st.get("type") or "").lower() == "unstarted":
            return st["id"], st["name"]
    raise RuntimeError("No suitable kickoff state found")


def create_blocks_relation(token: str, blocker_id: str, blocked_id: str) -> None:
    m = """
    mutation Relate($input: IssueRelationCreateInput!) {
      issueRelationCreate(input: $input) {
        success
        issueRelation { id type }
      }
    }
    """
    gql(
        token,
        m,
        {"input": {"issueId": blocker_id, "relatedIssueId": blocked_id, "type": "blocks"}},
    )


def update_issue(token: str, issue_id: str, assignee_id: str, state_id: str) -> None:
    m = """
    mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) {
        success
        issue { id identifier title state { name } assignee { id name displayName } }
      }
    }
    """
    gql(
        token,
        m,
        {"id": issue_id, "input": {"assigneeId": assignee_id, "stateId": state_id}},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Set chat dependencies and kickoff in Linear")
    parser.add_argument("--team", required=True, help="Team key/id, e.g. TAY")
    parser.add_argument("--assignee", required=True, help="Part of name/displayName/email")
    parser.add_argument("--token", default=os.getenv("LINEAR_API_TOKEN"), help="Linear API token")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without write")
    args = parser.parse_args()

    if not args.token:
        print("Ошибка: передайте --token или LINEAR_API_TOKEN", file=sys.stderr)
        return 1

    token = args.token
    team_id = resolve_team_uuid(token, args.team)
    assignee_id, assignee_name = resolve_assignee(token, team_id, args.assignee)
    state_id, state_name = resolve_ready_state(token, team_id)

    print(f"Team: {args.team} -> {team_id}")
    print(f"Assignee: {assignee_name} ({assignee_id})")
    print(f"Kickoff state: {state_name} ({state_id})")

    # Dependencies
    print("\n[1/2] Setting dependencies...")
    for blocker, blocked in DEPENDENCIES:
        blocker_id = issue_id_by_identifier(token, blocker)
        blocked_id = issue_id_by_identifier(token, blocked)
        if args.dry_run:
            print(f"DRY: {blocker} blocks {blocked}")
            continue
        try:
            create_blocks_relation(token, blocker_id, blocked_id)
            print(f"OK: {blocker} blocks {blocked}")
        except Exception as exc:
            # Duplicate relation or unsupported type – show and continue
            print(f"SKIP/ERR: {blocker} -> {blocked}: {exc}")

    # Kickoff
    print("\n[2/2] Setting kickoff owner/state...")
    for ident in KICKOFF_IDS:
        issue_id = issue_id_by_identifier(token, ident)
        if args.dry_run:
            print(f"DRY: assign {ident} to {assignee_name}, state={state_name}")
            continue
        update_issue(token, issue_id, assignee_id, state_id)
        print(f"OK: {ident} assigned to {assignee_name}, state={state_name}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
