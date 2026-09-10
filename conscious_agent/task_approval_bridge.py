from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Optional

from approval_manager import create_approval, list_approvals
from memory import store_memory
from task_queue import get_task, list_tasks, resolve_task_id, update_task_fields
from task_work_executor import classify_task_work

READY_STATUSES = {"planned", "active", "blocked"}
APPROVAL_RISKS = {"medium", "high", "critical"}


@dataclass
class TaskApprovalRequestResult:
    ok: bool
    task_id: str = ""
    approval_id: str = ""
    message: str = ""
    error: str = ""
    command: str = ""
    approval: dict[str, Any] | None = None
    task: dict[str, Any] | None = None
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _task_execution_command(task_id: str, use_ai: bool = True, full: bool = False) -> str:
    parts = [
        "python",
        "conscious_agent/main.py",
        "--execute-task-work-id",
        task_id,
        "--approve-task-work-execution",
    ]
    if not use_ai:
        parts.append("--no-ai-task-work-executor")
    if full:
        parts.append("--task-work-executor-full")
    return " ".join(parts)


def _task_needs_approval(task: dict[str, Any]) -> bool:
    risk = str(task.get("risk") or "low").lower().strip()
    return bool(task.get("requires_approval")) or risk in APPROVAL_RISKS


def _task_approval_metadata(task: dict[str, Any], command: str, reason: str, use_ai: bool) -> dict[str, Any]:
    task_id = str(task.get("id") or "")
    action_type = classify_task_work(task)
    return {
        "approval_kind": "task_work_execution",
        "task_id": task_id,
        "task_title": task.get("title", ""),
        "task_status": task.get("status", ""),
        "task_project": task.get("project", ""),
        "task_risk": task.get("risk", "low"),
        "task_requires_approval": bool(task.get("requires_approval")),
        "task_action_type": action_type,
        "approved_command": command,
        "use_ai": bool(use_ai),
        "reason": reason,
    }


def list_task_approvals(task_id: str, include_closed: bool = True) -> list[dict[str, Any]]:
    resolved = resolve_task_id(task_id) or task_id
    matches: list[dict[str, Any]] = []
    for approval in list_approvals(include_closed=include_closed):
        metadata = approval.get("metadata") if isinstance(approval.get("metadata"), dict) else {}
        if approval.get("object_id") == resolved or metadata.get("task_id") == resolved:
            matches.append(approval)
    return matches


