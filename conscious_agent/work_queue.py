from __future__ import annotations

"""
Legacy work-queue compatibility layer.

v5.1 consolidation note:
    The task queue (data/tasks.json via task_queue.py) is now Eidolon's single
    source of truth for task/work state. This module preserves the v4.6-v5.0
    WorkItem API and CLI so existing dashboard/API/work-cycle code keeps working,
    but all reads and writes are mapped to task_queue.py.

Translation:
    work status "pending" -> task status "planned"
    task status "planned" -> work status "pending"

So yes, this is now an adapter instead of yet another tiny kingdom with its own
JSON file. Civilization may recover.
"""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from task_queue import (
    add_task,
    delete_task,
    get_task,
    list_tasks,
    load_tasks_data,
    resolve_task_id,
    update_task_fields,
)

VALID_STATUSES = {
    "pending",
    "active",
    "blocked",
    "done",
    "failed",
    "cancelled",
}

VALID_RISKS = {
    "low",
    "medium",
    "high",
}

VALID_SOURCES = {
    "user",
    "eidolon",
    "system",
    "dashboard",
}

WORK_TO_TASK_STATUS = {
    "pending": "planned",
    "active": "active",
    "blocked": "blocked",
    "done": "done",
    "failed": "blocked",
    "cancelled": "cancelled",
}

TASK_TO_WORK_STATUS = {
    "planned": "pending",
    "active": "active",
    "blocked": "blocked",
    "paused": "blocked",
    "done": "done",
    "cancelled": "cancelled",
}

PRIORITY_TO_NUMBER = {
    "critical": 10,
    "high": 8,
    "medium": 5,
    "low": 2,
}

