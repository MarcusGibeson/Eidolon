from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from memory import store_memory
from paths import DATA_DIR
from project_manager import get_active_project


TASKS_FILE = DATA_DIR / "tasks.json"

TASK_STATUSES = {"planned", "active", "blocked", "paused", "done", "cancelled"}
TASK_PRIORITIES = {"low", "medium", "high", "critical"}
OPEN_STATUSES = {"planned", "active", "blocked", "paused"}
READY_STATUSES = {"planned", "active"}
PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class TaskMutationResult:
    ok: bool
    task: dict[str, Any] | None = None
    message: str = ""
    error: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not cleaned:
        cleaned = "task"
    return cleaned[:max_length].strip("-") or "task"


def _new_task_id(title: str) -> str:
    return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(title)}"


def _default_tasks() -> dict[str, Any]:
    return {
        "version": 1,
        "active_task": "",
        "tasks": [],
    }


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        with TASKS_FILE.open("w", encoding="utf-8") as file:
            json.dump(_default_tasks(), file, indent=2)


def load_tasks_data() -> dict[str, Any]:
    _ensure_storage()
    try:
        with TASKS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        data = _default_tasks()

    if not isinstance(data, dict):
        data = _default_tasks()

    data.setdefault("version", 1)
    data.setdefault("active_task", "")
    data.setdefault("tasks", [])

    if not isinstance(data["tasks"], list):
        data["tasks"] = []

    return data


def save_tasks_data(data: dict[str, Any]) -> None:
    _ensure_storage()
    with TASKS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def _task_sort_key(task: dict[str, Any]) -> tuple[int, int, str]:
    priority = str(task.get("priority", "medium")).lower()
    status = str(task.get("status", "planned")).lower()
    status_rank = {
        "active": 0,
        "planned": 1,
        "blocked": 2,
        "paused": 3,
        "done": 4,
        "cancelled": 5,
    }.get(status, 9)
    updated = str(task.get("updated_at", task.get("created_at", "")))
    # Negative-ish ordering for newest by reversing later is awkward, so list_tasks sorts by this + reverse on updated separately below.
    return (PRIORITY_RANK.get(priority, 2), status_rank, updated)


def list_tasks(
    status: str = "",
    project: str = "",
    include_cancelled: bool = True,
) -> list[dict[str, Any]]:
    tasks = load_tasks_data().get("tasks", [])

    if status:
        status = status.lower().strip()
        tasks = [task for task in tasks if task.get("status") == status]

    if project:
        project_lower = project.lower().strip()
        tasks = [task for task in tasks if task.get("project", "").lower() == project_lower]

    if not include_cancelled:
        tasks = [task for task in tasks if task.get("status") != "cancelled"]

    return sorted(
        tasks,
        key=lambda task: (
            PRIORITY_RANK.get(str(task.get("priority", "medium")).lower(), 2),
            0 if task.get("status") == "active" else 1 if task.get("status") == "planned" else 2,
            str(task.get("updated_at", task.get("created_at", ""))),
        ),
    )


def resolve_task_id(task_id: str) -> str:
    token = (task_id or "").strip()
    token_lower = token.lower()
    if token_lower not in {
        "latest",
        "last",
        "latest-open",
        "latest-ready",
        "latest-active",
        "latest-planned",
        "latest-blocked",
        "latest-paused",
        "latest-done",
        "latest-completed",
    }:
        return token

    if token_lower in {"latest", "last"}:
        matches = list_tasks()
    elif token_lower == "latest-open":
        matches = [task for task in list_tasks() if task.get("status") in OPEN_STATUSES]
    elif token_lower == "latest-ready":
        matches = [task for task in list_tasks() if task.get("status") in READY_STATUSES]
    elif token_lower == "latest-active":
        matches = list_tasks(status="active")
    elif token_lower == "latest-planned":
        matches = list_tasks(status="planned")
    elif token_lower == "latest-blocked":
        matches = list_tasks(status="blocked")
    elif token_lower == "latest-paused":
        matches = list_tasks(status="paused")
    else:
        matches = list_tasks(status="done")

    if not matches:
        return ""

    return matches[0].get("id", "")


