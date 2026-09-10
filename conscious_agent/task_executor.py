from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from command_runner import run_approved_command, CommandRunResult
from memory import store_memory
from task_queue import (
    get_task,
    load_tasks_data,
    save_tasks_data,
    resolve_task_id,
    set_task_status,
    task_detail_text,
)


@dataclass
class TaskExecutionResult:
    ok: bool
    task_id: str
    command: str = ""
    command_index: int = 0
    dry_run: bool = False
    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    error: str = ""
    task_completed: bool = False


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED: task execution output exceeded {limit} characters]"


def _task_command_options(task: dict[str, Any]) -> list[str]:
    """
    Returns command options for a task.

    Index 0 is the primary task command.
    Index 1+ are follow-up commands.
    Empty commands are skipped.
    """
    commands: list[str] = []

    primary = str(task.get("command", "")).strip()
    if primary:
        commands.append(primary)

    for command in task.get("follow_up_commands", []) or []:
        command_text = str(command).strip()
        if command_text:
            commands.append(command_text)

    return commands


def task_command_options_text(task_id: str = "latest-ready") -> str:
    task = get_task(task_id)
    if not task:
        return f"Task not found: {task_id}"

    commands = _task_command_options(task)
    lines = [f"# Task command options: {task.get('id')}", f"Title: {task.get('title')}"]

    if not commands:
        lines.append("No command options found for this task.")
        return "\n".join(lines)

    for index, command in enumerate(commands):
        label = "primary" if index == 0 else f"follow-up {index}"
        lines.append(f"[{index}] {label}: {command}")

    lines.append("")
    lines.append("Run one with:")
    lines.append(f"python conscious_agent/main.py --execute-task {task.get('id')} --task-command-index 0 --dry-run")
    return "\n".join(lines)


def _update_task_execution_history(
    task_id: str,
    command_result: CommandRunResult,
    command_index: int,
    completed_task: bool = False,
) -> None:
    data = load_tasks_data()
    task = None

    for existing in data.get("tasks", []):
        if existing.get("id") == task_id:
            task = existing
            break

    if not task:
        return

    history_entry = {
        "executed_at": _now(),
        "command": command_result.command,
        "command_index": command_index,
        "dry_run": command_result.dry_run,
        "ok": command_result.ok,
        "return_code": command_result.return_code,
        "message": command_result.message,
        "error": command_result.error,
        "stdout_preview": _truncate(command_result.stdout, limit=1200),
        "stderr_preview": _truncate(command_result.stderr, limit=1200),
        "completed_task": completed_task,
    }

    task.setdefault("execution_history", []).append(history_entry)
    task["last_command"] = command_result.command
    task["last_command_ok"] = command_result.ok
    task["last_command_return_code"] = command_result.return_code
    task["last_executed_at"] = history_entry["executed_at"]
    task["updated_at"] = history_entry["executed_at"]

    if command_result.dry_run:
        task.setdefault("notes", []).append(
            f"{history_entry['executed_at']}: Dry-run command check {'passed' if command_result.ok else 'failed'}: {command_result.command}"
        )
    else:
        task.setdefault("notes", []).append(
            f"{history_entry['executed_at']}: Ran task command with status {'success' if command_result.ok else 'failed'}: {command_result.command}"
        )

    save_tasks_data(data)


