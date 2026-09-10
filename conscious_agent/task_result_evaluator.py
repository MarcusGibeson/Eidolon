from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from local_brain import local_generate
from memory import store_memory
from paths import DATA_DIR
from task_queue import (
    add_task,
    get_task,
    load_tasks_data,
    save_tasks_data,
    resolve_task_id,
    set_task_status,
    task_detail_text,
)

TASK_EVALUATIONS_DIR = DATA_DIR / "task_evaluations"
TASK_EVALUATIONS_README = TASK_EVALUATIONS_DIR / "README.md"

RECOMMENDATIONS = {
    "complete_task",
    "run_task_command",
    "execute_after_dry_run",
    "retry_command",
    "block_task",
    "manual_review",
    "create_follow_up_task",
    "already_done",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    if not cleaned:
        cleaned = "task-evaluation"
    return cleaned[:max_length].strip("-") or "task-evaluation"


def _new_evaluation_id(task: dict[str, Any]) -> str:
    title = task.get("title") or task.get("id") or "task"
    return f"taskeval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(title)}"


def _ensure_storage() -> None:
    TASK_EVALUATIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not TASK_EVALUATIONS_README.exists():
        TASK_EVALUATIONS_README.write_text(
            "Saved task execution evaluations. These summarize task command results and recommend the next safe task action.\n",
            encoding="utf-8",
        )


def _evaluation_path(evaluation_id: str) -> Path:
    _ensure_storage()
    safe_id = _slug(evaluation_id, max_length=96)
    if not safe_id.startswith("taskeval-") and not safe_id.startswith("taskeval_"):
        # File names are slugged, but ids may include underscores. Keep this permissive.
        safe_id = evaluation_id.replace("_", "-")
    return TASK_EVALUATIONS_DIR / f"{safe_id}.json"


def _save_evaluation(evaluation: dict[str, Any]) -> None:
    _ensure_storage()
    # Preserve original id in JSON, use a filesystem-safe filename.
    path = TASK_EVALUATIONS_DIR / f"{evaluation['id'].replace('_', '-')}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(evaluation, file, indent=2)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_task_evaluations() -> list[dict[str, Any]]:
    _ensure_storage()
    evaluations: list[dict[str, Any]] = []
    for path in TASK_EVALUATIONS_DIR.glob("*.json"):
        data = _load_json_file(path)
        if data:
            evaluations.append(data)
    return sorted(evaluations, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_task_evaluation_id(evaluation_id: str) -> str:
    token = (evaluation_id or "").strip()
    token_lower = token.lower()
    evaluations = list_task_evaluations()

    if token_lower in {"latest", "last"}:
        return evaluations[0].get("id", "") if evaluations else ""

    if token_lower in {"latest-complete", "latest-complete-task"}:
        matches = [item for item in evaluations if item.get("recommendation") == "complete_task"]
        return matches[0].get("id", "") if matches else ""

    if token_lower in {"latest-block", "latest-block-task"}:
        matches = [item for item in evaluations if item.get("recommendation") == "block_task"]
        return matches[0].get("id", "") if matches else ""

    if token_lower in {"latest-retry", "latest-retry-command"}:
        matches = [item for item in evaluations if item.get("recommendation") == "retry_command"]
        return matches[0].get("id", "") if matches else ""

    return token


def get_task_evaluation(evaluation_id: str) -> dict[str, Any] | None:
    resolved = resolve_task_evaluation_id(evaluation_id)
    if not resolved:
        return None
    for evaluation in list_task_evaluations():
        if evaluation.get("id") == resolved:
            return evaluation
    return None


def _latest_execution(task: dict[str, Any]) -> dict[str, Any] | None:
    history = task.get("execution_history", []) or []
    if not history:
        return None
    return history[-1]


def _recent_failures(task: dict[str, Any]) -> int:
    count = 0
    for entry in reversed(task.get("execution_history", []) or []):
        if entry.get("dry_run"):
            continue
        if entry.get("ok"):
            break
        count += 1
    return count


def _derive_recommendation(task: dict[str, Any]) -> dict[str, Any]:
    status = task.get("status", "planned")
    latest = _latest_execution(task)
    command = str(task.get("command", "")).strip()

    if status == "done":
        return {
            "recommendation": "already_done",
            "confidence": 0.95,
            "reason": "Task is already marked done.",
            "next_command": f"python conscious_agent/main.py --show-task {task.get('id')} --show-task-full",
        }

    if not latest:
        if command:
            return {
                "recommendation": "run_task_command",
                "confidence": 0.85,
                "reason": "Task has a command but no execution history yet.",
                "next_command": f"python conscious_agent/main.py --execute-task {task.get('id')} --dry-run",
            }
        return {
            "recommendation": "manual_review",
            "confidence": 0.75,
            "reason": "Task has no command and no execution history, so it needs manual review or a command added.",
            "next_command": f"python conscious_agent/main.py --show-task {task.get('id')} --show-task-full",
        }

    if latest.get("dry_run") and latest.get("ok"):
        return {
            "recommendation": "execute_after_dry_run",
            "confidence": 0.85,
            "reason": "Latest execution was a successful dry run, so the next safe step is to run the command for real.",
            "next_command": f"python conscious_agent/main.py --execute-task {task.get('id')}",
        }

    if latest.get("dry_run") and not latest.get("ok"):
        return {
            "recommendation": "block_task",
            "confidence": 0.8,
            "reason": "Latest dry run failed validation, usually because the command is not approved or is malformed.",
            "next_command": f"python conscious_agent/main.py --block-task {task.get('id')} \"Dry-run command validation failed\"",
        }

    if latest.get("ok") and latest.get("return_code") == 0:
        return {
            "recommendation": "complete_task",
            "confidence": 0.88,
            "reason": "Latest real command succeeded with return code 0.",
            "next_command": f"python conscious_agent/main.py --complete-task {task.get('id')} --task-note \"Task evaluation recommended completion after successful command\"",
        }

    failures = _recent_failures(task)
    if failures >= 2:
        return {
            "recommendation": "block_task",
            "confidence": 0.82,
            "reason": f"There are {failures} recent failed real command attempts. Blocking prevents repeated thrashing.",
            "next_command": f"python conscious_agent/main.py --block-task {task.get('id')} \"Repeated command failures; needs review\"",
        }

    return {
        "recommendation": "retry_command",
        "confidence": 0.65,
        "reason": "Latest real command failed, but this does not yet look like repeated failure.",
        "next_command": f"python conscious_agent/main.py --execute-task {task.get('id')} --dry-run",
    }


def _execution_summary(task: dict[str, Any]) -> dict[str, Any]:
    history = task.get("execution_history", []) or []
    latest = history[-1] if history else None
    real_runs = [entry for entry in history if not entry.get("dry_run")]
    dry_runs = [entry for entry in history if entry.get("dry_run")]
    successful = [entry for entry in real_runs if entry.get("ok") and entry.get("return_code") == 0]
    failed = [entry for entry in real_runs if not entry.get("ok")]

    return {
        "history_count": len(history),
        "dry_run_count": len(dry_runs),
        "real_run_count": len(real_runs),
        "successful_real_run_count": len(successful),
        "failed_real_run_count": len(failed),
        "latest": latest,
    }


def _ai_task_evaluation(task: dict[str, Any], evaluation: dict[str, Any]) -> str:
    prompt = f"""
You are reviewing the result of a supervised task execution for Eidolon, a local autonomous AI assistant prototype.

Task:
{task_detail_text(task, full=True)}

Heuristic evaluation:
{json.dumps(evaluation, indent=2)}

Write a concise review for Marcus.
Include:
- what happened
- why the recommendation makes sense
- any risk or uncertainty
- the next safest command

Do not claim the system is conscious. Do not tell Marcus to blindly trust the result.
Keep it under 220 words.
""".strip()

    return local_generate(prompt, temperature=0.25, max_tokens=350)


def evaluate_task_result(task_id: str = "latest", use_ai: bool = True) -> dict[str, Any]:
    task = get_task(task_id)
    if not task:
        return {
            "ok": False,
            "error": f"Task not found: {task_id}",
            "id": "",
            "task_id": task_id,
        }

    derived = _derive_recommendation(task)
    summary = _execution_summary(task)
    evaluation = {
        "ok": True,
        "id": _new_evaluation_id(task),
        "type": "task_result_evaluation",
        "task_id": task.get("id"),
        "task_title": task.get("title"),
        "task_status": task.get("status"),
        "created_at": _now(),
        "recommendation": derived["recommendation"],
        "confidence": derived["confidence"],
        "reason": derived["reason"],
        "next_command": derived["next_command"],
        "execution_summary": summary,
        "ai_review": "",
        "applied": False,
        "applied_at": "",
    }

    if use_ai:
        try:
            evaluation["ai_review"] = _ai_task_evaluation(task, evaluation)
        except Exception as error:
            evaluation["ai_review"] = f"AI task evaluation failed: {error}"

    _save_evaluation(evaluation)

    store_memory({
        "type": "task_result_evaluation",
        "content": f"Evaluated task {task.get('id')} and recommended {evaluation['recommendation']}: {evaluation['reason']}",
        "source": "task_result_evaluator",
        "task_id": task.get("id"),
        "evaluation_id": evaluation["id"],
        "recommendation": evaluation["recommendation"],
    })

    return evaluation


def apply_task_evaluation(evaluation_id: str = "latest", create_follow_up: bool = False) -> dict[str, Any]:
    evaluation = get_task_evaluation(evaluation_id)
    if not evaluation:
        return {"ok": False, "error": f"Task evaluation not found: {evaluation_id}"}

    task_id = evaluation.get("task_id", "")
    task = get_task(task_id)
    if not task:
        return {"ok": False, "error": f"Task not found for evaluation: {task_id}"}

    recommendation = evaluation.get("recommendation", "")
    note = f"Task result evaluation {evaluation.get('id')} applied: {evaluation.get('reason')}"

    if recommendation == "complete_task":
        result = set_task_status(task_id, "done", note=note)
    elif recommendation == "block_task":
        result = set_task_status(task_id, "blocked", blocker=evaluation.get("reason", "Blocked by task evaluation."), note=note)
    elif recommendation == "already_done":
        result = set_task_status(task_id, "done", note=note)
    elif recommendation == "create_follow_up_task" or create_follow_up:
        follow_up = add_task(
            title=f"Follow up: {task.get('title')}",
            description=f"Created from task evaluation {evaluation.get('id')}: {evaluation.get('reason')}",
            priority=task.get("priority", "medium"),
            status="planned",
            project=task.get("project", ""),
            command=evaluation.get("next_command", ""),
            source="task_evaluation",
            source_id=evaluation.get("id", ""),
            source_category="follow_up",
        )
        return {
            "ok": follow_up.ok,
            "message": follow_up.message,
            "error": follow_up.error,
            "evaluation_id": evaluation.get("id"),
            "created_task_id": follow_up.task.get("id") if follow_up.task else "",
        }
    else:
        return {
            "ok": False,
            "error": f"Recommendation '{recommendation}' is advisory only. Run the suggested next command manually: {evaluation.get('next_command')}",
        }

    if not result.ok:
        return {"ok": False, "error": result.error, "evaluation_id": evaluation.get("id")}

    evaluation["applied"] = True
    evaluation["applied_at"] = _now()
    _save_evaluation(evaluation)

    store_memory({
        "type": "task_evaluation_apply_event",
        "content": f"Applied task evaluation {evaluation.get('id')} to task {task_id}; recommendation was {recommendation}.",
        "source": "task_result_evaluator",
        "task_id": task_id,
        "evaluation_id": evaluation.get("id"),
        "recommendation": recommendation,
    })

    return {
        "ok": True,
        "message": f"Applied recommendation: {recommendation}",
        "evaluation_id": evaluation.get("id"),
        "task_id": task_id,
    }


def task_evaluation_text(evaluation: dict[str, Any], include_ai: bool = True) -> str:
    lines = [
        f"# Task Evaluation: {evaluation.get('id')}",
        f"Task: {evaluation.get('task_id')} | {evaluation.get('task_title')}",
        f"Created: {evaluation.get('created_at')}",
        f"Task status: {evaluation.get('task_status')}",
        f"Recommendation: {evaluation.get('recommendation')}",
        f"Confidence: {evaluation.get('confidence')}",
        f"Reason: {evaluation.get('reason')}",
        f"Next command: {evaluation.get('next_command')}",
        f"Applied: {evaluation.get('applied', False)}",
    ]

    summary = evaluation.get("execution_summary", {}) or {}
    lines.append("")
    lines.append("## Execution summary")
    lines.append(f"History entries: {summary.get('history_count', 0)}")
    lines.append(f"Dry runs: {summary.get('dry_run_count', 0)}")
    lines.append(f"Real runs: {summary.get('real_run_count', 0)}")
    lines.append(f"Successful real runs: {summary.get('successful_real_run_count', 0)}")
    lines.append(f"Failed real runs: {summary.get('failed_real_run_count', 0)}")

    latest = summary.get("latest")
    if latest:
        lines.append("")
        lines.append("## Latest execution")
        lines.append(f"When: {latest.get('executed_at')}")
        lines.append(f"Command: {latest.get('command')}")
        lines.append(f"Dry run: {latest.get('dry_run')}")
        lines.append(f"OK: {latest.get('ok')}")
        lines.append(f"Return code: {latest.get('return_code')}")
        if latest.get("error"):
            lines.append(f"Error: {latest.get('error')}")

    if include_ai and evaluation.get("ai_review"):
        lines.append("")
        lines.append("## AI review")
        lines.append(str(evaluation.get("ai_review")))

    lines.append("")
    lines.append("## Useful commands")
    lines.append(f"python conscious_agent/main.py --show-task {evaluation.get('task_id')} --show-task-full")
    lines.append(f"python conscious_agent/main.py --apply-task-evaluation {evaluation.get('id')}")
    lines.append(str(evaluation.get("next_command")))

    return "\n".join(lines)


def print_task_evaluation(task_id: str = "latest", use_ai: bool = True) -> None:
    evaluation = evaluate_task_result(task_id, use_ai=use_ai)
    if not evaluation.get("ok"):
        print(f"Could not evaluate task: {evaluation.get('error')}")
        return

    print(task_evaluation_text(evaluation, include_ai=True))


def print_task_evaluations() -> None:
    evaluations = list_task_evaluations()
    if not evaluations:
        print("No task evaluations found.")
        return

    for evaluation in evaluations:
        print(
            f"{evaluation.get('id')} | "
            f"recommendation={evaluation.get('recommendation')} | "
            f"confidence={evaluation.get('confidence')} | "
            f"task={evaluation.get('task_id')} | "
            f"created={evaluation.get('created_at')}"
        )


def print_saved_task_evaluation(evaluation_id: str = "latest", include_ai: bool = True) -> None:
    evaluation = get_task_evaluation(evaluation_id)
    if not evaluation:
        print(f"Task evaluation not found: {evaluation_id}")
        return
    print(task_evaluation_text(evaluation, include_ai=include_ai))


def print_apply_task_evaluation(evaluation_id: str = "latest", create_follow_up: bool = False) -> None:
    evaluation = get_task_evaluation(evaluation_id)
    if evaluation:
        print(task_evaluation_text(evaluation, include_ai=False))
        print()

    result = apply_task_evaluation(evaluation_id, create_follow_up=create_follow_up)
    if not result.get("ok"):
        print("Task evaluation was not applied.")
        print(f"Reason: {result.get('error')}")
        return

    print(result.get("message"))
    if result.get("task_id"):
        print(f"Task: {result.get('task_id')}")
    if result.get("created_task_id"):
        print(f"Created follow-up task: {result.get('created_task_id')}")