def get_task(task_id: str) -> dict[str, Any] | None:
    resolved = resolve_task_id(task_id)
    if not resolved:
        return None

    for task in load_tasks_data().get("tasks", []):
        if task.get("id") == resolved:
            return task
    return None


def _update_task_in_data(data: dict[str, Any], updated_task: dict[str, Any]) -> bool:
    for index, task in enumerate(data.get("tasks", [])):
        if task.get("id") == updated_task.get("id"):
            data["tasks"][index] = updated_task
            return True
    return False


def _active_project_name() -> str:
    project = get_active_project() or {}
    return project.get("name", "")


def add_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    status: str = "planned",
    project: str = "",
    command: str = "",
    next_action: str = "",
    linked_goal: str = "",
    risk: str = "low",
    source: str = "manual",
    source_id: str = "",
    source_category: str = "",
    follow_up_commands: list[str] | None = None,
) -> TaskMutationResult:
    title = title.strip()
    if not title:
        return TaskMutationResult(False, error="Task title is required.")

    priority = priority.lower().strip()
    if priority not in TASK_PRIORITIES:
        return TaskMutationResult(False, error=f"Invalid task priority: {priority}")

    status = status.lower().strip()
    if status not in TASK_STATUSES:
        return TaskMutationResult(False, error=f"Invalid task status: {status}")

    now = _now()
    if not project:
        project = _active_project_name()

    actions: list[str] = []
    if next_action:
        actions.append(next_action)
    elif command:
        actions.append(command)

    task = {
        "id": _new_task_id(title),
        "title": title,
        "description": description,
        "project": project,
        "status": status,
        "priority": priority,
        "risk": risk or "low",
        "command": command,
        "follow_up_commands": follow_up_commands or [],
        "next_actions": actions,
        "blockers": [],
        "notes": [],
        "linked_goal": linked_goal,
        "source": source,
        "source_id": source_id,
        "source_category": source_category,
        "created_at": now,
        "updated_at": now,
        "started_at": now if status == "active" else "",
        "completed_at": now if status == "done" else "",
    }

    data = load_tasks_data()
    data.setdefault("tasks", []).append(task)
    if status == "active":
        data["active_task"] = task["id"]
    save_tasks_data(data)

    store_memory({
        "type": "task_event",
        "content": f"Added task {task['id']}: {title}",
        "source": "task_queue",
        "task_id": task["id"],
        "status": status,
        "priority": priority,
    })

    return TaskMutationResult(True, task=task, message=f"Added task: {task['id']}")


def set_task_status(task_id: str, status: str, note: str = "") -> TaskMutationResult:
    resolved = resolve_task_id(task_id)
    if not resolved:
        return TaskMutationResult(False, error=f"Task not found: {task_id}")

    status = status.lower().strip()
    if status not in TASK_STATUSES:
        return TaskMutationResult(False, error=f"Invalid task status: {status}")

    data = load_tasks_data()
    task = None
    for existing in data.get("tasks", []):
        if existing.get("id") == resolved:
            task = existing
            break

    if not task:
        return TaskMutationResult(False, error=f"Task not found: {task_id}")

    now = _now()
    task["status"] = status
    task["updated_at"] = now
    if status == "active" and not task.get("started_at"):
        task["started_at"] = now
    if status == "done":
        task["completed_at"] = now
    if status == "active":
        data["active_task"] = task["id"]
    elif data.get("active_task") == task.get("id") and status in {"done", "cancelled"}:
        data["active_task"] = ""

    if note:
        task.setdefault("notes", []).append(f"{now}: {note}")

    _update_task_in_data(data, task)
    save_tasks_data(data)

    store_memory({
        "type": "task_event",
        "content": f"Set task {task['id']} status to {status}.",
        "source": "task_queue",
        "task_id": task["id"],
        "status": status,
    })

    return TaskMutationResult(True, task=task, message=f"Task {task['id']} status set to {status}.")


