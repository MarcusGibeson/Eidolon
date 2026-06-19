from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from code_reviewer import review_project_file
from command_runner import run_approved_command, validate_command
from memory import store_memory
from patch_suggester import suggest_patch
from test_runner import run_test_workflow
from work_queue import (
    WorkItem,
    find_work_item,
    format_work_item,
    get_next_work_item,
    update_work_item,
)


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

PATH_PATTERN = re.compile(r"([A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)")
QUOTED_PATTERN = re.compile(r"['\"]([^'\"]+)['\"]")


@dataclass
class WorkExecutionResult:
    ok: bool
    work_id: str = ""
    action_type: str = ACTION_MANUAL
    dry_run: bool = False
    message: str = ""
    error: str = ""
    result: str = ""
    blocked: bool = False
    completed: bool = False
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, limit: int = 4000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED: work executor output exceeded {limit} characters]"


def _text_for_item(item: WorkItem) -> str:
    metadata = item.metadata or {}
    return "\n".join([
        item.title or "",
        item.description or "",
        json.dumps(metadata, indent=2) if metadata else "",
    ]).strip()


def _metadata_action_type(item: WorkItem) -> str:
    metadata = item.metadata or {}
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


def classify_work_item(item: WorkItem) -> str:
    metadata_type = _metadata_action_type(item)
    if metadata_type in EXECUTABLE_ACTIONS or metadata_type == ACTION_MANUAL:
        return metadata_type

    text = _text_for_item(item).lower()

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


def can_execute_work_item(item: WorkItem, allow_approval_required: bool = False) -> tuple[bool, str]:
    if item.status != "pending":
        return False, f"Work item is {item.status}, not pending."

    if item.risk != "low" and not allow_approval_required:
        return False, f"Work item risk is {item.risk}; only low-risk items execute automatically."

    if item.requires_approval and not allow_approval_required:
        return False, "Work item requires approval before execution."

    return True, ""


