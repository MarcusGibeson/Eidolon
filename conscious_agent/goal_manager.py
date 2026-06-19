from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from memory import store_memory
from paths import DATA_DIR
from project_manager import get_active_project
from self_model import load_self_model, save_self_model


GOALS_FILE = DATA_DIR / "goals.json"

GOAL_STATUSES = {"planned", "active", "blocked", "paused", "completed", "cancelled"}
GOAL_PRIORITIES = {"low", "medium", "high", "critical"}
OPEN_STATUSES = {"planned", "active", "blocked", "paused"}


@dataclass
class GoalMutationResult:
    ok: bool
    goal: dict[str, Any] | None = None
    message: str = ""
    error: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not cleaned:
        cleaned = "goal"
    return cleaned[:max_length].strip("-") or "goal"


def _new_goal_id(title: str) -> str:
    return f"goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(title)}"


def _default_goals() -> dict[str, Any]:
    now = _now()
    return {
        "version": 1,
        "active_goal": "",
        "goals": [
            {
                "id": "goal_seed_build-eidolon",
                "title": "Build Eidolon into a safe local AI assistant",
                "description": "Continue developing Eidolon with memory, tools, review, approved edits, rollback, testing, and supervised self-improvement.",
                "project": "Eidolon",
                "status": "active",
                "priority": "critical",
                "next_actions": [
                    "Test the newest workflow after each version.",
                    "Keep powerful actions permission-gated and logged."
                ],
                "blockers": [],
                "notes": [
                    "Seed goal created by v1.8 Goal Manager."
                ],
                "created_at": now,
                "updated_at": now,
                "completed_at": "",
            },
            {
                "id": "goal_seed_keep-memory-usable",
                "title": "Keep Eidolon memory useful and compact",
                "description": "Use memory status, compaction, summaries, and semantic rebuilds to keep long-term continuity manageable.",
                "project": "Eidolon",
                "status": "planned",
                "priority": "high",
                "next_actions": [
                    "Run --memory-status after active development sessions."
                ],
                "blockers": [],
                "notes": [],
                "created_at": now,
                "updated_at": now,
                "completed_at": "",
            },
        ],
    }


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not GOALS_FILE.exists():
        with GOALS_FILE.open("w", encoding="utf-8") as file:
            json.dump(_default_goals(), file, indent=2)


def load_goals_data() -> dict[str, Any]:
    _ensure_storage()
    try:
        with GOALS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        data = _default_goals()

    if not isinstance(data, dict):
        data = _default_goals()

    data.setdefault("version", 1)
    data.setdefault("active_goal", "")
    data.setdefault("goals", [])

    if not isinstance(data["goals"], list):
        data["goals"] = []

    return data


def save_goals_data(data: dict[str, Any]) -> None:
    _ensure_storage()
    with GOALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def list_goals(
    status: str = "",
    project: str = "",
    include_cancelled: bool = True,
) -> list[dict[str, Any]]:
    goals = load_goals_data().get("goals", [])

    if status:
        status = status.lower().strip()
        goals = [goal for goal in goals if goal.get("status") == status]

    if project:
        project_lower = project.lower().strip()
        goals = [goal for goal in goals if goal.get("project", "").lower() == project_lower]

    if not include_cancelled:
        goals = [goal for goal in goals if goal.get("status") != "cancelled"]

    return sorted(goals, key=lambda goal: goal.get("updated_at", goal.get("created_at", "")), reverse=True)


def resolve_goal_id(goal_id: str) -> str:
    token = (goal_id or "").strip()
    token_lower = token.lower()
    if token_lower not in {
        "latest",
        "last",
        "latest-open",
        "latest-active",
        "latest-planned",
        "latest-blocked",
        "latest-completed",
    }:
        return token

    if token_lower in {"latest", "last"}:
        matches = list_goals()
    elif token_lower == "latest-open":
        matches = [goal for goal in list_goals() if goal.get("status") in OPEN_STATUSES]
    elif token_lower == "latest-active":
        matches = list_goals(status="active")
    elif token_lower == "latest-planned":
        matches = list_goals(status="planned")
    elif token_lower == "latest-blocked":
        matches = list_goals(status="blocked")
    else:
        matches = list_goals(status="completed")

    if not matches:
        return ""

    return matches[0].get("id", "")


