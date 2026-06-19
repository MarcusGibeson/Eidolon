from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from memory import store_memory
from patch_suggester import (
    load_patch_proposal,
    patch_proposal_text,
    save_patch_proposal,
    suggest_patch,
)
from task_queue import add_task, get_task, update_task_fields


PATH_PATTERN = re.compile(r"([A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)")
QUOTED_PATTERN = re.compile(r"['\"]([^'\"]+)['\"]")


@dataclass
class TaskPatchResult:
    ok: bool
    task_id: str = ""
    patch_id: str = ""
    target_file: str = ""
    dry_run: bool = False
    message: str = ""
    error: str = ""
    result: str = ""
    metadata: dict[str, Any] | None = None
    # Compatibility alias for older v4.9-v5.1 callers.
    work_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("work_id") and data.get("task_id"):
            data["work_id"] = data["task_id"]
        return data


@dataclass
class PatchFollowupResult:
    ok: bool
    patch_id: str = ""
    created_task_ids: list[str] | None = None
    message: str = ""
    error: str = ""
    metadata: dict[str, Any] | None = None
    # Compatibility alias for older v4.9-v5.1 callers.
    created_work_ids: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data.get("created_work_ids") is None and data.get("created_task_ids") is not None:
            data["created_work_ids"] = data["created_task_ids"]
        return data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _priority_number_to_label(value: Any) -> str:
    try:
        priority = int(value)
    except (TypeError, ValueError):
        priority = 5
    if priority >= 9:
        return "critical"
    if priority >= 7:
        return "high"
    if priority >= 4:
        return "medium"
    return "low"


def _risk_label(value: str) -> str:
    risk = (value or "low").strip().lower()
    return risk if risk in {"low", "medium", "high", "critical"} else "low"


def _task_metadata(task: dict[str, Any] | None) -> dict[str, Any]:
    metadata = (task or {}).get("metadata") if isinstance(task, dict) else {}
    return dict(metadata) if isinstance(metadata, dict) else {}