def execute_task_command(
    task_id: str = "latest-ready",
    command_index: int = 0,
    dry_run: bool = False,
    complete_on_success: bool = False,
) -> TaskExecutionResult:
    resolved_task_id = resolve_task_id(task_id)
    if not resolved_task_id:
        return TaskExecutionResult(False, task_id=task_id, error=f"Task not found: {task_id}", dry_run=dry_run)

    task = get_task(resolved_task_id)
    if not task:
        return TaskExecutionResult(False, task_id=resolved_task_id, error=f"Task not found: {task_id}", dry_run=dry_run)

    commands = _task_command_options(task)
    if not commands:
        return TaskExecutionResult(False, task_id=resolved_task_id, error="Task has no command or follow-up commands.", dry_run=dry_run)

    if command_index < 0 or command_index >= len(commands):
        return TaskExecutionResult(
            False,
            task_id=resolved_task_id,
            error=f"Command index {command_index} is out of range. Use --task-command-options {resolved_task_id}.",
            dry_run=dry_run,
        )

    command = commands[command_index]

    if not dry_run and task.get("status") == "planned":
        set_task_status(resolved_task_id, "active", note="Task started by task execution assistant.")

    command_result = run_approved_command(command, dry_run=dry_run)

    completed_task = False
    if command_result.ok and complete_on_success and not dry_run:
        status_result = set_task_status(
            resolved_task_id,
            "done",
            note=f"Completed automatically after successful task command: {command}",
        )
        completed_task = status_result.ok

    _update_task_execution_history(
        resolved_task_id,
        command_result=command_result,
        command_index=command_index,
        completed_task=completed_task,
    )

    status = "success" if command_result.ok else "failed"
    store_memory({
        "type": "task_execution_event",
        "content": f"Task {resolved_task_id} command execution {status}: {command}",
        "source": "task_executor",
        "task_id": resolved_task_id,
        "command": command,
        "command_index": command_index,
        "dry_run": dry_run,
        "ok": command_result.ok,
        "return_code": command_result.return_code,
    })

    return TaskExecutionResult(
        ok=command_result.ok,
        task_id=resolved_task_id,
        command=command,
        command_index=command_index,
        dry_run=dry_run,
        return_code=command_result.return_code,
        stdout=command_result.stdout,
        stderr=command_result.stderr,
        message=command_result.message,
        error=command_result.error,
        task_completed=completed_task,
    )


def task_execution_history_text(task_id: str = "latest") -> str:
    task = get_task(task_id)
    if not task:
        return f"Task not found: {task_id}"

    history = task.get("execution_history", []) or []
    lines = [f"# Task execution history: {task.get('id')}", f"Title: {task.get('title')}"]

    if not history:
        lines.append("No execution history found for this task.")
        return "\n".join(lines)

    for entry in history[-10:]:
        lines.append("")
        lines.append(
            f"{entry.get('executed_at')} | "
            f"dry_run={entry.get('dry_run')} | "
            f"ok={entry.get('ok')} | "
            f"return_code={entry.get('return_code')}"
        )
        lines.append(f"Command: {entry.get('command')}")
        if entry.get("error"):
            lines.append(f"Error: {entry.get('error')}")
        if entry.get("stdout_preview"):
            lines.append("stdout preview:")
            lines.append(str(entry.get("stdout_preview")))
        if entry.get("stderr_preview"):
            lines.append("stderr preview:")
            lines.append(str(entry.get("stderr_preview")))

    return "\n".join(lines)


def print_task_command_options(task_id: str = "latest-ready") -> None:
    print(task_command_options_text(task_id))


def print_execute_task(
    task_id: str = "latest-ready",
    command_index: int = 0,
    dry_run: bool = False,
    complete_on_success: bool = False,
) -> None:
    task = get_task(task_id)
    if task:
        print(task_detail_text(task, full=False))
        print()

    result = execute_task_command(
        task_id=task_id,
        command_index=command_index,
        dry_run=dry_run,
        complete_on_success=complete_on_success,
    )

    if not result.ok and result.return_code is None:
        print("Task command was not run.")
        print(f"Reason: {result.error}")
        return

    if result.dry_run:
        print("Dry run completed.")
    else:
        print("Task command executed.")

    print(f"Task: {result.task_id}")
    print(f"Command index: {result.command_index}")
    print(f"Command: {result.command}")
    print(f"Return code: {result.return_code}")
    print(f"OK: {result.ok}")

    if result.message:
        print(f"Message: {result.message}")
    if result.error:
        print(f"Error: {result.error}")

    if result.stdout:
        print("\n--- stdout ---")
        print(result.stdout)

    if result.stderr:
        print("\n--- stderr ---")
        print(result.stderr)

    if result.task_completed:
        print("\nTask marked done because --complete-on-success was used.")
    elif result.ok and not result.dry_run:
        print("\nNext options:")
        print(f"- Complete task: python conscious_agent/main.py --complete-task {result.task_id} --task-note \"Command succeeded\"")
        print(f"- Show history: python conscious_agent/main.py --task-execution-history {result.task_id}")
    elif not result.ok:
        print("\nNext options:")
        print(f"- Review task history: python conscious_agent/main.py --task-execution-history {result.task_id}")
        print(f"- Block task: python conscious_agent/main.py --block-task {result.task_id} \"Command failed; needs review\"")


def print_task_execution_history(task_id: str = "latest") -> None:
    print(task_execution_history_text(task_id))