def get_goal(goal_id: str) -> dict[str, Any] | None:
    resolved = resolve_goal_id(goal_id)
    if not resolved:
        return None

    for goal in load_goals_data().get("goals", []):
        if goal.get("id") == resolved:
            return goal
    return None


def _update_goal_in_data(data: dict[str, Any], updated_goal: dict[str, Any]) -> bool:
    for index, goal in enumerate(data.get("goals", [])):
        if goal.get("id") == updated_goal.get("id"):
            data["goals"][index] = updated_goal
            return True
    return False


def _sync_self_model_active_goals() -> None:
    """
    Keeps self_model['active_goals'] useful while structured goals become source of truth.
    This preserves older modules that still read loose active_goals strings.
    """
    try:
        self_model = load_self_model()
        open_goals = [
            goal["title"]
            for goal in list_goals()
            if goal.get("status") in {"active", "planned", "blocked"}
        ][:8]
        if open_goals:
            self_model["active_goals"] = open_goals
            save_self_model(self_model)
    except Exception:
        # Goal changes should not fail just because legacy self_model sync failed.
        return


def add_goal(
    title: str,
    description: str = "",
    priority: str = "medium",
    status: str = "planned",
    project: str = "",
    next_action: str = "",
) -> GoalMutationResult:
    title = title.strip()
    if not title:
        return GoalMutationResult(ok=False, error="Goal title cannot be empty.")

    priority = priority.lower().strip() or "medium"
    if priority not in GOAL_PRIORITIES:
        return GoalMutationResult(ok=False, error=f"Invalid priority '{priority}'. Use one of: {', '.join(sorted(GOAL_PRIORITIES))}.")

    status = status.lower().strip() or "planned"
    if status not in GOAL_STATUSES:
        return GoalMutationResult(ok=False, error=f"Invalid status '{status}'. Use one of: {', '.join(sorted(GOAL_STATUSES))}.")

    if not project:
        active_project = get_active_project()
        project = active_project.get("name", "") if active_project else ""

    now = _now()
    goal = {
        "id": _new_goal_id(title),
        "title": title,
        "description": description.strip(),
        "project": project,
        "status": status,
        "priority": priority,
        "next_actions": [next_action.strip()] if next_action.strip() else [],
        "blockers": [],
        "notes": [],
        "created_at": now,
        "updated_at": now,
        "completed_at": now if status == "completed" else "",
    }

    data = load_goals_data()
    data.setdefault("goals", []).append(goal)
    if status == "active":
        data["active_goal"] = goal["id"]
    save_goals_data(data)
    _sync_self_model_active_goals()

    store_memory({
        "type": "goal_event",
        "content": f"Added goal '{title}' with status {status} and priority {priority}.",
        "source": "goal_manager",
        "goal_id": goal["id"],
        "project": project,
    })

    return GoalMutationResult(ok=True, goal=goal, message=f"Added goal: {goal['id']}")


def set_goal_status(goal_id: str, status: str, note: str = "") -> GoalMutationResult:
    status = status.lower().strip()
    if status not in GOAL_STATUSES:
        return GoalMutationResult(ok=False, error=f"Invalid status '{status}'. Use one of: {', '.join(sorted(GOAL_STATUSES))}.")

    data = load_goals_data()
    goal = get_goal(goal_id)
    if not goal:
        return GoalMutationResult(ok=False, error=f"Goal not found: {goal_id}")

    old_status = goal.get("status", "")
    goal["status"] = status
    goal["updated_at"] = _now()
    if status == "completed":
        goal["completed_at"] = _now()
    elif status != "completed":
        goal["completed_at"] = goal.get("completed_at", "") if old_status == "completed" else ""

    if note:
        goal.setdefault("notes", []).append(f"[{_now()}] Status changed from {old_status} to {status}: {note}")

    if status == "active":
        data["active_goal"] = goal["id"]
    elif data.get("active_goal") == goal.get("id") and status not in {"active", "planned", "blocked"}:
        data["active_goal"] = ""

    if not _update_goal_in_data(data, goal):
        return GoalMutationResult(ok=False, error=f"Could not update goal: {goal_id}")

    save_goals_data(data)
    _sync_self_model_active_goals()

    store_memory({
        "type": "goal_event",
        "content": f"Goal '{goal.get('title')}' changed from {old_status} to {status}.",
        "source": "goal_manager",
        "goal_id": goal.get("id"),
        "project": goal.get("project", ""),
    })

    return GoalMutationResult(ok=True, goal=goal, message=f"Goal {goal['id']} status changed to {status}.")