def _task_text(task: dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    return "\n".join([
        str(task.get("title") or ""),
        str(task.get("description") or ""),
        str(task.get("command") or ""),
        json.dumps(metadata, indent=2) if metadata else "",
    ]).strip()


def patch_target_from_task(task: dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    for key in ["target_file", "patch_target_file", "file", "path", "relative_path"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    text = _task_text(task)
    for quoted in QUOTED_PATTERN.findall(text):
        if "." in quoted and not quoted.strip().startswith("--"):
            return quoted.strip()

    match = PATH_PATTERN.search(text)
    if match:
        return match.group(1).strip()

    return ""


def patch_request_from_task(task: dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    for key in ["patch_request", "request", "change_request", "instructions"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    return str(task.get("description") or task.get("title") or "").strip()


def _merge_task_metadata(task: dict[str, Any] | None, updates: dict[str, Any]) -> dict[str, Any]:
    merged = _task_metadata(task)
    merged.update(updates)
    return merged


def link_patch_to_task(task_id: str, patch_id: str, relationship: str = "created_from_task") -> TaskPatchResult:
    task = get_task(task_id)
    if not task:
        return TaskPatchResult(False, task_id=task_id, work_id=task_id, patch_id=patch_id, error=f"Task not found: {task_id}")

    proposal = load_patch_proposal(patch_id)
    if not proposal:
        return TaskPatchResult(False, task_id=task_id, work_id=task_id, patch_id=patch_id, error=f"Patch proposal not found: {patch_id}")

    target_file = str(proposal.get("target_file") or patch_target_from_task(task) or "")
    timestamp = _now()

    linked_tasks = proposal.get("linked_tasks")
    if not isinstance(linked_tasks, list):
        linked_tasks = []
    task_link = {
        "task_id": task_id,
        "relationship": relationship,
        "linked_at": timestamp,
    }
    if not any(entry.get("task_id") == task_id and entry.get("relationship") == relationship for entry in linked_tasks if isinstance(entry, dict)):
        linked_tasks.append(task_link)

    # Keep older dashboard/API fields available during the transition.
    linked_work_items = proposal.get("linked_work_items")
    if not isinstance(linked_work_items, list):
        linked_work_items = []
    work_link = {
        "work_id": task_id,
        "relationship": relationship.replace("task", "work_item"),
        "linked_at": timestamp,
    }
    if not any(entry.get("work_id") == task_id and entry.get("relationship") == work_link["relationship"] for entry in linked_work_items if isinstance(entry, dict)):
        linked_work_items.append(work_link)

    proposal["task_id"] = proposal.get("task_id") or task_id
    proposal["task_relationship"] = proposal.get("task_relationship") or relationship
    proposal["linked_tasks"] = linked_tasks
    proposal["work_item_id"] = proposal.get("work_item_id") or task_id
    proposal["work_item_relationship"] = proposal.get("work_item_relationship") or relationship.replace("task", "work_item")
    proposal["linked_work_items"] = linked_work_items
    proposal["updated_at"] = timestamp
    save_patch_proposal(proposal)

    updated_metadata = _merge_task_metadata(task, {
        "action_type": "suggest_patch",
        "patch_id": patch_id,
        "patch_status": proposal.get("status", "proposed"),
        "target_file": target_file,
        "patch_target_file": target_file,
        "patch_linked_at": timestamp,
        "patch_relationship": relationship,
    })
    update_result = update_task_fields(
        task_id,
        metadata=updated_metadata,
        patch_id=patch_id,
        patch_status=str(proposal.get("status", "proposed")),
    )

    store_memory({
        "type": "task_patch_link_event",
        "content": f"Linked task {task_id} to patch proposal {patch_id} for '{target_file}'.",
        "source": "task_patch_bridge",
        "task_id": task_id,
        "patch_id": patch_id,
        "file": target_file,
        "relationship": relationship,
    })

    task_after = update_result.task if update_result.ok else task
    return TaskPatchResult(
        True,
        task_id=task_id,
        work_id=task_id,
        patch_id=patch_id,
        target_file=target_file,
        message=f"Linked task {task_id} to patch proposal {patch_id}.",
        result=patch_proposal_text(proposal, include_full_content=False),
        metadata=_task_metadata(task_after),
    )


def create_patch_task(
    target_file: str,
    request: str,
    project_id: str = "eidolon",
    priority: int = 7,
    risk: str = "low",
    source: str = "user",
    requires_approval: Optional[bool] = None,
) -> dict[str, Any]:
    target_file = target_file.strip()
    request = request.strip()
    if not target_file:
        raise ValueError("target_file is required.")
    if not request:
        raise ValueError("request is required.")

    metadata = {
        "action_type": "suggest_patch",
        "target_file": target_file,
        "patch_target_file": target_file,
        "patch_request": request,
        "patch_status": "queued",
    }
    result = add_task(
        title=f"Suggest patch for {target_file}",
        description=request,
        project=project_id or "eidolon",
        priority=_priority_number_to_label(priority),
        status="planned",
        risk=_risk_label(risk),
        source=source,
        source_category="task_patch_bridge",
        requires_approval=requires_approval,
        metadata=metadata,
        patch_status="queued",
    )
    if not result.ok or not result.task:
        raise ValueError(result.error or "Could not create patch task.")
    return result.task


def suggest_patch_for_task(task_id: str, use_ai: bool = True, dry_run: bool = False) -> TaskPatchResult:
    task = get_task(task_id)
    if not task:
        return TaskPatchResult(False, task_id=task_id, work_id=task_id, dry_run=dry_run, error=f"Task not found: {task_id}")

    target_file = patch_target_from_task(task)
    request = patch_request_from_task(task)

    if not target_file:
        return TaskPatchResult(False, task_id=task_id, work_id=task_id, dry_run=dry_run, error="No target file found in task metadata, title, command, or description.")
    if not request:
        return TaskPatchResult(False, task_id=task_id, work_id=task_id, target_file=target_file, dry_run=dry_run, error="No patch request found in task description or metadata.")

    if dry_run:
        lines = [
            "# Task-to-patch dry run",
            "",
            f"Task: {task_id}",
            f"Target file: {target_file}",
            f"Use AI: {use_ai}",
            "",
            "## Patch request",
            request,
            "",
            "No patch proposal was created.",
        ]
        return TaskPatchResult(True, task_id=task_id, work_id=task_id, target_file=target_file, dry_run=True, result="\n".join(lines), message="Patch dry run passed.")

    if not use_ai:
        return TaskPatchResult(False, task_id=task_id, work_id=task_id, target_file=target_file, error="Patch suggestion requires local AI. Run without --no-ai-work-executor or enable use_ai.")

    update_task_fields(
        task_id,
        metadata=_merge_task_metadata(task, {
            "action_type": "suggest_patch",
            "patch_status": "generating",
            "target_file": target_file,
            "patch_target_file": target_file,
            "patch_request": request,
            "patch_started_at": _now(),
        }),
        patch_status="generating",
    )

    result = suggest_patch(target_file, request, use_ai=True)
    if not result.ok:
        failed_task = get_task(task_id) or task
        update_task_fields(
            task_id,
            metadata=_merge_task_metadata(failed_task, {
                "patch_status": "failed",
                "patch_error": result.error,
                "patch_finished_at": _now(),
            }),
            patch_status="failed",
            result=result.error,
        )
        return TaskPatchResult(False, task_id=task_id, work_id=task_id, target_file=target_file, error=result.error)

    link = link_patch_to_task(task_id, result.patch_id)
    linked_task = get_task(task_id) or task
    update_task_fields(
        task_id,
        metadata=_merge_task_metadata(linked_task, {
            "patch_id": result.patch_id,
            "patch_status": "proposed",
            "patch_finished_at": _now(),
        }),
        patch_id=result.patch_id,
        patch_status="proposed",
    )

    return TaskPatchResult(
        True,
        task_id=task_id,
        work_id=task_id,
        patch_id=result.patch_id,
        target_file=result.target_file,
        message=f"Patch proposal saved and linked: {result.patch_id}",
        result=link.result or result.text,
        metadata={"patch_id": result.patch_id, "target_file": result.target_file},
    )


def create_patch_followup_tasks(patch_id: str, project_id: str = "eidolon") -> PatchFollowupResult:
    proposal = load_patch_proposal(patch_id)
    if not proposal:
        return PatchFollowupResult(False, patch_id=patch_id, created_task_ids=[], created_work_ids=[], error=f"Patch proposal not found: {patch_id}")

    target_file = str(proposal.get("target_file") or "")
    risk = _risk_label(str(proposal.get("risk_level") or "medium"))
    created: list[str] = []

    definitions = [
        {
            "title": f"Review patch {patch_id}",
            "description": f"Review proposed patch {patch_id} for {target_file} before applying it.",
            "priority": "high",
            "risk": "low",
            "requires_approval": False,
            "metadata": {
                "action_type": "manual",
                "patch_id": patch_id,
                "target_file": target_file,
                "patch_status": proposal.get("status", "proposed"),
                "recommended_command": f"python conscious_agent/main.py --show-patch {patch_id}",
                "patch_relationship": "patch_followup",
            },
        },
        {
            "title": f"Apply patch {patch_id}",
            "description": f"Apply proposed patch {patch_id} for {target_file} after review/approval.",
            "priority": "high",
            "risk": risk if risk in {"medium", "high", "critical"} else "medium",
            "requires_approval": True,
            "metadata": {
                "action_type": "run_command",
                "patch_id": patch_id,
                "target_file": target_file,
                "patch_status": proposal.get("status", "proposed"),
                "command": f"python conscious_agent/main.py --apply-patch {patch_id}",
                "dry_run_command": f"python conscious_agent/main.py --apply-patch {patch_id} --dry-run",
                "patch_relationship": "patch_followup",
            },
        },
        {
            "title": f"Run tests after patch {patch_id}",
            "description": f"Run the approved test workflow after patch {patch_id} is applied.",
            "priority": "medium",
            "risk": "low",
            "requires_approval": False,
            "metadata": {
                "action_type": "test_project",
                "patch_id": patch_id,
                "target_file": target_file,
                "patch_status": proposal.get("status", "proposed"),
                "patch_relationship": "patch_followup",
            },
        },
    ]

    for definition in definitions:
        metadata = definition.pop("metadata")
        result = add_task(
            project=project_id,
            status="planned",
            source="system",
            source_category="task_patch_bridge",
            source_id=patch_id,
            patch_id=patch_id,
            patch_status=str(proposal.get("status", "proposed")),
            **definition,
            metadata=metadata,
        )
        if result.ok and result.task:
            created.append(str(result.task.get("id")))

    linked_tasks = proposal.get("linked_tasks")
    if not isinstance(linked_tasks, list):
        linked_tasks = []
    linked_work_items = proposal.get("linked_work_items")
    if not isinstance(linked_work_items, list):
        linked_work_items = []

    timestamp = _now()
    for task_id in created:
        linked_tasks.append({"task_id": task_id, "relationship": "patch_followup", "linked_at": timestamp})
        linked_work_items.append({"work_id": task_id, "relationship": "patch_followup", "linked_at": timestamp})
    proposal["linked_tasks"] = linked_tasks
    proposal["linked_work_items"] = linked_work_items
    proposal["updated_at"] = timestamp
    save_patch_proposal(proposal)

    store_memory({
        "type": "patch_followup_tasks_event",
        "content": f"Created {len(created)} follow-up tasks for patch {patch_id}.",
        "source": "task_patch_bridge",
        "patch_id": patch_id,
        "created_task_ids": created,
    })

    return PatchFollowupResult(
        True,
        patch_id=patch_id,
        created_task_ids=created,
        created_work_ids=created,
        message=f"Created {len(created)} follow-up task(s) for patch {patch_id}.",
        metadata={"target_file": target_file, "risk_level": risk},
    )


def task_patch_result_text(result: TaskPatchResult, full: bool = False) -> str:
    lines = ["# Task-to-patch result"]
    if result.message:
        lines.append(result.message)
    lines.extend([
        f"Task: {result.task_id or result.work_id or '[none]'}",
        f"Patch: {result.patch_id or '[none]'}",
        f"Target file: {result.target_file or '[unknown]'}",
        f"Dry run: {result.dry_run}",
        f"OK: {result.ok}",
    ])
    if result.error:
        lines.append(f"Error: {result.error}")
    if result.result:
        lines.extend(["", "## Result", result.result if full else result.result[:2400]])
    if full and result.metadata:
        lines.extend(["", "## Metadata", json.dumps(result.metadata, indent=2)])
    return "\n".join(lines).strip()


def patch_followup_result_text(result: PatchFollowupResult) -> str:
    lines = ["# Patch follow-up tasks"]
    if result.message:
        lines.append(result.message)
    lines.extend([
        f"Patch: {result.patch_id or '[none]'}",
        f"OK: {result.ok}",
    ])
    if result.error:
        lines.append(f"Error: {result.error}")
    ids = result.created_task_ids or result.created_work_ids or []
    if ids:
        lines.append("Created tasks:")
        lines.extend(f"- {task_id}" for task_id in ids)
    return "\n".join(lines).strip()


def print_create_patch_task(
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
    print("Queued patch task:")
    print(f"  Task: {task_id}")
    print(f"  Target file: {target_file}")
    print(f"  Priority: {task.get('priority')}")
    print(f"  Risk: {task.get('risk')}")
    print("Next:")
    print(f"  python conscious_agent/main.py --suggest-patch-for-task {task_id} --dry-run")
    print(f"  python conscious_agent/main.py --suggest-patch-for-task {task_id}")


def print_suggest_patch_for_task(task_id: str, use_ai: bool = True, dry_run: bool = False, full: bool = False) -> None:
    result = suggest_patch_for_task(task_id, use_ai=use_ai, dry_run=dry_run)
    print(task_patch_result_text(result, full=full))


def print_create_patch_task_followups(patch_id: str, project_id: str = "eidolon") -> None:
    result = create_patch_followup_tasks(patch_id, project_id=project_id)
    print(patch_followup_result_text(result))
