from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from memory import store_memory
from paths import DATA_DIR
from task_queue import get_task, resolve_task_id, task_detail_text
from task_executor import execute_task_command, task_command_options_text
from task_result_evaluator import (
    apply_task_evaluation,
    evaluate_task_result,
    get_task_evaluation,
    list_task_evaluations,
    task_evaluation_text,
)

GUIDED_SESSIONS_DIR = DATA_DIR / "guided_sessions"
GUIDED_SESSIONS_README = GUIDED_SESSIONS_DIR / "README.md"

SAFE_APPLY_RECOMMENDATIONS = {"complete_task", "block_task", "already_done"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not cleaned:
        cleaned = "guided-session"
    return cleaned[:max_length].strip("-") or "guided-session"


def _new_session_id(task: dict[str, Any] | None, step: str) -> str:
    title = (task or {}).get("title") or (task or {}).get("id") or "task"
    return f"guided_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{step}_{_slug(title)}"


def _ensure_storage() -> None:
    GUIDED_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not GUIDED_SESSIONS_README.exists():
        GUIDED_SESSIONS_README.write_text(
            "Saved guided work sessions. These record task guidance, one-step advances, evaluations, and safe next commands.\n",
            encoding="utf-8",
        )


def _session_path(session_id: str) -> Path:
    _ensure_storage()
    return GUIDED_SESSIONS_DIR / f"{session_id.replace('_', '-')}.json"


def _save_session(session: dict[str, Any]) -> None:
    _ensure_storage()
    with _session_path(session["id"]).open("w", encoding="utf-8") as file:
        json.dump(session, file, indent=2)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_guided_sessions() -> list[dict[str, Any]]:
    _ensure_storage()
    sessions: list[dict[str, Any]] = []
    for path in GUIDED_SESSIONS_DIR.glob("*.json"):
        data = _load_json_file(path)
        if data:
            sessions.append(data)
    return sorted(sessions, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_guided_session_id(session_id: str) -> str:
    token = (session_id or "").strip()
    token_lower = token.lower()
    sessions = list_guided_sessions()

    if token_lower in {"latest", "last"}:
        return sessions[0].get("id", "") if sessions else ""

    if token_lower.startswith("latest-"):
        desired_step = token_lower.replace("latest-", "", 1)
        matches = [session for session in sessions if str(session.get("step", "")).lower() == desired_step]
        return matches[0].get("id", "") if matches else ""

    return token


def get_guided_session(session_id: str) -> dict[str, Any] | None:
    resolved = resolve_guided_session_id(session_id)
    if not resolved:
        return None
    for session in list_guided_sessions():
        if session.get("id") == resolved:
            return session
    return None


def _latest_execution(task: dict[str, Any]) -> dict[str, Any] | None:
    history = task.get("execution_history", []) or []
    if not history:
        return None
    return history[-1]


def _latest_evaluation_for_task(task_id: str) -> dict[str, Any] | None:
    evaluations = [item for item in list_task_evaluations() if item.get("task_id") == task_id]
    return evaluations[0] if evaluations else None


def _determine_next_step(task: dict[str, Any]) -> dict[str, Any]:
    task_id = task.get("id", "")
    status = task.get("status", "planned")
    latest_execution = _latest_execution(task)
    latest_evaluation = _latest_evaluation_for_task(task_id)

    if status in {"done", "cancelled"}:
        return {
            "step": "observe",
            "reason": f"Task is already {status}.",
            "next_command": f"python conscious_agent/main.py --show-task {task_id} --show-task-full",
        }

    if not latest_execution:
        return {
            "step": "dry-run",
            "reason": "Task has no command execution history yet. The next safe step is to dry-run its command.",
            "next_command": f"python conscious_agent/main.py --advance-work-session {task_id} --dry-run",
        }

    if latest_execution.get("dry_run") and latest_execution.get("ok"):
        return {
            "step": "execute",
            "reason": "Latest command check was a successful dry run. The next safe step is to run the command for real.",
            "next_command": f"python conscious_agent/main.py --advance-work-session {task_id}",
        }

    if latest_execution.get("dry_run") and not latest_execution.get("ok"):
        return {
            "step": "evaluate",
            "reason": "Latest dry run failed. The next safe step is to evaluate the task result before trying anything else.",
            "next_command": f"python conscious_agent/main.py --advance-work-session {task_id}",
        }

    if latest_evaluation and not latest_evaluation.get("applied"):
        recommendation = latest_evaluation.get("recommendation", "")
        if recommendation in SAFE_APPLY_RECOMMENDATIONS:
            return {
                "step": "apply-evaluation",
                "reason": f"Latest task evaluation recommends {recommendation}. It can be applied only with --apply-guided-evaluation.",
                "next_command": f"python conscious_agent/main.py --advance-work-session {task_id} --apply-guided-evaluation",
                "evaluation_id": latest_evaluation.get("id", ""),
            }
        return {
            "step": "manual-review",
            "reason": f"Latest task evaluation recommends {recommendation}, which is advisory and should be reviewed manually.",
            "next_command": f"python conscious_agent/main.py --show-task-evaluation {latest_evaluation.get('id')}",
            "evaluation_id": latest_evaluation.get("id", ""),
        }

    return {
        "step": "evaluate",
        "reason": "Latest real command has not been evaluated yet. The next safe step is task result evaluation.",
        "next_command": f"python conscious_agent/main.py --advance-work-session {task_id}",
    }


def _base_session(task: dict[str, Any], mode: str, step: str) -> dict[str, Any]:
    return {
        "id": _new_session_id(task, step),
        "type": "guided_work_session",
        "created_at": _now(),
        "mode": mode,
        "step": step,
        "task_id": task.get("id", ""),
        "task_title": task.get("title", ""),
        "task_status": task.get("status", ""),
        "task_priority": task.get("priority", ""),
        "result": {},
        "next_step": {},
    }


def create_guided_work_session(task_id: str = "latest-ready") -> dict[str, Any]:
    resolved_task_id = resolve_task_id(task_id)
    task = get_task(resolved_task_id) if resolved_task_id else None
    if not task:
        return {"ok": False, "error": f"Task not found: {task_id}", "id": ""}

    next_step = _determine_next_step(task)
    session = _base_session(task, mode="guide", step="overview")
    session["ok"] = True
    session["task"] = task
    session["command_options_text"] = task_command_options_text(task.get("id", ""))
    session["next_step"] = next_step
    session["useful_commands"] = [
        f"python conscious_agent/main.py --show-task {task.get('id')} --show-task-full",
        f"python conscious_agent/main.py --task-command-options {task.get('id')}",
        next_step.get("next_command", ""),
        f"python conscious_agent/main.py --show-guided-session {session['id']}",
    ]
    _save_session(session)

    store_memory({
        "type": "guided_work_session",
        "content": f"Created guided work session for task {task.get('id')}. Next step: {next_step.get('step')}.",
        "source": "guided_work_session",
        "task_id": task.get("id"),
        "guided_session_id": session["id"],
        "next_step": next_step.get("step"),
    })
    return session


def advance_guided_work_session(
    task_id: str = "latest-ready",
    command_index: int = 0,
    dry_run: bool = False,
    use_ai: bool = True,
    apply_guided_evaluation: bool = False,
) -> dict[str, Any]:
    resolved_task_id = resolve_task_id(task_id)
    task = get_task(resolved_task_id) if resolved_task_id else None
    if not task:
        return {"ok": False, "error": f"Task not found: {task_id}", "id": ""}

    next_step = _determine_next_step(task)
    step = next_step.get("step", "observe")
    session = _base_session(task, mode="advance", step=step)
    session["ok"] = True
    session["initial_next_step"] = next_step

    if step == "dry-run":
        result = execute_task_command(
            resolved_task_id,
            command_index=command_index,
            dry_run=True,
            complete_on_success=False,
        )
        session["result"] = {
            "action": "dry-run",
            "ok": result.ok,
            "command": result.command,
            "return_code": result.return_code,
            "error": result.error,
            "message": result.message,
        }
    elif step == "execute":
        result = execute_task_command(
            resolved_task_id,
            command_index=command_index,
            dry_run=dry_run,
            complete_on_success=False,
        )
        session["result"] = {
            "action": "execute-dry-run" if dry_run else "execute",
            "ok": result.ok,
            "command": result.command,
            "return_code": result.return_code,
            "error": result.error,
            "message": result.message,
        }
    elif step == "evaluate":
        evaluation = evaluate_task_result(resolved_task_id, use_ai=use_ai)
        session["result"] = {
            "action": "evaluate",
            "ok": evaluation.get("ok", False),
            "evaluation_id": evaluation.get("id", ""),
            "recommendation": evaluation.get("recommendation", ""),
            "reason": evaluation.get("reason", evaluation.get("error", "")),
            "next_command": evaluation.get("next_command", ""),
        }
    elif step == "apply-evaluation":
        evaluation_id = next_step.get("evaluation_id", "latest")
        if not apply_guided_evaluation:
            session["ok"] = False
            session["result"] = {
                "action": "apply-evaluation",
                "ok": False,
                "evaluation_id": evaluation_id,
                "error": "Safe evaluation exists, but it was not applied because --apply-guided-evaluation was not used.",
                "next_command": f"python conscious_agent/main.py --advance-work-session {resolved_task_id} --apply-guided-evaluation",
            }
        else:
            result = apply_task_evaluation(evaluation_id)
            session["result"] = {
                "action": "apply-evaluation",
                "ok": result.get("ok", False),
                "evaluation_id": evaluation_id,
                "message": result.get("message", ""),
                "error": result.get("error", ""),
            }
    else:
        session["result"] = {
            "action": step,
            "ok": False,
            "message": next_step.get("reason", "No automatic action is safe for this step."),
            "next_command": next_step.get("next_command", ""),
        }

    refreshed_task = get_task(resolved_task_id) or task
    session["final_task_status"] = refreshed_task.get("status", "")
    session["next_step"] = _determine_next_step(refreshed_task)
    session["useful_commands"] = [
        f"python conscious_agent/main.py --guided-work-session {resolved_task_id}",
        f"python conscious_agent/main.py --show-task {resolved_task_id} --show-task-full",
        session["next_step"].get("next_command", ""),
        f"python conscious_agent/main.py --show-guided-session {session['id']}",
    ]
    _save_session(session)

    store_memory({
        "type": "guided_work_session_advance",
        "content": f"Advanced guided work session for task {resolved_task_id}. Step: {step}. Result ok: {session.get('result', {}).get('ok')}.",
        "source": "guided_work_session",
        "task_id": resolved_task_id,
        "guided_session_id": session["id"],
        "step": step,
        "ok": session.get("result", {}).get("ok"),
    })
    return session


def guided_session_text(session: dict[str, Any], full: bool = False) -> str:
    if not session:
        return "Guided work session not found."

    lines = [
        f"# Guided Work Session: {session.get('id')}",
        f"Created: {session.get('created_at')}",
        f"Mode: {session.get('mode')}",
        f"Step: {session.get('step')}",
        f"Task: {session.get('task_id')} | {session.get('task_title')}",
        f"Task status: {session.get('final_task_status', session.get('task_status'))}",
    ]

    result = session.get("result", {}) or {}
    if result:
        lines.append("")
        lines.append("## Result")
        lines.append(f"Action: {result.get('action')}")
        lines.append(f"OK: {result.get('ok')}")
        if result.get("command"):
            lines.append(f"Command: {result.get('command')}")
        if result.get("return_code") is not None:
            lines.append(f"Return code: {result.get('return_code')}")
        if result.get("evaluation_id"):
            lines.append(f"Evaluation: {result.get('evaluation_id')}")
        if result.get("recommendation"):
            lines.append(f"Recommendation: {result.get('recommendation')}")
        if result.get("message"):
            lines.append(f"Message: {result.get('message')}")
        if result.get("error"):
            lines.append(f"Error: {result.get('error')}")

    next_step = session.get("next_step", {}) or {}
    if next_step:
        lines.append("")
        lines.append("## Next safe step")
        lines.append(f"Step: {next_step.get('step')}")
        lines.append(f"Reason: {next_step.get('reason')}")
        if next_step.get("next_command"):
            lines.append(f"Command: {next_step.get('next_command')}")

    useful = [command for command in session.get("useful_commands", []) if command]
    if useful:
        lines.append("")
        lines.append("## Useful commands")
        for command in useful:
            lines.append(command)

    if full and session.get("task"):
        lines.append("")
        lines.append("## Task detail")
        lines.append(task_detail_text(session["task"], full=True))

    if full and session.get("command_options_text"):
        lines.append("")
        lines.append("## Command options")
        lines.append(session["command_options_text"])

    return "\n".join(lines)


def print_guided_work_session(task_id: str = "latest-ready", full: bool = False) -> None:
    session = create_guided_work_session(task_id)
    if not session.get("ok"):
        print(f"Could not create guided work session: {session.get('error')}")
        return
    print(guided_session_text(session, full=full))


def print_advance_guided_work_session(
    task_id: str = "latest-ready",
    command_index: int = 0,
    dry_run: bool = False,
    use_ai: bool = True,
    apply_guided_evaluation: bool = False,
    full: bool = False,
) -> None:
    session = advance_guided_work_session(
        task_id=task_id,
        command_index=command_index,
        dry_run=dry_run,
        use_ai=use_ai,
        apply_guided_evaluation=apply_guided_evaluation,
    )
    if not session.get("ok") and not session.get("id"):
        print(f"Could not advance guided work session: {session.get('error')}")
        return
    print(guided_session_text(session, full=full))


def print_guided_sessions() -> None:
    sessions = list_guided_sessions()
    if not sessions:
        print("No guided work sessions found.")
        return
    for session in sessions[:25]:
        print(
            f"{session.get('id')} | {session.get('created_at')} | "
            f"step={session.get('step')} | mode={session.get('mode')} | task={session.get('task_id')}"
        )


def print_saved_guided_session(session_id: str = "latest", full: bool = False) -> None:
    session = get_guided_session(session_id)
    if not session:
        print(f"Guided work session not found: {session_id}")
        return
    print(guided_session_text(session, full=full))