def add_goal_note(goal_id: str, note: str) -> GoalMutationResult:
    note = note.strip()
    if not note:
        return GoalMutationResult(ok=False, error="Goal note cannot be empty.")

    data = load_goals_data()
    goal = get_goal(goal_id)
    if not goal:
        return GoalMutationResult(ok=False, error=f"Goal not found: {goal_id}")

    goal.setdefault("notes", []).append(f"[{_now()}] {note}")
    goal["updated_at"] = _now()

    if not _update_goal_in_data(data, goal):
        return GoalMutationResult(ok=False, error=f"Could not update goal: {goal_id}")

    save_goals_data(data)

    store_memory({
        "type": "goal_event",
        "content": f"Added note to goal '{goal.get('title')}': {note}",
        "source": "goal_manager",
        "goal_id": goal.get("id"),
        "project": goal.get("project", ""),
    })

    return GoalMutationResult(ok=True, goal=goal, message=f"Added note to {goal['id']}.")


def add_goal_next_action(goal_id: str, action: str) -> GoalMutationResult:
    action = action.strip()
    if not action:
        return GoalMutationResult(ok=False, error="Next action cannot be empty.")

    data = load_goals_data()
    goal = get_goal(goal_id)
    if not goal:
        return GoalMutationResult(ok=False, error=f"Goal not found: {goal_id}")

    goal.setdefault("next_actions", []).append(action)
    goal["updated_at"] = _now()

    if not _update_goal_in_data(data, goal):
        return GoalMutationResult(ok=False, error=f"Could not update goal: {goal_id}")

    save_goals_data(data)
    _sync_self_model_active_goals()

    store_memory({
        "type": "goal_event",
        "content": f"Added next action to goal '{goal.get('title')}': {action}",
        "source": "goal_manager",
        "goal_id": goal.get("id"),
        "project": goal.get("project", ""),
    })

    return GoalMutationResult(ok=True, goal=goal, message=f"Added next action to {goal['id']}.")


def add_goal_blocker(goal_id: str, blocker: str) -> GoalMutationResult:
    blocker = blocker.strip()
    if not blocker:
        return GoalMutationResult(ok=False, error="Blocker cannot be empty.")

    data = load_goals_data()
    goal = get_goal(goal_id)
    if not goal:
        return GoalMutationResult(ok=False, error=f"Goal not found: {goal_id}")

    goal.setdefault("blockers", []).append(f"[{_now()}] {blocker}")
    goal["status"] = "blocked"
    goal["updated_at"] = _now()

    if not _update_goal_in_data(data, goal):
        return GoalMutationResult(ok=False, error=f"Could not update goal: {goal_id}")

    save_goals_data(data)
    _sync_self_model_active_goals()

    store_memory({
        "type": "goal_event",
        "content": f"Goal '{goal.get('title')}' was blocked: {blocker}",
        "source": "goal_manager",
        "goal_id": goal.get("id"),
        "project": goal.get("project", ""),
    })

    return GoalMutationResult(ok=True, goal=goal, message=f"Blocked goal {goal['id']}.")


def goal_context_text(limit: int = 6) -> str:
    goals = [goal for goal in list_goals(include_cancelled=False) if goal.get("status") in OPEN_STATUSES]
    if not goals:
        return "No open structured goals are currently tracked."

    lines = ["Structured goals:"]
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    goals = sorted(
        goals,
        key=lambda goal: (priority_order.get(goal.get("priority", "medium"), 2), goal.get("updated_at", "")),
    )[:limit]

    for goal in goals:
        next_actions = goal.get("next_actions", [])[:2]
        action_text = "; ".join(next_actions) if next_actions else "none"
        lines.append(
            f"- {goal.get('title')} [{goal.get('status')}, {goal.get('priority')}] "
            f"next: {action_text}"
        )

    return "\n".join(lines)