def _target_file_from_item(item: WorkItem) -> str:
    metadata = item.metadata or {}
    for key in ["target_file", "file", "path", "relative_path"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    text = _text_for_item(item)

    for quoted in QUOTED_PATTERN.findall(text):
        if "." in quoted and not quoted.strip().startswith("--"):
            return quoted.strip()

    match = PATH_PATTERN.search(text)
    if match:
        return match.group(1).strip()

    return ""


def _command_from_item(item: WorkItem) -> str:
    metadata = item.metadata or {}
    for key in ["command", "cmd", "shell_command"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    text = _text_for_item(item)
    command_match = re.search(r"command\s*:\s*(.+)", text, flags=re.IGNORECASE)
    if command_match:
        return command_match.group(1).strip()

    return ""


def _patch_request_from_item(item: WorkItem) -> str:
    metadata = item.metadata or {}
    for key in ["request", "patch_request", "change_request"]:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value

    return item.description or item.title


def _test_commands_from_item(item: WorkItem) -> list[str]:
    metadata = item.metadata or {}
    raw = metadata.get("test_commands") or metadata.get("commands") or []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(command).strip() for command in raw if str(command).strip()]
    return []


def _dry_run_message(item: WorkItem, action_type: str) -> str:
    target_file = _target_file_from_item(item)
    command = _command_from_item(item)
    commands = _test_commands_from_item(item)

    lines = [
        "# Work queue dry run",
        "",
        format_work_item(item, full=True),
        "",
        f"Classified action: {action_type}",
    ]

    if target_file:
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
        lines.append("This item needs manual handling. No safe automatic executor matched it.")

    return "\n".join(lines)


def _execute_review_file(item: WorkItem, use_ai: bool) -> WorkExecutionResult:
    target_file = _target_file_from_item(item)
    if not target_file:
        return WorkExecutionResult(False, work_id=item.id, action_type=ACTION_REVIEW_FILE, error="No target file found in metadata, title, or description.")

    review = review_project_file(target_file, use_ai=use_ai)
    if not review.ok:
        return WorkExecutionResult(False, work_id=item.id, action_type=ACTION_REVIEW_FILE, error=review.error)

    result_text = _truncate(review.text)
    return WorkExecutionResult(True, work_id=item.id, action_type=ACTION_REVIEW_FILE, result=result_text, completed=True)


def _execute_run_command(item: WorkItem, dry_run: bool) -> WorkExecutionResult:
    command = _command_from_item(item)
    if not command:
        return WorkExecutionResult(False, work_id=item.id, action_type=ACTION_RUN_COMMAND, error="No command found in metadata or description. Use metadata.command or include 'command: ...'.")

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

    return WorkExecutionResult(
        ok=command_result.ok,
        work_id=item.id,
        action_type=ACTION_RUN_COMMAND,
        dry_run=dry_run,
        result="\n".join(lines),
        error=command_result.error,
        completed=command_result.ok and not dry_run,
    )


def _execute_suggest_patch(item: WorkItem, use_ai: bool) -> WorkExecutionResult:
    target_file = _target_file_from_item(item)
    if not target_file:
        return WorkExecutionResult(False, work_id=item.id, action_type=ACTION_SUGGEST_PATCH, error="No target file found for patch suggestion.")

    if not use_ai:
        return WorkExecutionResult(False, work_id=item.id, action_type=ACTION_SUGGEST_PATCH, error="Patch suggestion requires local AI. Run without --no-ai-work-executor.")

    patch = suggest_patch(target_file, _patch_request_from_item(item), use_ai=True)
    if not patch.ok:
        return WorkExecutionResult(False, work_id=item.id, action_type=ACTION_SUGGEST_PATCH, error=patch.error)

    result_text = _truncate(patch.text)
    return WorkExecutionResult(
        True,
        work_id=item.id,
        action_type=ACTION_SUGGEST_PATCH,
        result=result_text,
        completed=True,
        metadata={"patch_id": patch.patch_id, "target_file": patch.target_file},
    )


def _execute_test_project(item: WorkItem, dry_run: bool) -> WorkExecutionResult:
    commands = _test_commands_from_item(item)
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

    return WorkExecutionResult(
        ok=test_result.ok,
        work_id=item.id,
        action_type=ACTION_TEST_PROJECT,
        dry_run=dry_run,
        result="\n".join(lines),
        error=test_result.error,
        completed=test_result.ok and not dry_run,
        metadata={"test_report_id": test_result.report_id},
    )


def _execute_dashboard_note(item: WorkItem) -> WorkExecutionResult:
    result = f"Dashboard note recorded from work item {item.id}: {item.title}\n\n{item.description}".strip()
    store_memory({
        "type": "dashboard_note",
        "content": result,
        "source": "work_queue_executor",
        "work_id": item.id,
        "project_id": item.project_id,
    })
    return WorkExecutionResult(True, work_id=item.id, action_type=ACTION_DASHBOARD_NOTE, result=result, completed=True)


def execute_work_item(
    item_id: str,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
) -> WorkExecutionResult:
    item = find_work_item(item_id)
    if not item:
        return WorkExecutionResult(False, work_id=item_id, error=f"Work item not found: {item_id}")

    action_type = classify_work_item(item)
    allowed, reason = can_execute_work_item(item, allow_approval_required=allow_approval_required)
    if not allowed:
        if not dry_run and item.status == "pending":
            update_work_item(item.id, status="blocked", blocked_reason=reason)
        return WorkExecutionResult(False, work_id=item.id, action_type=action_type, error=reason, blocked=True)

    if dry_run:
        return WorkExecutionResult(True, work_id=item.id, action_type=action_type, dry_run=True, result=_dry_run_message(item, action_type))

    if action_type == ACTION_MANUAL:
        reason = "No safe automatic executor matched this work item. Manual handling required."
        update_work_item(item.id, status="blocked", blocked_reason=reason)
        return WorkExecutionResult(False, work_id=item.id, action_type=action_type, error=reason, blocked=True)

    update_work_item(item.id, status="active")

    if action_type == ACTION_REVIEW_FILE:
        result = _execute_review_file(item, use_ai=use_ai)
    elif action_type == ACTION_RUN_COMMAND:
        result = _execute_run_command(item, dry_run=False)
    elif action_type == ACTION_SUGGEST_PATCH:
        result = _execute_suggest_patch(item, use_ai=use_ai)
    elif action_type == ACTION_TEST_PROJECT:
        result = _execute_test_project(item, dry_run=False)
    elif action_type == ACTION_DASHBOARD_NOTE:
        result = _execute_dashboard_note(item)
    else:
        result = WorkExecutionResult(False, work_id=item.id, action_type=action_type, error=f"Unsupported action type: {action_type}")

    if result.ok and result.completed:
        update_work_item(item.id, status="done", result=result.result, metadata={**(item.metadata or {}), **(result.metadata or {}), "last_executed_at": _now(), "action_type": action_type})
    elif result.ok:
        update_work_item(item.id, status="pending", result=result.result, metadata={**(item.metadata or {}), **(result.metadata or {}), "last_executed_at": _now(), "action_type": action_type})
    else:
        update_work_item(item.id, status="failed", result=result.result or result.error, metadata={**(item.metadata or {}), **(result.metadata or {}), "last_executed_at": _now(), "action_type": action_type})

    store_memory({
        "type": "work_queue_execution_event",
        "content": f"Executed work item {item.id} as {action_type}. ok={result.ok}",
        "source": "work_queue_executor",
        "work_id": item.id,
        "project_id": item.project_id,
        "action_type": action_type,
        "ok": result.ok,
    })

    return result


def execute_next_work_item(
    project_id: Optional[str] = None,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
) -> WorkExecutionResult:
    item = get_next_work_item(project_id=project_id)
    if not item:
        return WorkExecutionResult(True, message="No pending work item found.", dry_run=dry_run)

    return execute_work_item(
        item.id,
        dry_run=dry_run,
        allow_approval_required=allow_approval_required,
        use_ai=use_ai,
    )


def work_execution_text(result: WorkExecutionResult, full: bool = False) -> str:
    lines = ["# Work queue execution"]

    if result.message:
        lines.append(result.message)

    if result.work_id:
        lines.append(f"Work item: {result.work_id}")
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


def print_execute_next_work_item(
    project_id: Optional[str] = None,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    result = execute_next_work_item(
        project_id=project_id,
        dry_run=dry_run,
        allow_approval_required=allow_approval_required,
        use_ai=use_ai,
    )
    print(work_execution_text(result, full=full))


def print_execute_work_item(
    item_id: str,
    dry_run: bool = False,
    allow_approval_required: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    result = execute_work_item(
        item_id,
        dry_run=dry_run,
        allow_approval_required=allow_approval_required,
        use_ai=use_ai,
    )
    print(work_execution_text(result, full=full))
