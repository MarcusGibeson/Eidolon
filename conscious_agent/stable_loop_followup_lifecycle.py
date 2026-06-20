from __future__ import annotations

"""Lifecycle integration for stable-loop decision follow-up tasks.

v6.7 note:
    v6.6 could create canonical tasks from stable-loop final decisions.
    v6.7 makes those tasks visible as follow-ups in task lifecycle views and
    gives operators a safe way to mark the originating stable-loop decision
    follow-up chain resolved once the follow-up tasks are finished.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from stable_loop_decision_report import decision_label, final_decision_for_loop
from stable_loop_operator_notes import ensure_operator_notes, summarize_operator_notes
from stable_loop_review import set_stable_loop_archived
from stable_supervised_loop import load_stable_loop, save_stable_loop
from task_lifecycle import derive_task_lifecycle
from task_queue import get_task, list_tasks, update_task_fields

FOLLOWUP_LIFECYCLE_VERSION = "6.9"
FOLLOWUP_SOURCE = "stable_loop_decision"
FOLLOWUP_CATEGORY = "stable_loop_followup"
TERMINAL_TASK_STATUSES = {"done", "cancelled"}


@dataclass
class FollowupLifecycleResult:
    ok: bool
    loop_id: str = ""
    task_id: str = ""
    resolved: bool = False
    archived: bool = False
    task_ids: list[str] | None = None
    open_task_ids: list[str] | None = None
    message: str = ""
    error: str = ""
    row: dict[str, Any] | None = None
    loop: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _metadata(task: dict[str, Any] | None) -> dict[str, Any]:
    raw = (task or {}).get("metadata") if isinstance(task, dict) else {}
    return dict(raw) if isinstance(raw, dict) else {}


def is_stable_loop_followup_task(task: dict[str, Any] | None) -> bool:
    if not isinstance(task, dict):
        return False
    metadata = _metadata(task)
    return bool(
        task.get("source_category") == FOLLOWUP_CATEGORY
        or task.get("source") == FOLLOWUP_SOURCE
        or metadata.get("source") == FOLLOWUP_SOURCE
        or metadata.get("stable_loop_id")
    )


def stable_loop_id_for_task(task: dict[str, Any] | None) -> str:
    metadata = _metadata(task)
    if metadata.get("stable_loop_id"):
        return str(metadata.get("stable_loop_id") or "").strip()
    if not isinstance(task, dict):
        return ""
    if task.get("source_category") == FOLLOWUP_CATEGORY or task.get("source") == FOLLOWUP_SOURCE or metadata.get("source") == FOLLOWUP_SOURCE:
        return str(task.get("source_id") or "").strip()
    return ""


def followup_kind_for_task(task: dict[str, Any] | None) -> str:
    metadata = _metadata(task)
    return str(metadata.get("followup_kind") or "").strip()


def final_decision_for_task(task: dict[str, Any] | None) -> str:
    metadata = _metadata(task)
    return str(metadata.get("final_decision") or "").strip() or "undecided"


def stable_loop_followup_tasks(loop_id: str, include_closed: bool = True) -> list[dict[str, Any]]:
    resolved = str(loop_id or "").strip()
    rows: list[dict[str, Any]] = []
    for task in list_tasks(include_cancelled=True):
        if not is_stable_loop_followup_task(task):
            continue
        if stable_loop_id_for_task(task) != resolved:
            continue
        if not include_closed and str(task.get("status") or "") in TERMINAL_TASK_STATUSES:
            continue
        rows.append(task)
    return rows


def stable_loop_followup_task_row(task: dict[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(task, str):
        task = get_task(task)
    if not task:
        return {
            "ok": False,
            "task_id": str(task or ""),
            "is_stable_loop_followup": False,
            "message": "Task not found.",
        }

    metadata = _metadata(task)
    loop_id = stable_loop_id_for_task(task)
    loop = load_stable_loop(loop_id) if loop_id else None
    lifecycle = derive_task_lifecycle(task)
    task_status = str(task.get("status") or "")
    loop_notes = ensure_operator_notes(loop, save=False) if loop else {}
    resolution = loop_notes.get("decision_followup_resolution") if isinstance(loop_notes.get("decision_followup_resolution"), dict) else {}
    decision = final_decision_for_task(task)
    if loop:
        decision = final_decision_for_loop(loop) or decision

    row = {
        "ok": True,
        "task_id": str(task.get("id") or ""),
        "title": str(task.get("title") or ""),
        "status": task_status,
        "priority": str(task.get("priority") or ""),
        "risk": str(task.get("risk") or ""),
        "is_stable_loop_followup": is_stable_loop_followup_task(task),
        "stable_loop_id": loop_id,
        "stable_loop_exists": bool(loop),
        "stable_loop_live": bool((loop or {}).get("live")),
        "stable_loop_archived": bool((loop or {}).get("archived")),
        "final_decision": decision,
        "final_decision_label": decision_label(decision),
        "followup_kind": followup_kind_for_task(task),
        "source": str(task.get("source") or metadata.get("source") or ""),
        "source_category": str(task.get("source_category") or ""),
        "terminal": task_status in TERMINAL_TASK_STATUSES,
        "open": task_status not in TERMINAL_TASK_STATUSES,
        "lifecycle": lifecycle,
        "lifecycle_stage": str(lifecycle.get("stage") or "unknown"),
        "lifecycle_label": str(lifecycle.get("stage_label") or "Unknown"),
        "resolution_status": str(resolution.get("status") or "open"),
        "resolution": resolution,
        "metadata": metadata,
    }
    if not row["is_stable_loop_followup"]:
        row["message"] = "Task is not a stable-loop decision follow-up task."
    return row


def list_stable_loop_followup_task_rows(
    decision_filter: str = "all",
    include_closed: bool = True,
    include_archived: bool = False,
    loop_id: str = "",
) -> list[dict[str, Any]]:
    decision_token = str(decision_filter or "all").strip().lower().replace("-", "_").replace(" ", "_")
    rows: list[dict[str, Any]] = []
    for task in list_tasks(include_cancelled=True):
        if not is_stable_loop_followup_task(task):
            continue
        if loop_id and stable_loop_id_for_task(task) != loop_id:
            continue
        row = stable_loop_followup_task_row(task)
        if not include_closed and row.get("terminal"):
            continue
        if row.get("stable_loop_archived") and not include_archived:
            continue
        decision = str(row.get("final_decision") or "undecided")
        if decision_token not in {"", "all", "any"}:
            if decision_token == "action_required" and decision not in {"fix_forward", "rollback", "needs_review"}:
                continue
            if decision_token not in {"action_required", decision}:
                continue
        rows.append(row)
    return sorted(rows, key=lambda item: (item.get("stable_loop_id", ""), item.get("terminal", False), item.get("task_id", "")))


def stable_loop_followup_lifecycle_summary(
    decision_filter: str = "all",
    include_closed: bool = True,
    include_archived: bool = False,
    loop_id: str = "",
) -> dict[str, Any]:
    requested_loop_id = loop_id
    rows = list_stable_loop_followup_task_rows(decision_filter=decision_filter, include_closed=include_closed, include_archived=include_archived, loop_id=requested_loop_id)
    loops: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_loop_id = str(row.get("stable_loop_id") or "")
        if not row_loop_id:
            continue
        item = loops.setdefault(row_loop_id, {
            "loop_id": row_loop_id,
            "final_decision": row.get("final_decision", "undecided"),
            "final_decision_label": row.get("final_decision_label", "Undecided"),
            "task_ids": [],
            "open_task_ids": [],
            "done_task_ids": [],
            "resolution_status": row.get("resolution_status", "open"),
            "archived": row.get("stable_loop_archived", False),
        })
        task_id = str(row.get("task_id") or "")
        if task_id:
            item["task_ids"].append(task_id)
            if row.get("terminal"):
                item["done_task_ids"].append(task_id)
            else:
                item["open_task_ids"].append(task_id)
    return {
        "version": FOLLOWUP_LIFECYCLE_VERSION,
        "generated_at": _now(),
        "decision_filter": decision_filter,
        "loop_id": requested_loop_id,
        "include_closed": include_closed,
        "include_archived": include_archived,
        "total_followup_tasks": len(rows),
        "open_followup_tasks": sum(1 for row in rows if row.get("open")),
        "terminal_followup_tasks": sum(1 for row in rows if row.get("terminal")),
        "stable_loop_count": len(loops),
        "ready_to_resolve_loop_count": sum(1 for item in loops.values() if item.get("task_ids") and not item.get("open_task_ids") and item.get("resolution_status") != "resolved"),
        "resolved_loop_count": sum(1 for item in loops.values() if item.get("resolution_status") == "resolved"),
        "rows": rows,
        "loops": list(loops.values()),
    }


def resolve_stable_loop_followups(
    loop_id: str,
    archive: bool = False,
    force: bool = False,
    note: str = "",
    reviewer: str = "operator",
) -> FollowupLifecycleResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return FollowupLifecycleResult(False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    resolved_loop_id = str(loop.get("id") or loop_id)
    tasks = stable_loop_followup_tasks(resolved_loop_id, include_closed=True)
    task_ids = [str(task.get("id") or "") for task in tasks if task.get("id")]
    open_task_ids = [str(task.get("id") or "") for task in tasks if str(task.get("status") or "") not in TERMINAL_TASK_STATUSES]
    if not tasks:
        return FollowupLifecycleResult(False, loop_id=resolved_loop_id, task_ids=[], open_task_ids=[], error="No stable-loop decision follow-up tasks found for this loop.", loop=loop)
    if open_task_ids and not force:
        return FollowupLifecycleResult(False, loop_id=resolved_loop_id, task_ids=task_ids, open_task_ids=open_task_ids, error="Follow-up tasks are still open. Complete/cancel them first, or use force.", loop=loop)

    notes = ensure_operator_notes(loop, save=False)
    now = _now()
    resolution = {
        "version": FOLLOWUP_LIFECYCLE_VERSION,
        "status": "resolved",
        "resolved_at": now,
        "resolved_by": reviewer or "operator",
        "task_ids": task_ids,
        "open_task_ids_at_resolution": open_task_ids,
        "forced": bool(force),
        "note": note or "Stable-loop decision follow-up tasks resolved.",
    }
    notes["decision_followup_resolution"] = resolution
    entries = notes.get("notes") if isinstance(notes.get("notes"), list) else []
    entries.append({
        "at": now,
        "by": reviewer or "operator",
        "note": resolution["note"],
        "source": "stable_loop_followup_lifecycle",
    })
    notes["notes"] = entries
    notes["updated_at"] = now
    notes["summary"] = summarize_operator_notes(notes)
    loop["operator_notes"] = notes
    save_stable_loop(loop)

    for task_id in task_ids:
        update_task_fields(task_id, metadata={
            "stable_loop_followup_resolution_status": "resolved",
            "stable_loop_followup_resolved_at": now,
            "stable_loop_followup_resolved_by": reviewer or "operator",
        })

    archived = False
    if archive:
        archive_result = set_stable_loop_archived(resolved_loop_id, archived=True, note=note or "Archived after follow-up task resolution.", reviewer=reviewer)
        archived = bool(archive_result.ok)
        loop = archive_result.loop or load_stable_loop(resolved_loop_id) or loop

    return FollowupLifecycleResult(
        True,
        loop_id=resolved_loop_id,
        resolved=True,
        archived=archived,
        task_ids=task_ids,
        open_task_ids=open_task_ids,
        message=f"Resolved follow-up lifecycle for stable loop {resolved_loop_id} with {len(task_ids)} linked task(s).",
        loop=loop,
    )


def resolve_task_stable_loop_followup(
    task_id: str,
    archive: bool = False,
    force: bool = False,
    note: str = "",
    reviewer: str = "operator",
) -> FollowupLifecycleResult:
    task = get_task(task_id)
    if not task:
        return FollowupLifecycleResult(False, task_id=task_id, error=f"Task not found: {task_id}")
    row = stable_loop_followup_task_row(task)
    if not row.get("is_stable_loop_followup"):
        return FollowupLifecycleResult(False, task_id=str(task.get("id") or task_id), row=row, error="Task is not a stable-loop decision follow-up task.")
    if str(task.get("status") or "") not in TERMINAL_TASK_STATUSES and not force:
        return FollowupLifecycleResult(False, task_id=str(task.get("id") or task_id), row=row, error="This follow-up task is still open. Complete/cancel it first, or use force.")
    result = resolve_stable_loop_followups(str(row.get("stable_loop_id") or ""), archive=archive, force=force, note=note, reviewer=reviewer)
    result.task_id = str(task.get("id") or task_id)
    result.row = row
    return result


def stable_loop_followup_task_text(task_or_id: dict[str, Any] | str | None, full: bool = False) -> str:
    row = stable_loop_followup_task_row(task_or_id)
    lines = [
        "# Stable-loop follow-up task lifecycle",
        "",
        f"OK: {row.get('ok')}",
        f"Task: {row.get('task_id', '')}",
        f"Is follow-up: {row.get('is_stable_loop_followup')}",
        f"Stable loop: {row.get('stable_loop_id', '') or '[none]'}",
        f"Decision: {row.get('final_decision_label', '')}",
        f"Follow-up kind: {row.get('followup_kind', '') or '[none]'}",
        f"Task status: {row.get('status', '')}",
        f"Lifecycle: {row.get('lifecycle_label', '')}",
        f"Resolution: {row.get('resolution_status', 'open')}",
        f"Loop archived: {row.get('stable_loop_archived')}",
    ]
    if row.get("message"):
        lines.append(f"Message: {row.get('message')}")
    if full:
        lines.extend(["", "## Raw row", json.dumps(row, indent=2, default=str)])
    return "\n".join(lines).strip()


def followup_lifecycle_summary_text(summary: dict[str, Any] | None = None, full: bool = False) -> str:
    data = summary or stable_loop_followup_lifecycle_summary()
    lines = [
        "# Stable-loop follow-up task lifecycle summary",
        "",
        f"Version: {data.get('version')}",
        f"Follow-up tasks: {data.get('total_followup_tasks', 0)}",
        f"Open follow-up tasks: {data.get('open_followup_tasks', 0)}",
        f"Terminal follow-up tasks: {data.get('terminal_followup_tasks', 0)}",
        f"Stable loops represented: {data.get('stable_loop_count', 0)}",
        f"Ready to resolve: {data.get('ready_to_resolve_loop_count', 0)}",
        f"Resolved loops: {data.get('resolved_loop_count', 0)}",
    ]
    loops = data.get("loops") if isinstance(data.get("loops"), list) else []
    if loops:
        lines.extend(["", "## Stable loops"])
        for item in loops[:50]:
            lines.append(
                f"- {item.get('loop_id')}: {item.get('final_decision_label')} | "
                f"tasks={len(item.get('task_ids') or [])} open={len(item.get('open_task_ids') or [])} "
                f"resolution={item.get('resolution_status')} archived={item.get('archived')}"
            )
    if full:
        lines.extend(["", "## Raw summary", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def followup_resolution_text(result: FollowupLifecycleResult | dict[str, Any], full: bool = False) -> str:
    data = result.to_dict() if isinstance(result, FollowupLifecycleResult) else result
    lines = [
        "# Stable-loop follow-up resolution",
        "",
        f"OK: {data.get('ok')}",
        f"Loop: {data.get('loop_id', '')}",
        f"Task: {data.get('task_id', '')}",
        f"Resolved: {data.get('resolved')}",
        f"Archived: {data.get('archived')}",
        f"Linked tasks: {len(data.get('task_ids') or [])}",
        f"Open tasks at resolution: {len(data.get('open_task_ids') or [])}",
        f"Message: {data.get('message', '')}",
    ]
    if data.get("error"):
        lines.append(f"Error: {data.get('error')}")
    if data.get("task_ids"):
        lines.extend(["", "Task IDs:"])
        lines.extend(f"- {task_id}" for task_id in data.get("task_ids") or [])
    if data.get("open_task_ids"):
        lines.extend(["", "Open task IDs:"])
        lines.extend(f"- {task_id}" for task_id in data.get("open_task_ids") or [])
    if full:
        lines.extend(["", "## Raw result", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stable_loop_followup_lifecycle_summary(decision_filter: str = "all", include_closed: bool = True, include_archived: bool = False, loop_id: str = "", full: bool = False) -> None:
    print(followup_lifecycle_summary_text(stable_loop_followup_lifecycle_summary(decision_filter=decision_filter, include_closed=include_closed, include_archived=include_archived, loop_id=loop_id), full=full))


def print_stable_loop_followup_task(task_id: str, full: bool = False) -> None:
    print(stable_loop_followup_task_text(task_id, full=full))


def print_resolve_stable_loop_followups(loop_id: str, archive: bool = False, force: bool = False, note: str = "", full: bool = False) -> None:
    result = resolve_stable_loop_followups(loop_id, archive=archive, force=force, note=note, reviewer="cli")
    print(followup_resolution_text(result, full=full))


def print_resolve_task_stable_loop_followup(task_id: str, archive: bool = False, force: bool = False, note: str = "", full: bool = False) -> None:
    result = resolve_task_stable_loop_followup(task_id, archive=archive, force=force, note=note, reviewer="cli")
    print(followup_resolution_text(result, full=full))