def add_task_note(task_id: str, note: str) -> TaskMutationResult:
    task = get_task(task_id)
    if not task:
        return TaskMutationResult(False, error=f"Task not found: {task_id}")
    if not note.strip():
        return TaskMutationResult(False, error="Note cannot be empty.")

    data = load_tasks_data()
    now = _now()
    task.setdefault("notes", []).append(f"{now}: {note.strip()}")
    task["updated_at"] = now
    _update_task_in_data(data, task)
    save_tasks_data(data)
    return TaskMutationResult(True, task=task, message=f"Added note to task {task['id']}.")


def add_task_next_action(task_id: str, action: str) -> TaskMutationResult:
    task = get_task(task_id)
    if not task:
        return TaskMutationResult(False, error=f"Task not found: {task_id}")
    if not action.strip():
        return TaskMutationResult(False, error="Action cannot be empty.")

    data = load_tasks_data()
    now = _now()
    task.setdefault("next_actions", []).append(action.strip())
    task["updated_at"] = now
    _update_task_in_data(data, task)
    save_tasks_data(data)
    return TaskMutationResult(True, task=task, message=f"Added next action to task {task['id']}.")


def block_task(task_id: str, reason: str) -> TaskMutationResult:
    task = get_task(task_id)
    if not task:
        return TaskMutationResult(False, error=f"Task not found: {task_id}")
    if not reason.strip():
        return TaskMutationResult(False, error="Blocker reason cannot be empty.")

    data = load_tasks_data()
    now = _now()
    task["status"] = "blocked"
    task.setdefault("blockers", []).append(reason.strip())
    task["updated_at"] = now
    if data.get("active_task") == task.get("id"):
        data["active_task"] = ""
    _update_task_in_data(data, task)
    save_tasks_data(data)

    store_memory({
        "type": "task_event",
        "content": f"Blocked task {task['id']}: {reason.strip()}",
        "source": "task_queue",
        "task_id": task["id"],
        "status": "blocked",
    })

    return TaskMutationResult(True, task=task, message=f"Blocked task {task['id']}.")


def complete_task(task_id: str, note: str = "") -> TaskMutationResult:
    return set_task_status(task_id, "done", note=note)


def start_task(task_id: str, note: str = "") -> TaskMutationResult:
    return set_task_status(task_id, "active", note=note)


def next_task() -> dict[str, Any] | None:
    ready = [task for task in list_tasks(include_cancelled=False) if task.get("status") in READY_STATUSES]
    if not ready:
        return None
    return ready[0]


def _task_exists_from_source(source_id: str, title: str) -> bool:
    title_lower = title.strip().lower()
    for task in load_tasks_data().get("tasks", []):
        if task.get("source_id") == source_id and task.get("title", "").strip().lower() == title_lower:
            return True
    return False


