from __future__ import annotations

"""
Task-centered executor for safe, supervised work.

v5.3 consolidation note:
    This module is the canonical executor for task/work items. It operates on
    task_queue.py / data/tasks.json directly. The older work_queue_executor.py
    remains as a compatibility wrapper so legacy CLI, dashboard, and API routes
    keep working while names migrate from "work item" to "task work".
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from code_reviewer import review_project_file
from command_runner import run_approved_command, validate_command
from memory import store_memory
from task_patch_bridge import suggest_patch_for_task
from task_queue import (
    get_task,
    list_tasks,
    resolve_task_id,
    task_detail_text,
    update_task_fields,
)
from test_runner import run_test_workflow


ACTION_REVIEW_FILE = "review_file"
ACTION_RUN_COMMAND = "run_command"
ACTION_SUGGEST_PATCH = "suggest_patch"
ACTION_TEST_PROJECT = "test_project"
ACTION_DASHBOARD_NOTE = "dashboard_note"
ACTION_MANUAL = "manual"

EXECUTABLE_ACTIONS = {
    ACTION_REVIEW_FILE,
    ACTION_RUN_COMMAND,
    ACTION_SUGGEST_PATCH,
    ACTION_TEST_PROJECT,
    ACTION_DASHBOARD_NOTE,
}

READY_STATUSES = {"planned", "active"}
AUTOMATIC_RISKS = {"low"}
PATH_PATTERN = re.compile(r"([A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)")
QUOTED_PATTERN = re.compile(r"['\"]([^'\"]+)['\"]")


@dataclass
class TaskWorkExecutionResult:
    ok: bool
    task_id: str = ""
    action_type: str = ACTION_MANUAL
    dry_run: bool = False
    message: str = ""
    error: str = ""
    result: str = ""
    blocked: bool = False
    completed: bool = False
    metadata: dict[str, Any] | None = None
    # Compatibility alias for v4.7-v5.2 callers.
    work_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("work_id") and data.get("task_id"):
            data["work_id"] = data["task_id"]
        return data


# Compatibility name for old imports and serialized UI payloads.
WorkExecutionResult = TaskWorkExecutionResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, limit: int = 4000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED: task work executor output exceeded {limit} characters]"


def _task_metadata(task: dict[str, Any] | None) -> dict[str, Any]:
    metadata = (task or {}).get("metadata") if isinstance(task, dict) else {}
    return dict(metadata) if isinstance(metadata, dict) else {}


def _text_for_task(task: dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    parts = [
        str(task.get("title") or ""),
        str(task.get("description") or ""),
        str(task.get("command") or ""),
    ]
    if metadata:
        parts.append(json.dumps(metadata, indent=2))
    return "\n".join(parts).strip()


def _metadata_action_type(task: dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    raw = str(metadata.get("action_type") or metadata.get("type") or "").strip().lower()
    aliases = {
        "review": ACTION_REVIEW_FILE,
        "inspect": ACTION_REVIEW_FILE,
        "file_review": ACTION_REVIEW_FILE,
        "command": ACTION_RUN_COMMAND,
        "run": ACTION_RUN_COMMAND,
        "patch": ACTION_SUGGEST_PATCH,
        "fix": ACTION_SUGGEST_PATCH,
        "test": ACTION_TEST_PROJECT,
        "tests": ACTION_TEST_PROJECT,
        "note": ACTION_DASHBOARD_NOTE,
        "manual": ACTION_MANUAL,
    }
    return aliases.get(raw, raw)


def classify_task_work(task: dict[str, Any]) -> str:
    metadata_type = _metadata_action_type(task)
    if metadata_type in EXECUTABLE_ACTIONS or metadata_type == ACTION_MANUAL:
        return metadata_type

    text = _text_for_task(task).lower()

    if any(token in text for token in ["review", "inspect", "look through", "analyze file", "check file"]):
        return ACTION_REVIEW_FILE

    if any(token in text for token in ["suggest patch", "propose patch", "make patch", "patch proposal"]):
        return ACTION_SUGGEST_PATCH

    if any(token in text for token in ["run tests", "test workflow", "pytest", "compile", "py_compile"]):
        return ACTION_TEST_PROJECT

    if any(token in text for token in ["run command", "execute command", "command:"]):
        return ACTION_RUN_COMMAND

    if any(token in text for token in ["dashboard note", "note for dashboard", "record note"]):
        return ACTION_DASHBOARD_NOTE

    return ACTION_MANUAL


def can_execute_task_work(task: dict[str, Any], allow_approval_required: bool = False) -> tuple[bool, str]:
    status = str(task.get("status") or "planned").lower().strip()
    if status not in READY_STATUSES:
        metadata = _task_metadata(task)
        approval_linked = bool(metadata.get("approval_id"))
        if not (status == "blocked" and allow_approval_required and approval_linked):
            return False, f"Task is {status}, not planned/active."

    risk = str(task.get("risk") or "low").lower().strip()
    if risk not in AUTOMATIC_RISKS and not allow_approval_required:
        return False, f"Task risk is {risk}; only low-risk tasks execute automatically."

    if bool(task.get("requires_approval")) and not allow_approval_required:
        return False, "Task requires approval before execution."

    return True, ""


def _target_file_from_task(task: dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    for key in ["target_file", "patch_target_file", "file", "path", "relative_path"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    text = _text_for_task(task)
    for quoted in QUOTED_PATTERN.findall(text):
        if "." in quoted and not quoted.strip().startswith("--"):
            return quoted.strip()

    match = PATH_PATTERN.search(text)
    if match:
        return match.group(1).strip()

    return ""


def _command_from_task(task: dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    for key in ["command", "cmd", "shell_command", "recommended_command"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    command = str(task.get("command") or "").strip()
    if command:
        return command

    text = _text_for_task(task)
    command_match = re.search(r"command\s*:\s*(.+)", text, flags=re.IGNORECASE)
    if command_match:
        return command_match.group(1).strip()

    return ""


def _test_commands_from_task(task: dict[str, Any]) -> list[str]:
    metadata = _task_metadata(task)
    raw = metadata.get("test_commands") or metadata.get("commands") or []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(command).strip() for command in raw if str(command).strip()]
    follow_ups = task.get("follow_up_commands") or []
    if isinstance(follow_ups, list):
        return [str(command).strip() for command in follow_ups if str(command).strip()]
    return []


def _dry_run_message(task: dict[str, Any], action_type: str) -> str:
    target_file = _target_file_from_task(task)
    command = _command_from_task(task)
    commands = _test_commands_from_task(task)

    lines = [
        "# Task work dry run",
        "",
        task_detail_text(task, full=True),
        "",
        f"Classified action: {action_type}",
    ]

    if target_file and action_type in {ACTION_REVIEW_FILE, ACTION_SUGGEST_PATCH}:
        lines.append(f"Target file: {target_file}")
    if command:
        validation = validate_command(command)
        lines.append(f"Command: {command}")
        lines.append(f"Command allowed: {validation.ok}")
        if validation.reason:
            lines.append(f"Command validation reason: {validation.reason}")
    if commands:
        lines.append("Test commands:")
        lines.extend(f"- {command}" for command in commands)

    if action_type == ACTION_MANUAL:
        lines.append("This task needs manual handling. No safe automatic executor matched it.")

    return "\n".join(lines)


def _execute_review_file(task: dict[str, Any], use_ai: bool) -> TaskWorkExecutionResult:
    task_id = str(task.get("id") or "")
    target_file = _target_file_from_task(task)
    if not target_file:
        return TaskWorkExecutionResult(False, task_id=task_id, work_id=task_id, action_type=ACTION_REVIEW_FILE, error="No target file found in metadata, title, command, or description.")

    review = review_project_file(target_file, use_ai=use_ai)
    if not review.ok:
        return TaskWorkExecutionResult(False, task_id=task_id, work_id=task_id, action_type=ACTION_REVIEW_FILE, error=review.error)

    result_text = _truncate(review.text)
    return TaskWorkExecutionResult(True, task_id=task_id, work_id=task_id, action_type=ACTION_REVIEW_FILE, result=result_text, completed=True)


def _execute_run_command(task: dict[str, Any], dry_run: bool) -> TaskWorkExecutionResult:
    task_id = str(task.get("id") or "")
    command = _command_from_task(task)
    if not command:
        return TaskWorkExecutionResult(False, task_id=task_id, work_id=task_id, action_type=ACTION_RUN_COMMAND, error="No command found in task command, metadata, or description. Use task.command, metadata.command, or include 'command: ...'.")

    command_result = run_approved_command(command, dry_run=dry_run)
    lines = [
        f"Command: {command_result.command}",
        f"Dry run: {command_result.dry_run}",
        f"OK: {command_result.ok}",
        f"Return code: {command_result.return_code}",
    ]
    if command_result.message:
        lines.append(f"Message: {command_result.message}")
    if command_result.error:
        lines.append(f"Error: {command_result.error}")
    if command_result.stdout:
        lines.extend(["", "--- stdout ---", _truncate(command_result.stdout, 2400)])
    if command_result.stderr:
        lines.extend(["", "--- stderr ---", _truncate(command_result.stderr, 2400)])

    return TaskWorkExecutionResult(
        ok=command_result.ok,
        task_id=task_id,
        work_id=task_id,
        action_type=ACTION_RUN_COMMAND,
        dry_run=dry_run,
        result="\n".join(lines),
        error=command_result.error,
        completed=command_result.ok and not dry_run,
    )


def _execute_suggest_patch(task: dict[str, Any], use_ai: bool) -> TaskWorkExecutionResult:
    task_id = str(task.get("id") or "")
    patch = suggest_patch_for_task(task_id, use_ai=use_ai, dry_run=False)
    if not patch.ok:
        return TaskWorkExecutionResult(False, task_id=task_id, work_id=task_id, action_type=ACTION_SUGGEST_PATCH, error=patch.error)

    result_text = _truncate(patch.result)
    return TaskWorkExecutionResult(
        True,
        task_id=task_id,
        work_id=task_id,
        action_type=ACTION_SUGGEST_PATCH,
        result=result_text,
        completed=True,
        metadata={
            "patch_id": patch.patch_id,
            "target_file": patch.target_file,
            "patch_status": "proposed",
        },
    )


def _execute_test_project(task: dict[str, Any], dry_run: bool) -> TaskWorkExecutionResult:
    task_id = str(task.get("id") or "")
    commands = _test_commands_from_task(task)
    test_result = run_test_workflow(commands=commands, dry_run=dry_run)

    lines = [
        f"Test report: {test_result.report_id}",
        f"Dry run: {test_result.dry_run}",
        f"OK: {test_result.ok}",
        f"Status: {test_result.status}",
    ]
    if test_result.recommendation:
        lines.append(f"Recommendation: {test_result.recommendation}")
    if test_result.error:
        lines.append(f"Error: {test_result.error}")

    return TaskWorkExecutionResult(
        ok=test_result.ok,
        task_id=task_id,
        work_id=task_id,
        action_type=ACTION_TEST_PROJECT,
        dry_run=dry_run,
        result="\n".join(lines),
        error=test_result.error,
        completed=test_result.ok and not dry_run,
        metadata={"test_report_id": test_result.report_id},
    )


def _execute_dashboard_note(task: dict[str, Any]) -> TaskWorkExecutionResult:
    task_id = str(task.get("id") or "")
    project_id = str(task.get("project") or "")
    result = f"Dashboard note recorded from task {task_id}: {task.get('title')}\n\n{task.get('description', '')}".strip()
    store_memory({
        "type": "dashboard_note",
        "content": result,
        "source": "task_work_executor",
        "task_id": task_id,
        "work_id": task_id,
        "project_id": project_id,
    })
    return TaskWorkExecutionResult(True, task_id=task_id, work_id=task_id, action_type=ACTION_DASHBOARD_NOTE, result=result, completed=True)


def _merge_metadata(task: dict[str, Any], updates: dict[str, Any] | None) -> dict[str, Any]:
    metadata = _task_metadata(task)
    if updates:
        metadata.update(updates)
    return metadata


def execute_task_work_item(
    task_id: str,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
) -> TaskWorkExecutionResult:
    resolved_task_id = resolve_task_id(task_id)
    task = get_task(resolved_task_id or task_id)
    if not task:
        return TaskWorkExecutionResult(False, task_id=task_id, work_id=task_id, error=f"Task not found: {task_id}")

    actual_task_id = str(task.get("id") or resolved_task_id or task_id)
    action_type = classify_task_work(task)
    allowed, reason = can_execute_task_work(task, allow_approval_required=allow_approval_required)
    if not allowed:
        approval_metadata: dict[str, Any] = {}
        if not dry_run:
            if "requires approval" in reason.lower() or "risk is" in reason.lower():
                try:
                    from task_approval_bridge import request_task_work_approval

                    approval = request_task_work_approval(
                        actual_task_id,
                        reason=reason,
                        use_ai=use_ai,
                        force=True,
                    )
                    if approval.ok:
                        approval_metadata = {
                            "approval_id": approval.approval_id,
                            "approval_status": "pending",
                            "approval_command": approval.command,
                        }
                        reason = f"{reason} Approval request created: {approval.approval_id}"
                    elif approval.error:
                        approval_metadata = {"approval_request_error": approval.error}
                except Exception as error:  # Approval creation must not hide the original block reason.
                    approval_metadata = {"approval_request_error": str(error)}
            elif str(task.get("status")) == "planned":
                update_task_fields(
                    actual_task_id,
                    status="blocked",
                    blocked_reason=reason,
                    metadata={"last_executor_block_reason": reason, "action_type": action_type},
                )

        metadata = {"last_executor_block_reason": reason, "action_type": action_type, **approval_metadata}
        return TaskWorkExecutionResult(
            False,
            task_id=actual_task_id,
            work_id=actual_task_id,
            action_type=action_type,
            error=reason,
            blocked=True,
            metadata=metadata,
        )

    if dry_run:
        return TaskWorkExecutionResult(True, task_id=actual_task_id, work_id=actual_task_id, action_type=action_type, dry_run=True, result=_dry_run_message(task, action_type))

    if action_type == ACTION_MANUAL:
        reason = "No safe automatic executor matched this task. Manual handling required."
        update_task_fields(actual_task_id, status="blocked", blocked_reason=reason, metadata={"last_executor_block_reason": reason, "action_type": action_type})
        return TaskWorkExecutionResult(False, task_id=actual_task_id, work_id=actual_task_id, action_type=action_type, error=reason, blocked=True)

    update_task_fields(actual_task_id, status="active", metadata={"last_executed_at": _now(), "action_type": action_type})
    task = get_task(actual_task_id) or task

    if action_type == ACTION_REVIEW_FILE:
        result = _execute_review_file(task, use_ai=use_ai)
    elif action_type == ACTION_RUN_COMMAND:
        result = _execute_run_command(task, dry_run=False)
    elif action_type == ACTION_SUGGEST_PATCH:
        result = _execute_suggest_patch(task, use_ai=use_ai)
    elif action_type == ACTION_TEST_PROJECT:
        result = _execute_test_project(task, dry_run=False)
    elif action_type == ACTION_DASHBOARD_NOTE:
        result = _execute_dashboard_note(task)
    else:
        result = TaskWorkExecutionResult(False, task_id=actual_task_id, work_id=actual_task_id, action_type=action_type, error=f"Unsupported action type: {action_type}")

    latest_task = get_task(actual_task_id) or task
    metadata = _merge_metadata(latest_task, {**(result.metadata or {}), "last_executed_at": _now(), "action_type": action_type})

    if result.ok and result.completed:
        update_task_fields(
            actual_task_id,
            status="done",
            result=result.result,
            metadata=metadata,
            patch_id=str(metadata.get("patch_id") or latest_task.get("patch_id") or ""),
            patch_status=str(metadata.get("patch_status") or latest_task.get("patch_status") or ""),
            work_status="done",
        )
    elif result.ok:
        update_task_fields(actual_task_id, status="planned", result=result.result, metadata=metadata, work_status="pending")
    else:
        update_task_fields(actual_task_id, status="blocked", result=result.result or result.error, metadata=metadata, work_status="failed", blocked_reason=result.error or "Task work execution failed.")

    store_memory({
        "type": "task_work_execution_event",
        "content": f"Executed task {actual_task_id} as {action_type}. ok={result.ok}",
        "source": "task_work_executor",
        "task_id": actual_task_id,
        "work_id": actual_task_id,
        "project_id": str(latest_task.get("project") or ""),
        "action_type": action_type,
        "ok": result.ok,
    })

    return result


def _safe_ready_tasks(project_id: Optional[str] = None) -> list[dict[str, Any]]:
    tasks = [task for task in list_tasks(project=project_id or "", include_cancelled=False) if str(task.get("status")) in READY_STATUSES]
    return [task for task in tasks if str(task.get("risk", "low")).lower() == "low" and not bool(task.get("requires_approval"))]


def get_next_task_work(project_id: Optional[str] = None) -> dict[str, Any] | None:
    safe = _safe_ready_tasks(project_id=project_id)
    if safe:
        return safe[0]
    ready = [task for task in list_tasks(project=project_id or "", include_cancelled=False) if str(task.get("status")) in READY_STATUSES]
    return ready[0] if ready else None


def execute_next_task_work(
    project_id: Optional[str] = None,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
) -> TaskWorkExecutionResult:
    task = get_next_task_work(project_id=project_id)
    if not task:
        return TaskWorkExecutionResult(True, message="No ready task found.", dry_run=dry_run)

    return execute_task_work_item(
        str(task.get("id") or ""),
        dry_run=dry_run,
        allow_approval_required=allow_approval_required,
        use_ai=use_ai,
    )


def task_work_execution_text(result: TaskWorkExecutionResult, full: bool = False) -> str:
    lines = ["# Task work execution"]

    if result.message:
        lines.append(result.message)

    task_id = result.task_id or result.work_id
    if task_id:
        lines.append(f"Task: {task_id}")
    lines.append(f"Action type: {result.action_type}")
    lines.append(f"Dry run: {result.dry_run}")
    lines.append(f"OK: {result.ok}")
    if result.blocked:
        lines.append("Blocked: True")
    if result.completed:
        lines.append("Completed: True")
    if result.error:
        lines.append(f"Error: {result.error}")

    if result.result:
        lines.extend(["", "## Result", result.result if full else _truncate(result.result, 2200)])

    if full and result.metadata:
        lines.extend(["", "## Metadata", json.dumps(result.metadata, indent=2)])

    return "\n".join(lines).strip()


def print_execute_next_task_work_item(
    project_id: Optional[str] = None,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    result = execute_next_task_work(
        project_id=project_id,
        dry_run=dry_run,
        allow_approval_required=allow_approval_required,
        use_ai=use_ai,
    )
    print(task_work_execution_text(result, full=full))


def print_execute_task_work_item(
    task_id: str,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    result = execute_task_work_item(
        task_id,
        dry_run=dry_run,
        allow_approval_required=allow_approval_required,
        use_ai=use_ai,
    )
    print(task_work_execution_text(result, full=full))


# Legacy compatibility aliases. Prefer the task_* names above in new code.
def classify_work_item(item: Any) -> str:
    task = item if isinstance(item, dict) else get_task(getattr(item, "id", ""))
    return classify_task_work(task or {})


def can_execute_work_item(item: Any, allow_approval_required: bool = False) -> tuple[bool, str]:
    task = item if isinstance(item, dict) else get_task(getattr(item, "id", ""))
    return can_execute_task_work(task or {}, allow_approval_required=allow_approval_required)


def execute_work_item(
    item_id: str,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
) -> TaskWorkExecutionResult:
    return execute_task_work_item(item_id, dry_run=dry_run, allow_approval_required=allow_approval_required, use_ai=use_ai)


def execute_next_work_item(
    project_id: Optional[str] = None,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
) -> TaskWorkExecutionResult:
    return execute_next_task_work(project_id=project_id, dry_run=dry_run, allow_approval_required=allow_approval_required, use_ai=use_ai)


def work_execution_text(result: TaskWorkExecutionResult, full: bool = False) -> str:
    return task_work_execution_text(result, full=full)


def print_execute_next_work_item(
    project_id: Optional[str] = None,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    print_execute_next_task_work_item(project_id=project_id, dry_run=dry_run, allow_approval_required=allow_approval_required, use_ai=use_ai, full=full)


def print_execute_work_item(
    item_id: str,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    print_execute_task_work_item(item_id, dry_run=dry_run, allow_approval_required=allow_approval_required, use_ai=use_ai, full=full)