def goal_status_summary() -> dict[str, Any]:
    goals = list_goals()
    counts: dict[str, int] = {status: 0 for status in sorted(GOAL_STATUSES)}
    priorities: dict[str, int] = {priority: 0 for priority in sorted(GOAL_PRIORITIES)}
    for goal in goals:
        counts[goal.get("status", "planned")] = counts.get(goal.get("status", "planned"), 0) + 1
        priorities[goal.get("priority", "medium")] = priorities.get(goal.get("priority", "medium"), 0) + 1
    return {
        "total": len(goals),
        "by_status": counts,
        "by_priority": priorities,
        "active_goal": load_goals_data().get("active_goal", ""),
    }


def _goal_line(goal: dict[str, Any]) -> str:
    return (
        f"{goal.get('id')} | {goal.get('status')} | {goal.get('priority')} | "
        f"{goal.get('project', '')} | {goal.get('title')}"
    )


def _print_goal(goal: dict[str, Any], full: bool = False) -> None:
    print(f"ID: {goal.get('id')}")
    print(f"Title: {goal.get('title')}")
    print(f"Project: {goal.get('project', '')}")
    print(f"Status: {goal.get('status')}")
    print(f"Priority: {goal.get('priority')}")
    print(f"Created: {goal.get('created_at')}")
    print(f"Updated: {goal.get('updated_at')}")
    if goal.get("completed_at"):
        print(f"Completed: {goal.get('completed_at')}")
    if goal.get("description"):
        print()
        print("Description:")
        print(goal.get("description"))

    if goal.get("next_actions"):
        print()
        print("Next actions:")
        for action in goal.get("next_actions", []):
            print(f"- {action}")

    if goal.get("blockers"):
        print()
        print("Blockers:")
        for blocker in goal.get("blockers", []):
            print(f"- {blocker}")

    if full and goal.get("notes"):
        print()
        print("Notes:")
        for note in goal.get("notes", []):
            print(f"- {note}")


def print_goal_status() -> None:
    summary = goal_status_summary()
    print("# Goal Status")
    print(f"Total goals: {summary['total']}")
    print(f"Active goal id: {summary.get('active_goal') or '[none]'}")
    print()
    print("By status:")
    for status, count in summary["by_status"].items():
        print(f"  {status}: {count}")
    print()
    print("By priority:")
    for priority, count in summary["by_priority"].items():
        print(f"  {priority}: {count}")
    print()
    print("Open goal context:")
    print(goal_context_text())


def print_goal_list(status: str = "", project: str = "", include_cancelled: bool = True) -> None:
    goals = list_goals(status=status, project=project, include_cancelled=include_cancelled)
    if not goals:
        print("No goals found.")
        return
    for goal in goals:
        print(_goal_line(goal))


def print_goal_detail(goal_id: str, full: bool = False) -> None:
    goal = get_goal(goal_id)
    if not goal:
        print(f"Goal not found: {goal_id}")
        return
    _print_goal(goal, full=full)


def print_add_goal(
    title: str,
    description: str = "",
    priority: str = "medium",
    status: str = "planned",
    project: str = "",
    next_action: str = "",
) -> None:
    result = add_goal(
        title=title,
        description=description,
        priority=priority,
        status=status,
        project=project,
        next_action=next_action,
    )
    if not result.ok:
        print(f"Could not add goal: {result.error}")
        return
    print(result.message)
    if result.goal:
        print(_goal_line(result.goal))


def print_set_goal_status(goal_id: str, status: str, note: str = "") -> None:
    result = set_goal_status(goal_id, status=status, note=note)
    if not result.ok:
        print(f"Could not update goal: {result.error}")
        return
    print(result.message)
    if result.goal:
        print(_goal_line(result.goal))


def print_add_goal_note(goal_id: str, note: str) -> None:
    result = add_goal_note(goal_id, note)
    if not result.ok:
        print(f"Could not add note: {result.error}")
        return
    print(result.message)


def print_add_goal_next_action(goal_id: str, action: str) -> None:
    result = add_goal_next_action(goal_id, action)
    if not result.ok:
        print(f"Could not add next action: {result.error}")
        return
    print(result.message)


def print_block_goal(goal_id: str, blocker: str) -> None:
    result = add_goal_blocker(goal_id, blocker)
    if not result.ok:
        print(f"Could not block goal: {result.error}")
        return
    print(result.message)


def print_complete_goal(goal_id: str, note: str = "") -> None:
    print_set_goal_status(goal_id, "completed", note=note)