NUMBER_TO_PRIORITY = [
    (9, "critical"),
    (7, "high"),
    (4, "medium"),
    (1, "low"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkItem:
    id: str
    title: str
    description: str = ""
    project_id: str = "default"
    status: str = "pending"
    priority: int = 5
    risk: str = "low"
    source: str = "user"
    requires_approval: bool = False
    created_at: str = ""
    updated_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    blocked_reason: Optional[str] = None
    result: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @staticmethod
    def create(
        title: str,
        description: str = "",
        project_id: str = "default",
        priority: int = 5,
        risk: str = "low",
        source: str = "user",
        requires_approval: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "WorkItem":
        risk = normalize_risk(risk)
        source = normalize_source(source)
        if requires_approval is None:
            requires_approval = risk in {"medium", "high"}
        return WorkItem(
            id="",
            title=title.strip(),
            description=description.strip(),
            project_id=project_id.strip() or "default",
            status="pending",
            priority=clamp_priority(priority),
            risk=risk,
            source=source,
            requires_approval=bool(requires_approval),
            created_at=now_iso(),
            updated_at=now_iso(),
            metadata=metadata or {},
        )

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WorkItem":
        return WorkItem(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")).strip(),
            description=str(data.get("description", "")).strip(),
            project_id=str(data.get("project_id", "default")).strip() or "default",
            status=normalize_status(str(data.get("status", "pending"))),
            priority=clamp_priority(data.get("priority", 5)),
            risk=normalize_risk(str(data.get("risk", "low"))),
            source=normalize_source(str(data.get("source", "user"))),
            requires_approval=bool(data.get("requires_approval", False)),
            created_at=str(data.get("created_at", now_iso())),
            updated_at=str(data.get("updated_at", now_iso())),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            blocked_reason=data.get("blocked_reason"),
            result=data.get("result"),
            metadata=data.get("metadata") or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def clamp_priority(value: Any) -> int:
    try:
        priority = int(value)
    except (TypeError, ValueError):
        priority = 5
    return max(1, min(10, priority))


def _number_to_task_priority(value: Any) -> str:
    priority = clamp_priority(value)
    for threshold, label in NUMBER_TO_PRIORITY:
        if priority >= threshold:
            return label
    return "medium"


def _task_priority_to_number(value: Any) -> int:
    return PRIORITY_TO_NUMBER.get(str(value or "medium").lower().strip(), 5)


def normalize_status(status: str) -> str:
    status = status.strip().lower()
    return status if status in VALID_STATUSES else "pending"


def normalize_risk(risk: str) -> str:
    risk = risk.strip().lower()
    if risk == "critical":
        return "high"
    return risk if risk in VALID_RISKS else "low"


def normalize_source(source: str) -> str:
    source = source.strip().lower()
    return source if source in VALID_SOURCES else "user"


def _work_status_from_task(task: dict[str, Any]) -> str:
    # Use the task status as truth. The optional work_status field is only for
    # compatibility-only states that task_queue.py does not have, such as failed.
    explicit = str(task.get("work_status") or "").strip().lower()
    if explicit == "failed":
        return "failed"
    return TASK_TO_WORK_STATUS.get(str(task.get("status", "planned")).lower(), "pending")


def _task_status_from_work(status: str) -> str:
    return WORK_TO_TASK_STATUS.get(normalize_status(status), "planned")


def _blocked_reason_from_task(task: dict[str, Any]) -> Optional[str]:
    blockers = task.get("blockers") or []
    if blockers:
        return str(blockers[-1])
    return None


def _task_to_work_item(task: dict[str, Any]) -> WorkItem:
    metadata = dict(task.get("metadata") or {})
    if task.get("patch_id"):
        metadata.setdefault("patch_id", task.get("patch_id"))
    if task.get("patch_status"):
        metadata.setdefault("patch_status", task.get("patch_status"))
    if task.get("command"):
        metadata.setdefault("command", task.get("command"))

    return WorkItem(
        id=str(task.get("id", "")),
        title=str(task.get("title", "")),
        description=str(task.get("description", "")),
        project_id=str(task.get("project") or "default"),
        status=_work_status_from_task(task),
        priority=_task_priority_to_number(task.get("priority")),
        risk=normalize_risk(str(task.get("risk", "low"))),
        source=normalize_source(str(task.get("source", "user"))),
        requires_approval=bool(task.get("requires_approval", False)),
        created_at=str(task.get("created_at", "")),
        updated_at=str(task.get("updated_at", "")),
        started_at=task.get("started_at") or None,
        completed_at=task.get("completed_at") or None,
        blocked_reason=_blocked_reason_from_task(task),
        result=task.get("result") or None,
        metadata=metadata,
    )


def _work_updates_to_task_updates(updates: dict[str, Any]) -> dict[str, Any]:
    converted: dict[str, Any] = {}
    metadata_updates: dict[str, Any] = {}

    for key, value in updates.items():
        if key == "status":
            status = normalize_status(str(value))
            converted["status"] = _task_status_from_work(status)
            converted["work_status"] = status if status == "failed" else ""
            metadata_updates["work_status"] = status
        elif key == "priority":
            converted["priority"] = _number_to_task_priority(value)
        elif key == "project_id":
            converted["project"] = str(value)
        elif key == "source":
            converted["source"] = normalize_source(str(value))
        elif key == "metadata":
            if isinstance(value, dict):
                metadata_updates.update(value)
        elif key == "blocked_reason":
            converted["blocked_reason"] = str(value)
        elif key == "result":
            converted["result"] = str(value)
        elif key == "risk":
            converted["risk"] = normalize_risk(str(value))
        elif key == "requires_approval":
            converted["requires_approval"] = bool(value)
        elif key in {"title", "description"}:
            converted[key] = str(value)
        elif key in {"patch_id", "patch_status"}:
            converted[key] = str(value)
            metadata_updates[key] = str(value)

    if metadata_updates:
        converted["metadata"] = metadata_updates
    return converted


def load_work_items() -> List[WorkItem]:
    return [_task_to_work_item(task) for task in load_tasks_data().get("tasks", []) if isinstance(task, dict)]


def save_work_items(items: List[WorkItem]) -> None:
    """Compatibility shim.

    Full replacement saves are intentionally not supported because task_queue.py is
    now the canonical store. Update individual items through add/update/delete.
    """
    for item in items:
        if item.id and get_task(item.id):
            update_work_item(item.id, **item.to_dict())
        else:
            add_work_item(
                title=item.title,
                description=item.description,
                project_id=item.project_id,
                priority=item.priority,
                risk=item.risk,
                source=item.source,
                requires_approval=item.requires_approval,
                metadata=item.metadata,
            )


def add_work_item(
    title: str,
    description: str = "",
    project_id: str = "default",
    priority: int = 5,
    risk: str = "low",
    source: str = "user",
    requires_approval: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkItem:
    if not title or not title.strip():
        raise ValueError("Work item title cannot be empty.")

    risk = normalize_risk(risk)
    metadata = dict(metadata or {})
    metadata.setdefault("compatibility_layer", "work_queue")
    metadata.setdefault("work_status", "pending")

    result = add_task(
        title=title,
        description=description,
        project=project_id,
        priority=_number_to_task_priority(priority),
        status="planned",
        risk=risk,
        source=normalize_source(source),
        source_category="work_queue_compat",
        requires_approval=requires_approval,
        metadata=metadata,
        patch_id=str(metadata.get("patch_id", "")),
        patch_status=str(metadata.get("patch_status", "")),
        work_status="pending",
    )
    if not result.ok or not result.task:
        raise ValueError(result.error or "Could not create task-backed work item.")
    return _task_to_work_item(result.task)


def find_work_item(item_id: str) -> Optional[WorkItem]:
    task = get_task(item_id.strip())
    if not task:
        return None
    return _task_to_work_item(task)


def update_work_item(item_id: str, **updates: Any) -> Optional[WorkItem]:
    converted = _work_updates_to_task_updates(updates)
    result = update_task_fields(item_id, **converted)
    if not result.ok or not result.task:
        return None
    return _task_to_work_item(result.task)


def delete_work_item(item_id: str) -> bool:
    result = delete_task(item_id)
    return result.ok


def list_work_items(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    include_done: bool = False,
) -> List[WorkItem]:
    items = load_work_items()

    if status:
        normalized_status = normalize_status(status)
        items = [item for item in items if item.status == normalized_status]
    elif not include_done:
        items = [item for item in items if item.status not in {"done", "cancelled"}]

    if project_id:
        project_lower = project_id.lower().strip()
        items = [item for item in items if item.project_id.lower() == project_lower]

    return sorted(
        items,
        key=lambda item: (
            status_sort_weight(item.status),
            -item.priority,
            item.created_at,
        ),
    )


def status_sort_weight(status: str) -> int:
    weights = {
        "active": 0,
        "pending": 1,
        "blocked": 2,
        "failed": 3,
        "done": 4,
        "cancelled": 5,
    }
    return weights.get(status, 99)


def get_next_work_item(project_id: Optional[str] = None) -> Optional[WorkItem]:
    candidates = list_work_items(status="pending", project_id=project_id, include_done=False)
    safe_candidates = [item for item in candidates if not item.requires_approval and item.risk == "low"]
    if safe_candidates:
        return sorted(safe_candidates, key=lambda item: (-item.priority, item.created_at))[0]
    if candidates:
        return sorted(candidates, key=lambda item: (-item.priority, item.created_at))[0]
    return None


def summarize_queue(project_id: Optional[str] = None) -> Dict[str, Any]:
    items = load_work_items()
    if project_id:
        items = [item for item in items if item.project_id.lower() == project_id.lower().strip()]

    summary = {
        "total": len(items),
        "pending": 0,
        "active": 0,
        "blocked": 0,
        "done": 0,
        "failed": 0,
        "cancelled": 0,
        "approval_required": 0,
        "next_item": None,
        "canonical_store": "data/tasks.json",
        "compatibility_layer": "work_queue.py",
    }

    for item in items:
        if item.status in summary:
            summary[item.status] += 1
        if item.requires_approval and item.status not in {"done", "cancelled"}:
            summary["approval_required"] += 1

    next_item = get_next_work_item(project_id=project_id)
    if next_item:
        summary["next_item"] = next_item.to_dict()
    return summary


def format_work_item(item: WorkItem, full: bool = False) -> str:
    approval = "approval required" if item.requires_approval else "safe"
    header = (
        f"{item.id} | {item.status.upper()} | p{item.priority} | "
        f"{item.risk} risk | {approval}"
    )
    lines = [
        header,
        "Canonical store: task_queue.py / data/tasks.json",
        f"Project: {item.project_id}",
        f"Title: {item.title}",
    ]
    if item.description:
        lines.append(f"Description: {item.description}")
    if item.blocked_reason:
        lines.append(f"Blocked: {item.blocked_reason}")
    if item.result:
        lines.append(f"Result: {item.result}")
    if full:
        lines.extend([
            f"Source: {item.source}",
            f"Created: {item.created_at}",
            f"Updated: {item.updated_at}",
            f"Started: {item.started_at}",
            f"Completed: {item.completed_at}",
            f"Metadata: {json.dumps(item.metadata or {}, indent=2)}",
        ])
    return "\n".join(lines)


def print_work_items(items: List[WorkItem], full: bool = False) -> None:
    if not items:
        print("No work items found.")
        return
    for item in items:
        print(format_work_item(item, full=full))
        print("-" * 72)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Eidolon work queue compatibility CLI backed by task_queue.py"
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a new task-backed work item")
    add_parser.add_argument("title", help="Work item title")
    add_parser.add_argument("--description", default="", help="Longer description")
    add_parser.add_argument("--project", default="default", help="Project id")
    add_parser.add_argument("--priority", type=int, default=5, help="Priority 1-10")
    add_parser.add_argument("--risk", default="low", choices=sorted(VALID_RISKS))
    add_parser.add_argument("--source", default="user", choices=sorted(VALID_SOURCES))
    add_parser.add_argument("--requires-approval", action="store_true")

    list_parser = subparsers.add_parser("list", help="List work items")
    list_parser.add_argument("--status", choices=sorted(VALID_STATUSES))
    list_parser.add_argument("--project", default=None)
    list_parser.add_argument("--include-done", action="store_true")
    list_parser.add_argument("--full", action="store_true")

    show_parser = subparsers.add_parser("show", help="Show one work item")
    show_parser.add_argument("id")
    show_parser.add_argument("--full", action="store_true")

    next_parser = subparsers.add_parser("next", help="Show next work item")
    next_parser.add_argument("--project", default=None)
    next_parser.add_argument("--full", action="store_true")

    update_parser = subparsers.add_parser("update", help="Update a work item")
    update_parser.add_argument("id")
    update_parser.add_argument("--title")
    update_parser.add_argument("--description")
    update_parser.add_argument("--project")
    update_parser.add_argument("--status", choices=sorted(VALID_STATUSES))
    update_parser.add_argument("--priority", type=int)
    update_parser.add_argument("--risk", choices=sorted(VALID_RISKS))
    update_parser.add_argument("--requires-approval", choices=["true", "false"])
    update_parser.add_argument("--blocked-reason")
    update_parser.add_argument("--result")

    done_parser = subparsers.add_parser("done", help="Mark a work item done")
    done_parser.add_argument("id")
    done_parser.add_argument("--result", default="Completed.")

    fail_parser = subparsers.add_parser("fail", help="Mark a work item failed")
    fail_parser.add_argument("id")
    fail_parser.add_argument("--result", default="Failed.")

    block_parser = subparsers.add_parser("block", help="Mark a work item blocked")
    block_parser.add_argument("id")
    block_parser.add_argument("--reason", required=True)

    delete_parser = subparsers.add_parser("delete", help="Delete a work item/task")
    delete_parser.add_argument("id")

    summary_parser = subparsers.add_parser("summary", help="Show queue summary")
    summary_parser.add_argument("--project", default=None)

    return parser


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        item = add_work_item(
            title=args.title,
            description=args.description,
            project_id=args.project,
            priority=args.priority,
            risk=args.risk,
            source=args.source,
            requires_approval=args.requires_approval,
        )
        print("Added task-backed work item:")
        print(format_work_item(item, full=True))
        return 0

    if args.command == "list":
        items = list_work_items(status=args.status, project_id=args.project, include_done=args.include_done)
        print_work_items(items, full=args.full)
        return 0

    if args.command == "show":
        item = find_work_item(args.id)
        if not item:
            print(f"No work item found with id: {args.id}")
            return 1
        print(format_work_item(item, full=args.full))
        return 0

    if args.command == "next":
        item = get_next_work_item(project_id=args.project)
        if not item:
            print("No pending work item found.")
            return 0
        print(format_work_item(item, full=args.full))
        return 0

    if args.command == "update":
        updates: Dict[str, Any] = {}
        if args.title is not None:
            updates["title"] = args.title
        if args.description is not None:
            updates["description"] = args.description
        if args.project is not None:
            updates["project_id"] = args.project
        if args.status is not None:
            updates["status"] = args.status
        if args.priority is not None:
            updates["priority"] = args.priority
        if args.risk is not None:
            updates["risk"] = args.risk
        if args.requires_approval is not None:
            updates["requires_approval"] = args.requires_approval == "true"
        if args.blocked_reason is not None:
            updates["blocked_reason"] = args.blocked_reason
        if args.result is not None:
            updates["result"] = args.result
        item = update_work_item(args.id, **updates)
        if not item:
            print(f"No work item found with id: {args.id}")
            return 1
        print("Updated task-backed work item:")
        print(format_work_item(item, full=True))
        return 0

    if args.command == "done":
        item = update_work_item(args.id, status="done", result=args.result)
        if not item:
            print(f"No work item found with id: {args.id}")
            return 1
        print("Marked done:")
        print(format_work_item(item, full=True))
        return 0

    if args.command == "fail":
        item = update_work_item(args.id, status="failed", result=args.result)
        if not item:
            print(f"No work item found with id: {args.id}")
            return 1
        print("Marked failed:")
        print(format_work_item(item, full=True))
        return 0

    if args.command == "block":
        item = update_work_item(args.id, status="blocked", blocked_reason=args.reason)
        if not item:
            print(f"No work item found with id: {args.id}")
            return 1
        print("Marked blocked:")
        print(format_work_item(item, full=True))
        return 0

    if args.command == "delete":
        deleted = delete_work_item(args.id)
        if not deleted:
            print(f"No work item found with id: {args.id}")
            return 1
        print(f"Deleted work item/task: {resolve_task_id(args.id) or args.id}")
        return 0

    if args.command == "summary":
        print(json.dumps(summarize_queue(project_id=args.project), indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
