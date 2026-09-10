from __future__ import annotations

"""
Legacy queue-to-patch compatibility layer.

v5.2 consolidation note:
    `task_patch_bridge.py` is now the task-native patch bridge. This module
    keeps the v4.9/v5.0/v5.1 function names alive so older dashboard, API, and
    CLI paths keep working while the canonical architecture speaks in tasks.
"""

from typing import Optional

from task_patch_bridge import (
    PatchFollowupResult,
    TaskPatchResult as WorkPatchResult,
    create_patch_followup_tasks,
    create_patch_task,
    patch_followup_result_text,
    suggest_patch_for_task,
    task_patch_result_text,
)
from work_queue import WorkItem, find_work_item


def create_patch_work_item(
    target_file: str,
    request: str,
    project_id: str = "eidolon",
    priority: int = 7,
    risk: str = "low",
    source: str = "user",
    requires_approval: Optional[bool] = None,
) -> WorkItem:
    task = create_patch_task(
        target_file=target_file,
        request=request,
        project_id=project_id,
        priority=priority,
        risk=risk,
        source=source,
        requires_approval=requires_approval,
    )
    item = find_work_item(str(task.get("id", "")))
    if not item:
        raise ValueError("Patch task was created, but the compatibility work item view could not reload it.")
    return item


def suggest_patch_for_work_item(work_id: str, use_ai: bool = True, dry_run: bool = False) -> WorkPatchResult:
    return suggest_patch_for_task(work_id, use_ai=use_ai, dry_run=dry_run)


def create_patch_followup_items(patch_id: str, project_id: str = "eidolon") -> PatchFollowupResult:
    return create_patch_followup_tasks(patch_id, project_id=project_id)


def work_patch_result_text(result: WorkPatchResult, full: bool = False) -> str:
    return task_patch_result_text(result, full=full)


def print_create_patch_work_item(
    target_file: str,
    request: str,
    project_id: str = "eidolon",
    priority: int = 7,
    risk: str = "low",
    requires_approval: Optional[bool] = None,
) -> None:
    task = create_patch_task(
        target_file=target_file,
        request=request,
        project_id=project_id,
        priority=priority,
        risk=risk,
        source="user",
        requires_approval=requires_approval,
    )
    task_id = str(task.get("id"))
    print("Queued patch task through legacy work-queue alias:")
    print(f"  Task: {task_id}")
    print(f"  Target file: {target_file}")
    print(f"  Priority: {task.get('priority')}")
    print(f"  Risk: {task.get('risk')}")
    print("Next:")
    print(f"  python conscious_agent/main.py --suggest-patch-for-task {task_id} --dry-run")
    print(f"  python conscious_agent/main.py --suggest-patch-for-task {task_id}")
    print("Legacy aliases still work:")
    print(f"  python conscious_agent/main.py --suggest-patch-for-work {task_id} --dry-run")


def print_suggest_patch_for_work_item(work_id: str, use_ai: bool = True, dry_run: bool = False, full: bool = False) -> None:
    result = suggest_patch_for_task(work_id, use_ai=use_ai, dry_run=dry_run)
    print(task_patch_result_text(result, full=full))


def print_create_patch_followups(patch_id: str, project_id: str = "eidolon") -> None:
    result = create_patch_followup_tasks(patch_id, project_id=project_id)
    print(patch_followup_result_text(result))
