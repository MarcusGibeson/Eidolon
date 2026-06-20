from __future__ import annotations

"""Task failure recovery and retry helpers.

v5.8 note:
    task_queue.py remains the source of truth. This module does not guess at
    code fixes. It reads blocked/failed task state, classifies the failure,
    suggests safe recovery options, and can mark a failed task ready for a
    controlled retry through task_work_executor.py.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from memory import store_memory
from task_lifecycle import derive_task_lifecycle, list_task_lifecycles
from task_queue import get_task, list_tasks, update_task_fields
from task_work_executor import execute_task_work_item, task_work_execution_text

RECOVERABLE_STAGES = {"recovery_needed", "blocked", "approval_failed", "approval_rejected"}
RECOVERABLE_WORK_STATUSES = {"failed", "blocked"}
RECOVERY_LIMIT_DEFAULT = 25


@dataclass
class TaskRecoveryResult:
    ok: bool
    task_id: str = ""
    dry_run: bool = False
    action: str = ""
    message: str = ""
    error: str = ""
    recovery: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _metadata(task: dict[str, Any] | None) -> dict[str, Any]:
    raw = (task or {}).get("metadata") if isinstance(task, dict) else {}
    return dict(raw) if isinstance(raw, dict) else {}


def _text_blob(task: dict[str, Any], lifecycle: dict[str, Any]) -> str:
    metadata = _metadata(task)
    parts = [
        str(task.get("title") or ""),
        str(task.get("description") or ""),
        str(task.get("result") or ""),
        str(task.get("work_status") or ""),
        str(metadata.get("last_executor_block_reason") or ""),
        str(metadata.get("approval_status") or ""),
        str(lifecycle.get("stage") or ""),
        str(lifecycle.get("approval_status") or ""),
        str(lifecycle.get("next_action") or ""),
    ]
    blockers = task.get("blockers") or []
    if isinstance(blockers, list):
        parts.extend(str(blocker) for blocker in blockers)
    if metadata:
        parts.append(json.dumps(metadata, sort_keys=True))
    return "\n".join(part for part in parts if part).lower()


def classify_task_failure(task: dict[str, Any] | None, lifecycle: dict[str, Any] | None = None) -> str:
    if not task:
        return "unknown"
    lifecycle = lifecycle or derive_task_lifecycle(task)
    metadata = _metadata(task)
    stage = str(lifecycle.get("stage") or "unknown")
    action_type = str(metadata.get("action_type") or lifecycle.get("action_type") or "").lower().strip()
    text = _text_blob(task, lifecycle)

    if stage == "approval_rejected" or "rejected" in text:
        return "approval_rejected"
    if stage == "approval_failed" or "approval failed" in text:
        return "approval_failed"
    if stage == "approval_required" or "requires approval" in text or "risk is" in text:
        return "approval_required"
    if "no target file" in text or "target file" in text and "not found" in text:
        return "missing_target_file"
    if "no command found" in text or "command is required" in text:
        return "missing_command"
    if "blocked token" in text or "command was not run" in text or "not allowed" in text:
        return "command_blocked"
    if action_type == "run_command" and ("return code:" in text or "stderr" in text or "error:" in text):
        return "command_failed"
    if action_type == "test_project" or "test report" in text or "pytest" in text:
        return "test_failed"
    if action_type == "suggest_patch" or "patch" in text:
        return "patch_failed"
    if action_type == "manual" or "manual handling" in text:
        return "manual_required"
    if str(task.get("work_status") or "").lower() == "failed":
        return "executor_failed"
    if str(task.get("status") or "").lower() == "blocked":
        return "blocked_unknown"
    return "unknown"


def _option(action: str, label: str, description: str, safe: bool = True, command: str = "", recommended: bool = False) -> dict[str, Any]:
    return {
        "action": action,
        "label": label,
        "description": description,
        "safe": safe,
        "recommended": recommended,
        "command": command,
    }


def recovery_options_for_category(task: dict[str, Any], category: str, lifecycle: dict[str, Any]) -> list[dict[str, Any]]:
    task_id = str(task.get("id") or "")
    options: list[dict[str, Any]] = []

    if category in {"approval_required", "approval_failed"}:
        options.append(_option(
            "request_approval",
            "Request approval",
            "Create or refresh an approval request for this task before executing it.",
            command=f"python conscious_agent/main.py --request-task-approval {task_id}",
            recommended=True,
        ))
    elif category == "approval_rejected":
        options.append(_option(
            "revise_then_request_approval",
            "Revise, then request approval",
            "Approval was rejected. Review the task/command/request, adjust it, then request approval again only if it still makes sense.",
            command=f"python conscious_agent/main.py --show-task {task_id} --show-task-full",
            recommended=True,
        ))
    elif category in {"missing_target_file", "missing_command", "command_blocked", "manual_required"}:
        options.append(_option(
            "edit_task",
            "Edit the task metadata or command",
            "The executor lacks safe actionable information. Add a target file, command, or action_type before retrying.",
            command=f"python conscious_agent/main.py --show-task {task_id} --show-task-full",
            recommended=True,
        ))
    elif category in {"command_failed", "test_failed", "patch_failed", "executor_failed", "blocked_unknown", "unknown"}:
        options.append(_option(
            "dry_run_retry",
            "Dry-run retry",
            "Run the task executor in dry-run mode to verify classification, target file, and command safety before changing state.",
            command=f"python conscious_agent/main.py --retry-task-work {task_id} --dry-run --task-recovery-full",
            recommended=True,
        ))
        options.append(_option(
            "mark_ready_for_retry",
            "Mark ready for retry",
            "Clear the blocked/failed work marker and return this task to planned so the executor can pick it again.",
            command=f"python conscious_agent/main.py --mark-task-ready-for-retry {task_id}",
        ))

    if category not in {"approval_required", "approval_failed", "approval_rejected"}:
        options.append(_option(
            "create_review_task",
            "Create a review task manually",
            "For unclear failures, create a separate low-risk review task that inspects the relevant file or command output.",
            command="python conscious_agent/main.py --add-task \"Review failed task context\" --task-risk low",
        ))

    options.append(_option(
        "cancel",
        "Cancel task",
        "Cancel this task if it is stale, wrong, or no longer worth recovering.",
        command=f"python conscious_agent/main.py --set-task-status {task_id} cancelled",
        safe=True,
    ))
    return options


def build_task_recovery(task_or_id: dict[str, Any] | str | None) -> dict[str, Any]:
    task = get_task(task_or_id) if isinstance(task_or_id, str) else task_or_id
    if not task:
        return {
            "ok": False,
            "task_id": str(task_or_id or ""),
            "recoverable": False,
            "category": "unknown",
            "message": "Task not found.",
            "options": [],
        }

    lifecycle = derive_task_lifecycle(task)
    metadata = _metadata(task)
    category = classify_task_failure(task, lifecycle)
    work_status = str(task.get("work_status") or "").lower().strip()
    recoverable = (
        lifecycle.get("stage") in RECOVERABLE_STAGES
        or work_status in RECOVERABLE_WORK_STATUSES
        or bool(metadata.get("last_executor_block_reason"))
    )
    options = recovery_options_for_category(task, category, lifecycle) if recoverable else []
    recommended = next((option for option in options if option.get("recommended")), options[0] if options else None)

    return {
        "ok": True,
        "task_id": str(task.get("id") or ""),
        "title": task.get("title", ""),
        "status": task.get("status", ""),
        "work_status": task.get("work_status", ""),
        "risk": task.get("risk", ""),
        "requires_approval": bool(task.get("requires_approval")),
        "recoverable": recoverable,
        "category": category,
        "stage": lifecycle.get("stage", "unknown"),
        "stage_label": lifecycle.get("stage_label", "Unknown"),
        "failure_text": _summarize_failure_text(task, lifecycle),
        "retry_count": int(metadata.get("retry_count") or 0),
        "last_recovery_action": metadata.get("last_recovery_action", ""),
        "recommended_action": recommended,
        "options": options,
        "lifecycle": lifecycle,
    }


def _summarize_failure_text(task: dict[str, Any], lifecycle: dict[str, Any], limit: int = 900) -> str:
    metadata = _metadata(task)
    parts = []
    for label, value in [
        ("Stage", lifecycle.get("stage_label")),
        ("Result", task.get("result")),
        ("Blocker", "; ".join(str(item) for item in task.get("blockers", []) if str(item).strip())),
        ("Executor block", metadata.get("last_executor_block_reason")),
        ("Approval", metadata.get("approval_status") or lifecycle.get("approval_status")),
    ]:
        if value:
            parts.append(f"{label}: {value}")
    text = "\n".join(parts).strip()
    if len(text) > limit:
        return text[:limit] + f"\n[TRUNCATED: failure context exceeded {limit} characters]"
    return text


def list_task_recoveries(project: str = "", include_nonrecoverable: bool = False, limit: int = RECOVERY_LIMIT_DEFAULT) -> list[dict[str, Any]]:
    rows = []
    for task in list_tasks(project=project, include_cancelled=False):
        recovery = build_task_recovery(task)
        if recovery.get("recoverable") or include_nonrecoverable:
            rows.append(recovery)
    rows.sort(key=lambda row: (0 if row.get("recoverable") else 1, str(row.get("category") or ""), str(row.get("task_id") or "")))
    return rows[: max(1, limit)]


def task_recovery_summary(project: str = "") -> dict[str, Any]:
    recoveries = list_task_recoveries(project=project, include_nonrecoverable=False, limit=500)
    categories: dict[str, int] = {}
    for recovery in recoveries:
        category = str(recovery.get("category") or "unknown")
        categories[category] = categories.get(category, 0) + 1
    lifecycle_rows = list_task_lifecycles(project=project, include_closed=False, stage_filter="needs_attention")
    return {
        "project": project,
        "recoverable": len(recoveries),
        "needs_attention": len(lifecycle_rows),
        "categories": categories,
        "next_recovery": recoveries[0] if recoveries else None,
        "recoveries": recoveries,
    }


def mark_task_ready_for_retry(task_id: str, note: str = "") -> TaskRecoveryResult:
    task = get_task(task_id)
    if not task:
        return TaskRecoveryResult(False, task_id=task_id, action="mark_ready_for_retry", error=f"Task not found: {task_id}")
    recovery = build_task_recovery(task)
    metadata = _metadata(task)
    retry_count = int(metadata.get("retry_count") or 0) + 1
    history = metadata.get("retry_history") if isinstance(metadata.get("retry_history"), list) else []
    history.append({
        "at": _now(),
        "action": "mark_ready_for_retry",
        "category": recovery.get("category"),
        "note": note or "Marked ready for retry.",
    })
    metadata.update({
        "retry_count": retry_count,
        "retry_history": history[-20:],
        "last_recovery_action": "mark_ready_for_retry",
        "last_recovery_at": _now(),
        "recovery_status": "ready_for_retry",
    })
    mutation = update_task_fields(
        str(task.get("id") or task_id),
        status="planned",
        work_status="retry_ready",
        metadata=metadata,
    )
    if not mutation.ok:
        return TaskRecoveryResult(False, task_id=task_id, action="mark_ready_for_retry", error=mutation.error, recovery=recovery)
    store_memory({
        "type": "task_recovery_event",
        "content": f"Marked task {mutation.task.get('id')} ready for retry.",
        "source": "task_recovery",
        "task_id": mutation.task.get("id"),
        "category": recovery.get("category"),
        "retry_count": retry_count,
    })
    return TaskRecoveryResult(
        True,
        task_id=str(mutation.task.get("id") or task_id),
        action="mark_ready_for_retry",
        message=f"Task marked ready for retry: {mutation.task.get('id')}",
        recovery=build_task_recovery(mutation.task),
    )


def retry_task_work(
    task_id: str,
    dry_run: bool = True,
    allow_approval_required: bool = False,
    use_ai: bool = True,
) -> TaskRecoveryResult:
    task = get_task(task_id)
    if not task:
        return TaskRecoveryResult(False, task_id=task_id, dry_run=dry_run, action="retry", error=f"Task not found: {task_id}")
    recovery = build_task_recovery(task)
    if not recovery.get("recoverable"):
        return TaskRecoveryResult(False, task_id=str(task.get("id") or task_id), dry_run=dry_run, action="retry", error="Task is not currently marked recoverable.", recovery=recovery)

    if dry_run:
        status = str(task.get("status") or "").lower().strip()
        if status in {"planned", "active"}:
            execution = execute_task_work_item(str(task.get("id") or task_id), dry_run=True, allow_approval_required=allow_approval_required, use_ai=use_ai)
            return TaskRecoveryResult(
                execution.ok,
                task_id=str(task.get("id") or task_id),
                dry_run=True,
                action="retry",
                message="Dry-run retry completed." if execution.ok else "Dry-run retry found a blocker.",
                error=execution.error,
                recovery=recovery,
                execution=execution.to_dict(),
            )
        return TaskRecoveryResult(
            True,
            task_id=str(task.get("id") or task_id),
            dry_run=True,
            action="retry",
            message="Dry-run retry preview: would mark this task planned/ready, then run the task work executor. No task state changed.",
            recovery=recovery,
            execution={
                "dry_run": True,
                "would_mark_status": "planned",
                "would_increment_retry_count": True,
                "would_execute_task_work": True,
            },
        )

    ready = mark_task_ready_for_retry(str(task.get("id") or task_id), note="Retry requested.")
    if not ready.ok:
        return ready
    execution = execute_task_work_item(str(task.get("id") or task_id), dry_run=False, allow_approval_required=allow_approval_required, use_ai=use_ai)
    updated = get_task(str(task.get("id") or task_id)) or task
    metadata = _metadata(updated)
    history = metadata.get("retry_history") if isinstance(metadata.get("retry_history"), list) else []
    history.append({
        "at": _now(),
        "action": "retry_execute",
        "ok": execution.ok,
        "error": execution.error,
    })
    metadata.update({
        "retry_history": history[-20:],
        "last_recovery_action": "retry_execute",
        "last_recovery_at": _now(),
        "recovery_status": "retry_succeeded" if execution.ok else "retry_failed",
    })
    update_task_fields(str(updated.get("id") or task_id), metadata=metadata)
    return TaskRecoveryResult(
        execution.ok,
        task_id=str(updated.get("id") or task_id),
        dry_run=False,
        action="retry",
        message="Retry execution completed." if execution.ok else "Retry execution failed or blocked.",
        error=execution.error,
        recovery=build_task_recovery(str(updated.get("id") or task_id)),
        execution=execution.to_dict(),
    )


def task_recovery_text(recovery_or_result: dict[str, Any] | TaskRecoveryResult | None, full: bool = False) -> str:
    if recovery_or_result is None:
        return "No task recovery data."
    if isinstance(recovery_or_result, TaskRecoveryResult):
        result = recovery_or_result
        lines = ["# Task recovery result"]
        lines.append(f"Task: {result.task_id or '[none]'}")
        lines.append(f"Action: {result.action or '[none]'}")
        lines.append(f"Dry run: {result.dry_run}")
        lines.append(f"OK: {result.ok}")
        if result.message:
            lines.append(f"Message: {result.message}")
        if result.error:
            lines.append(f"Error: {result.error}")
        if result.recovery:
            lines.extend(["", "## Recovery plan", task_recovery_text(result.recovery, full=False)])
        if result.execution:
            if "ok" in result.execution:
                lines.extend(["", "## Executor result", task_work_execution_text(_dict_to_execution(result.execution), full=full)])
            else:
                lines.extend(["", "## Retry preview", json.dumps(result.execution, indent=2, default=str)])
        if full:
            lines.extend(["", "## Raw", json.dumps(result.to_dict(), indent=2, default=str)])
        return "\n".join(lines).strip()

    recovery = recovery_or_result
    lines = [
        "# Task recovery plan",
        f"Task: {recovery.get('task_id') or '[none]'}",
        f"Stage: {recovery.get('stage_label') or recovery.get('stage') or '[unknown]'}",
        f"Category: {recovery.get('category') or '[unknown]'}",
        f"Recoverable: {recovery.get('recoverable')}",
        f"Retry count: {recovery.get('retry_count', 0)}",
    ]
    if recovery.get("failure_text"):
        lines.extend(["", "## Failure context", str(recovery.get("failure_text"))])
    options = recovery.get("options") or []
    if options:
        lines.extend(["", "## Recovery options"])
        for option in options:
            recommended = " [recommended]" if option.get("recommended") else ""
            lines.append(f"- {option.get('label')}{recommended}: {option.get('description')}")
            if option.get("command"):
                lines.append(f"  command: {option.get('command')}")
    else:
        lines.extend(["", "No recovery options available for this task state."])
    if full:
        lines.extend(["", "## Raw", json.dumps(recovery, indent=2, default=str)])
    return "\n".join(lines).strip()


def _dict_to_execution(data: dict[str, Any]):
    # Local import avoids creating a mandatory dependency cycle in static readers.
    from task_work_executor import TaskWorkExecutionResult

    valid_keys = set(TaskWorkExecutionResult.__dataclass_fields__.keys())
    return TaskWorkExecutionResult(**{key: value for key, value in data.items() if key in valid_keys})


def print_task_recovery(task_id: str, full: bool = False) -> None:
    print(task_recovery_text(build_task_recovery(task_id), full=full))


def print_task_recoveries(project: str = "", include_nonrecoverable: bool = False, full: bool = False) -> None:
    summary = task_recovery_summary(project=project)
    print("# Task recovery summary")
    print(f"Recoverable: {summary.get('recoverable')}")
    print(f"Needs attention: {summary.get('needs_attention')}")
    print(f"Categories: {json.dumps(summary.get('categories', {}), sort_keys=True)}")
    print()
    rows = list_task_recoveries(project=project, include_nonrecoverable=include_nonrecoverable)
    if not rows:
        print("No recoverable tasks found.")
        return
    for recovery in rows:
        print(task_recovery_text(recovery, full=full))
        print("-" * 72)


def print_mark_task_ready_for_retry(task_id: str, note: str = "", full: bool = False) -> None:
    result = mark_task_ready_for_retry(task_id, note=note)
    print(task_recovery_text(result, full=full))


def print_retry_task_work(
    task_id: str,
    dry_run: bool = True,
    allow_approval_required: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    result = retry_task_work(task_id, dry_run=dry_run, allow_approval_required=allow_approval_required, use_ai=use_ai)
    print(task_recovery_text(result, full=full))