def request_task_work_approval(
    task_id: str,
    reason: str = "",
    use_ai: bool = True,
    full_output: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> TaskApprovalRequestResult:
    resolved = resolve_task_id(task_id) or task_id
    task = get_task(resolved)
    if not task:
        return TaskApprovalRequestResult(False, task_id=task_id, error=f"Task not found: {task_id}")

    actual_task_id = str(task.get("id") or resolved)
    status = str(task.get("status") or "planned").lower().strip()
    if status not in READY_STATUSES and not force:
        return TaskApprovalRequestResult(
            False,
            task_id=actual_task_id,
            error=f"Task is {status}; approval requests are only created for planned/active/blocked tasks unless force=True.",
            task=task,
        )

    if not _task_needs_approval(task) and not force:
        return TaskApprovalRequestResult(
            False,
            task_id=actual_task_id,
            error="Task does not currently require approval. Use force=True if an approval request is still desired.",
            task=task,
        )

    command = _task_execution_command(actual_task_id, use_ai=use_ai, full=full_output)
    reason = reason or "Task is risk-gated or explicitly requires approval before execution."
    summary = f"Execute task {actual_task_id}: {task.get('title', '')}"
    metadata = _task_approval_metadata(task, command=command, reason=reason, use_ai=use_ai)

    if dry_run:
        return TaskApprovalRequestResult(
            True,
            task_id=actual_task_id,
            message="Dry run: task approval request can be created.",
            command=command,
            task=task,
            dry_run=True,
        )

    approval = create_approval(
        action_type="run_command",
        summary=summary,
        object_id=actual_task_id,
        command=command,
        risk_level=str(task.get("risk") or "medium"),
        source="task_approval_bridge",
        reason=reason,
        metadata=metadata,
        dedupe=True,
    )

    update_task_fields(
        actual_task_id,
        status="blocked",
        blocked_reason=f"Approval pending: {approval.get('id')}",
        metadata={
            "approval_id": approval.get("id", ""),
            "approval_status": approval.get("status", "pending"),
            "approval_kind": "task_work_execution",
            "approval_command": command,
            "approval_reason": reason,
            "action_type": metadata.get("task_action_type", ""),
        },
    )
    updated_task = get_task(actual_task_id) or task

    store_memory({
        "type": "task_approval_requested",
        "content": f"Created approval request {approval.get('id')} for task {actual_task_id}.",
        "source": "task_approval_bridge",
        "task_id": actual_task_id,
        "approval_id": approval.get("id"),
        "risk": task.get("risk"),
    })

    return TaskApprovalRequestResult(
        True,
        task_id=actual_task_id,
        approval_id=str(approval.get("id") or ""),
        message=f"Approval request ready: {approval.get('id')}",
        command=command,
        approval=approval,
        task=updated_task,
    )


def request_next_task_work_approval(
    project_id: Optional[str] = None,
    reason: str = "",
    use_ai: bool = True,
    full_output: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> TaskApprovalRequestResult:
    tasks = [task for task in list_tasks(project=project_id or "", include_cancelled=False) if str(task.get("status")) in {"planned", "active", "blocked"}]
    candidates = [task for task in tasks if _task_needs_approval(task) or force]
    if not candidates:
        return TaskApprovalRequestResult(True, message="No approval-required task found.", dry_run=dry_run)
    return request_task_work_approval(
        str(candidates[0].get("id") or ""),
        reason=reason,
        use_ai=use_ai,
        full_output=full_output,
        force=force,
        dry_run=dry_run,
    )


def task_approval_request_text(result: TaskApprovalRequestResult, full: bool = False) -> str:
    lines = ["# Task approval request"]
    if result.task_id:
        lines.append(f"Task: {result.task_id}")
    if result.approval_id:
        lines.append(f"Approval: {result.approval_id}")
    lines.append(f"OK: {result.ok}")
    if result.dry_run:
        lines.append("Dry run: True")
    if result.message:
        lines.append(f"Message: {result.message}")
    if result.error:
        lines.append(f"Error: {result.error}")
    if result.command:
        lines.extend(["", "## Approval command", result.command])
    if full and result.task:
        lines.extend(["", "## Task", json.dumps(result.task, indent=2, default=str)])
    if full and result.approval:
        lines.extend(["", "## Approval", json.dumps(result.approval, indent=2, default=str)])
    return "\n".join(lines).strip()


def task_approvals_text(task_id: str, include_closed: bool = True, full: bool = False) -> str:
    approvals = list_task_approvals(task_id, include_closed=include_closed)
    lines = [f"# Approvals for task: {task_id}"]
    if not approvals:
        lines.append("No approval requests found for this task.")
        return "\n".join(lines)
    for approval in approvals:
        lines.append(
            f"- {approval.get('id')} | {approval.get('status')} | {approval.get('action_type')} | {approval.get('summary')}"
        )
        if approval.get("command"):
            lines.append(f"  command: {approval.get('command')}")
    if full:
        lines.extend(["", "## Raw approvals", json.dumps(approvals, indent=2, default=str)])
    return "\n".join(lines)


def print_request_task_work_approval(
    task_id: str,
    reason: str = "",
    use_ai: bool = True,
    full_output: bool = False,
    force: bool = False,
    dry_run: bool = False,
    full: bool = False,
) -> None:
    result = request_task_work_approval(
        task_id,
        reason=reason,
        use_ai=use_ai,
        full_output=full_output,
        force=force,
        dry_run=dry_run,
    )
    print(task_approval_request_text(result, full=full))


def print_request_next_task_work_approval(
    project_id: Optional[str] = None,
    reason: str = "",
    use_ai: bool = True,
    full_output: bool = False,
    force: bool = False,
    dry_run: bool = False,
    full: bool = False,
) -> None:
    result = request_next_task_work_approval(
        project_id=project_id,
        reason=reason,
        use_ai=use_ai,
        full_output=full_output,
        force=force,
        dry_run=dry_run,
    )
    print(task_approval_request_text(result, full=full))


def print_task_approvals(task_id: str, include_closed: bool = True, full: bool = False) -> None:
    print(task_approvals_text(task_id, include_closed=include_closed, full=full))