def queue_tasks_from_session(plan_id: str = "latest", limit: int = 6) -> dict[str, Any]:
    from session_planner import load_session_plan

    plan = load_session_plan(plan_id)
    if not plan:
        return {
            "ok": False,
            "error": f"Session plan not found: {plan_id}",
            "created": [],
            "skipped": [],
        }

    resolved_plan_id = plan.get("id", "")
    recommendations = plan.get("recommendations", []) or []
    created: list[dict[str, Any]] = []
    skipped: list[str] = []

    for recommendation in recommendations[:max(1, limit)]:
        title = str(recommendation.get("title", "")).strip()
        if not title:
            continue
        if _task_exists_from_source(resolved_plan_id, title):
            skipped.append(title)
            continue

        result = add_task(
            title=title,
            description=str(recommendation.get("rationale", "")),
            priority=str(recommendation.get("priority", "medium")),
            status="planned",
            project=(plan.get("active_project") or {}).get("name", ""),
            command=str(recommendation.get("recommended_command", "")),
            linked_goal=str(recommendation.get("linked_goal", "")),
            risk=str(recommendation.get("risk", "low")),
            source="session_plan",
            source_id=resolved_plan_id,
            source_category=str(recommendation.get("category", "")),
            follow_up_commands=list(recommendation.get("follow_up_commands", []) or []),
        )
        if result.ok and result.task:
            created.append(result.task)

    store_memory({
        "type": "task_queue_event",
        "content": f"Queued {len(created)} task(s) from session plan {resolved_plan_id}. Skipped {len(skipped)} duplicate(s).",
        "source": "task_queue",
        "session_plan_id": resolved_plan_id,
        "created_count": len(created),
        "skipped_count": len(skipped),
    })

    return {
        "ok": True,
        "plan_id": resolved_plan_id,
        "created": created,
        "skipped": skipped,
    }


def task_status_counts() -> dict[str, int]:
    counts = {status: 0 for status in sorted(TASK_STATUSES)}
    for task in load_tasks_data().get("tasks", []):
        status = task.get("status", "planned")
        counts[status] = counts.get(status, 0) + 1
    return counts


def task_context_text(limit: int = 6) -> str:
    tasks = [task for task in list_tasks(include_cancelled=False) if task.get("status") in OPEN_STATUSES]
    lines = ["Task queue context:"]
    if not tasks:
        lines.append("- No open tasks found.")
        return "\n".join(lines)

    for task in tasks[:limit]:
        lines.append(f"- {task.get('id')} | {task.get('priority')} | {task.get('status')} | {task.get('title')}")
        if task.get("command"):
            lines.append(f"  command: {task.get('command')}")
        for action in (task.get("next_actions") or [])[:2]:
            lines.append(f"  next: {action}")
    return "\n".join(lines)


def _task_brief(task: dict[str, Any]) -> str:
    return (
        f"{task.get('id')} | {task.get('priority')} | {task.get('status')} | "
        f"{task.get('project') or '[no project]'} | {task.get('title')}"
    )


def task_detail_text(task: dict[str, Any], full: bool = False) -> str:
    lines: list[str] = []
    lines.append(f"# Task: {task.get('id')}")
    lines.append(f"Title: {task.get('title')}")
    lines.append(f"Status: {task.get('status')}")
    lines.append(f"Priority: {task.get('priority')}")
    lines.append(f"Risk: {task.get('risk')}")
    lines.append(f"Project: {task.get('project') or '[none]'}")
    if task.get("linked_goal"):
        lines.append(f"Linked goal: {task.get('linked_goal')}")
    if task.get("source"):
        lines.append(f"Source: {task.get('source')} {task.get('source_id') or ''}".strip())
    lines.append(f"Created: {task.get('created_at')}")
    lines.append(f"Updated: {task.get('updated_at')}")
    if task.get("description"):
        lines.append("")
        lines.append("## Description")
        lines.append(task.get("description", ""))
    if task.get("command"):
        lines.append("")
        lines.append("## Recommended command")
        lines.append(task.get("command", ""))
    if task.get("follow_up_commands"):
        lines.append("")
        lines.append("## Follow-up commands")
        for command in task.get("follow_up_commands", []):
            lines.append(f"- {command}")
    if task.get("next_actions"):
        lines.append("")
        lines.append("## Next actions")
        for action in task.get("next_actions", []):
            lines.append(f"- {action}")
    if task.get("blockers"):
        lines.append("")
        lines.append("## Blockers")
        for blocker in task.get("blockers", []):
            lines.append(f"- {blocker}")
    if full and task.get("notes"):
        lines.append("")
        lines.append("## Notes")
        for note in task.get("notes", []):
            lines.append(f"- {note}")
    if full and task.get("execution_history"):
        lines.append("")
        lines.append("## Execution history")
        for entry in (task.get("execution_history") or [])[-5:]:
            lines.append(
                f"- {entry.get('executed_at')} | "
                f"dry_run={entry.get('dry_run')} | "
                f"ok={entry.get('ok')} | "
                f"return_code={entry.get('return_code')} | "
                f"{entry.get('command')}"
            )
    return "\n".join(lines)


