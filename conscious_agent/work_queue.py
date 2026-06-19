from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from paths import DATA_DIR


QUEUE_DIR = DATA_DIR / "work_queue"
QUEUE_FILE = QUEUE_DIR / "work_items.json"


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_queue_file() -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    if not QUEUE_FILE.exists():
        QUEUE_FILE.write_text("[]", encoding="utf-8")


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

        timestamp = now_iso()

        return WorkItem(
            id=f"work_{uuid.uuid4().hex[:12]}",
            title=title.strip(),
            description=description.strip(),
            project_id=project_id.strip() or "default",
            status="pending",
            priority=clamp_priority(priority),
            risk=risk,
            source=source,
            requires_approval=bool(requires_approval),
            created_at=timestamp,
            updated_at=timestamp,
            metadata=metadata or {},
        )

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WorkItem":
        return WorkItem(
            id=str(data.get("id", f"work_{uuid.uuid4().hex[:12]}")),
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


def normalize_status(status: str) -> str:
    status = status.strip().lower()

    if status not in VALID_STATUSES:
        return "pending"

    return status


def normalize_risk(risk: str) -> str:
    risk = risk.strip().lower()

    if risk not in VALID_RISKS:
        return "low"

    return risk


def normalize_source(source: str) -> str:
    source = source.strip().lower()

    if source not in VALID_SOURCES:
        return "user"

    return source


def load_work_items() -> List[WorkItem]:
    ensure_queue_file()

    try:
        raw = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = QUEUE_FILE.with_suffix(".broken.json")
        backup.write_text(QUEUE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        QUEUE_FILE.write_text("[]", encoding="utf-8")
        raw = []

    if not isinstance(raw, list):
        raw = []

    return [WorkItem.from_dict(item) for item in raw if isinstance(item, dict)]


def save_work_items(items: List[WorkItem]) -> None:
    ensure_queue_file()

    data = [item.to_dict() for item in items]
    QUEUE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


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

    items = load_work_items()

    item = WorkItem.create(
        title=title,
        description=description,
        project_id=project_id,
        priority=priority,
        risk=risk,
        source=source,
        requires_approval=requires_approval,
        metadata=metadata,
    )

    items.append(item)
    save_work_items(items)

    return item


def find_work_item(item_id: str) -> Optional[WorkItem]:
    item_id = item_id.strip()

    for item in load_work_items():
        if item.id == item_id:
            return item

    return None


def update_work_item(item_id: str, **updates: Any) -> Optional[WorkItem]:
    items = load_work_items()
    updated_item: Optional[WorkItem] = None

    for index, item in enumerate(items):
        if item.id != item_id:
            continue

        for key, value in updates.items():
            if not hasattr(item, key):
                continue

            if key == "status":
                value = normalize_status(str(value))
            elif key == "risk":
                value = normalize_risk(str(value))
            elif key == "source":
                value = normalize_source(str(value))
            elif key == "priority":
                value = clamp_priority(value)

            setattr(item, key, value)

        item.updated_at = now_iso()

        if item.status == "active" and item.started_at is None:
            item.started_at = now_iso()

        if item.status in {"done", "failed", "cancelled"} and item.completed_at is None:
            item.completed_at = now_iso()

        items[index] = item
        updated_item = item
        break

    if updated_item is not None:
        save_work_items(items)

    return updated_item


def delete_work_item(item_id: str) -> bool:
    items = load_work_items()
    kept = [item for item in items if item.id != item_id]

    if len(kept) == len(items):
        return False

    save_work_items(kept)
    return True


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
        items = [
            item for item in items
            if item.status not in {"done", "cancelled"}
        ]

    if project_id:
        items = [item for item in items if item.project_id == project_id]

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

    safe_candidates = [
        item for item in candidates
        if not item.requires_approval and item.risk == "low"
    ]

    if safe_candidates:
        return sorted(safe_candidates, key=lambda item: (-item.priority, item.created_at))[0]

    if candidates:
        return sorted(candidates, key=lambda item: (-item.priority, item.created_at))[0]

    return None


def summarize_queue(project_id: Optional[str] = None) -> Dict[str, Any]:
    items = load_work_items()

    if project_id:
        items = [item for item in items if item.project_id == project_id]

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
    parser = argparse.ArgumentParser(description="Eidolon self-directed work queue")

    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a new work item")
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

    delete_parser = subparsers.add_parser("delete", help="Delete a work item")
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

        print("Added work item:")
        print(format_work_item(item, full=True))
        return 0

    if args.command == "list":
        items = list_work_items(
            status=args.status,
            project_id=args.project,
            include_done=args.include_done,
        )
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

        print("Updated work item:")
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
        item = update_work_item(
            args.id,
            status="blocked",
            blocked_reason=args.reason,
        )

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

        print(f"Deleted work item: {args.id}")
        return 0

    if args.command == "summary":
        summary = summarize_queue(project_id=args.project)
        print(json.dumps(summary, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