def print_task_status() -> None:
    data = load_tasks_data()
    counts = task_status_counts()
    print("# Task Queue Status")
    print(f"Active task: {data.get('active_task') or '[none]'}")
    for status in sorted(counts):
        print(f"{status}: {counts[status]}")
    print()
    task = next_task()
    if task:
        print("Next task:")
        print(_task_brief(task))
        if task.get("command"):
            print(f"Command: {task.get('command')}")
    else:
        print("No ready tasks found.")


def print_task_list(status: str = "", project: str = "", include_cancelled: bool = True) -> None:
    tasks = list_tasks(status=status, project=project, include_cancelled=include_cancelled)
    if not tasks:
        print("No tasks found.")
        return
    for task in tasks:
        print(_task_brief(task))
        if task.get("command"):
            print(f"  command: {task.get('command')}")


def print_task_detail(task_id: str, full: bool = False) -> None:
    task = get_task(task_id)
    if not task:
        print(f"Task not found: {task_id}")
        return
    print(task_detail_text(task, full=full))


def print_add_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    status: str = "planned",
    project: str = "",
    command: str = "",
    next_action: str = "",
    linked_goal: str = "",
    risk: str = "low",
) -> None:
    result = add_task(
        title=title,
        description=description,
        priority=priority,
        status=status,
        project=project,
        command=command,
        next_action=next_action,
        linked_goal=linked_goal,
        risk=risk,
    )
    if not result.ok:
        print(f"Could not add task: {result.error}")
        return
    print(result.message)
    if result.task:
        print(task_detail_text(result.task))


def print_set_task_status(task_id: str, status: str, note: str = "") -> None:
    result = set_task_status(task_id, status, note=note)
    if not result.ok:
        print(f"Could not update task: {result.error}")
        return
    print(result.message)


def print_add_task_note(task_id: str, note: str) -> None:
    result = add_task_note(task_id, note)
    if not result.ok:
        print(f"Could not add task note: {result.error}")
        return
    print(result.message)


def print_add_task_action(task_id: str, action: str) -> None:
    result = add_task_next_action(task_id, action)
    if not result.ok:
        print(f"Could not add task action: {result.error}")
        return
    print(result.message)


def print_block_task(task_id: str, reason: str) -> None:
    result = block_task(task_id, reason)
    if not result.ok:
        print(f"Could not block task: {result.error}")
        return
    print(result.message)


def print_complete_task(task_id: str, note: str = "") -> None:
    result = complete_task(task_id, note=note)
    if not result.ok:
        print(f"Could not complete task: {result.error}")
        return
    print(result.message)


def print_start_task(task_id: str, note: str = "") -> None:
    result = start_task(task_id, note=note)
    if not result.ok:
        print(f"Could not start task: {result.error}")
        return
    print(result.message)


def print_next_task() -> None:
    task = next_task()
    if not task:
        print("No ready tasks found.")
        return
    print(task_detail_text(task, full=True))


def print_queue_from_session(plan_id: str = "latest", limit: int = 6) -> None:
    result = queue_tasks_from_session(plan_id=plan_id, limit=limit)
    if not result.get("ok"):
        print(f"Could not queue tasks: {result.get('error')}")
        return
    print(f"Queued {len(result.get('created', []))} task(s) from session plan {result.get('plan_id')}.")
    if result.get("skipped"):
        print(f"Skipped {len(result.get('skipped', []))} duplicate(s).")
    for task in result.get("created", []):
        print(_task_brief(task))
        if task.get("command"):
            print(f"  command: {task.get('command')}")
