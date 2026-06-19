from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from goal_manager import list_goals
from local_brain import local_generate
from maintenance_advisor import list_maintenance_scans, maintenance_scan_text
from memory import load_memories, store_memory
from memory_compactor import list_memory_summaries
from patch_suggester import list_patch_proposals
from paths import DATA_DIR
from project_indexer import load_project_index
from project_manager import get_active_project
from self_improver import list_self_improvement_runs
from test_report_reviewer import list_test_reviews
from test_runner import list_test_reports
from task_queue import list_tasks


SESSION_PLANS_DIR = DATA_DIR / "session_plans"
ACTION_LOG_FILE = DATA_DIR / "action_log.json"
MAX_AI_CONTEXT_CHARS = 18_000
OPEN_GOAL_STATUSES = {"planned", "active", "blocked", "paused"}
PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class SessionPlanResult:
    ok: bool
    plan_id: str = ""
    recommendation_count: int = 0
    text: str = ""
    error: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_storage() -> None:
    SESSION_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    readme = SESSION_PLANS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Session Plans\n\n"
            "This folder stores read-only session plans. Session plans combine goals, project state, "
            "maintenance scans, memory summaries, patches, and test reports to recommend the next safe work step.\n",
            encoding="utf-8",
        )


def _new_plan_id() -> str:
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _plan_path(plan_id: str) -> Path:
    return SESSION_PLANS_DIR / f"{plan_id}.json"


def save_session_plan(plan: dict[str, Any]) -> None:
    _ensure_storage()
    with _plan_path(plan["id"]).open("w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)


def resolve_session_plan_id(plan_id: str) -> str:
    token = (plan_id or "").strip()
    if token.lower() not in {"latest", "last"}:
        return token

    plans = list_session_plans()
    if not plans:
        return ""
    return plans[0].get("id", "")


def load_session_plan(plan_id: str) -> dict[str, Any] | None:
    resolved_id = resolve_session_plan_id(plan_id)
    if not resolved_id:
        return None

    path = _plan_path(resolved_id)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def list_session_plans() -> list[dict[str, Any]]:
    _ensure_storage()
    plans: list[dict[str, Any]] = []

    for path in sorted(SESSION_PLANS_DIR.glob("session_*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            plans.append(data)

    return plans


def _load_action_log() -> list[dict[str, Any]]:
    if not ACTION_LOG_FILE.exists():
        return []
    try:
        with ACTION_LOG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED: exceeded {limit} characters]"


def _goal_sort_key(goal: dict[str, Any]) -> tuple[int, str, str]:
    priority = str(goal.get("priority", "medium")).lower()
    rank = PRIORITY_RANK.get(priority, 2)
    # newest updated first within same priority
    updated = str(goal.get("updated_at", goal.get("created_at", "")))
    return (rank, "" if goal.get("status") == "active" else "1", updated)


def _open_goals() -> list[dict[str, Any]]:
    goals = [goal for goal in list_goals(include_cancelled=False) if goal.get("status") in OPEN_GOAL_STATUSES]
    return sorted(goals, key=_goal_sort_key)


def _latest_by_time(items: list[dict[str, Any]], timestamp_key: str = "created_at") -> dict[str, Any] | None:
    if not items:
        return None
    return sorted(items, key=lambda item: item.get(timestamp_key, item.get("created_at", "")), reverse=True)[0]


def _recommendation(
    priority: str,
    category: str,
    title: str,
    rationale: str,
    command: str = "",
    follow_up_commands: list[str] | None = None,
    risk: str = "low",
    source: str = "heuristic",
    linked_goal: str = "",
) -> dict[str, Any]:
    return {
        "priority": priority,
        "category": category,
        "title": title,
        "rationale": rationale,
        "recommended_command": command,
        "follow_up_commands": follow_up_commands or [],
        "risk": risk,
        "source": source,
        "linked_goal": linked_goal,
    }


def _patch_recommendations(patches: list[dict[str, Any]], test_reports: list[dict[str, Any]], test_reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    proposed = [patch for patch in patches if patch.get("status") == "proposed"]
    applied = [patch for patch in patches if patch.get("status") == "applied"]

    if proposed:
        latest_proposed = proposed[0]
        recommendations.append(_recommendation(
            priority="high" if latest_proposed.get("risk_level") == "high" else "medium",
            category="patch_workflow",
            title="Review the latest proposed patch",
            rationale=(
                f"There are {len(proposed)} proposed patch(es) waiting for review. "
                "Review before applying anything. Yes, paperwork again. It keeps the goblin from chewing wires."
            ),
            command="python conscious_agent/main.py --show-patch latest-proposed",
            follow_up_commands=[
                "python conscious_agent/main.py --apply-patch latest-proposed --dry-run",
                "python conscious_agent/main.py --apply-patch latest-proposed",
                "python conscious_agent/main.py --run-test-workflow latest-applied --auto-review",
            ],
            risk=latest_proposed.get("risk_level", "medium"),
            linked_goal="Build Eidolon into a safe local AI assistant",
        ))

    reports_by_patch = {str(report.get("patch_id", "")): report for report in test_reports if report.get("patch_id")}
    reviews_by_report = {str(review.get("report_id", "")): review for review in test_reviews if review.get("report_id")}

    for patch in applied[:5]:
        patch_id = patch.get("id", "")
        report = reports_by_patch.get(patch_id)
        if not report:
            recommendations.append(_recommendation(
                priority="high",
                category="test_workflow",
                title="Run tests for the latest applied patch",
                rationale=f"Applied patch {patch_id} has no saved test report yet.",
                command=f"python conscious_agent/main.py --run-test-workflow {patch_id} --auto-review",
                follow_up_commands=["python conscious_agent/main.py --show-test-review latest"],
                risk="low",
            ))
            break

        if report.get("id") and report.get("id") not in reviews_by_report:
            recommendations.append(_recommendation(
                priority="medium",
                category="test_review",
                title="Auto-review the newest unreviewed test report",
                rationale=f"Test report {report.get('id')} exists for patch {patch_id}, but no review was found.",
                command=f"python conscious_agent/main.py --review-test-report {report.get('id')}",
                follow_up_commands=["python conscious_agent/main.py --show-test-review latest"],
                risk="low",
            ))
            break

    return recommendations


def _goal_recommendations(open_goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []

    blocked = [goal for goal in open_goals if goal.get("status") == "blocked"]
    critical_open = [goal for goal in open_goals if goal.get("priority") == "critical"]
    active = [goal for goal in open_goals if goal.get("status") == "active"]
    planned_high = [goal for goal in open_goals if goal.get("status") == "planned" and goal.get("priority") in {"critical", "high"}]

    if blocked:
        goal = blocked[0]
        blocker = (goal.get("blockers") or ["No blocker details recorded."])[0]
        recommendations.append(_recommendation(
            priority="high",
            category="goal_blocker",
            title=f"Resolve blocker for: {goal.get('title')}",
            rationale=f"Goal is blocked. Blocker: {blocker}",
            command=f"python conscious_agent/main.py --show-goal {goal.get('id')} --show-goal-full",
            follow_up_commands=[f"python conscious_agent/main.py --set-goal-status {goal.get('id')} active --goal-note \"Blocker resolved\""],
            risk="low",
            linked_goal=goal.get("id", ""),
        ))

    if active:
        goal = active[0]
        next_actions = goal.get("next_actions") or []
        next_action = next_actions[0] if next_actions else "Add a concrete next action for this goal."
        recommendations.append(_recommendation(
            priority="high" if goal.get("priority") in {"critical", "high"} else "medium",
            category="goal_next_action",
            title=f"Advance active goal: {goal.get('title')}",
            rationale=f"Next action: {next_action}",
            command=f"python conscious_agent/main.py --show-goal {goal.get('id')} --show-goal-full",
            follow_up_commands=[
                "python conscious_agent/main.py --maintenance-scan --no-ai-maintenance",
                "python conscious_agent/main.py --plan-session --no-ai-session",
            ],
            risk="low",
            linked_goal=goal.get("id", ""),
        ))

    if planned_high and not active:
        goal = planned_high[0]
        recommendations.append(_recommendation(
            priority="medium",
            category="goal_activation",
            title=f"Start high-priority planned goal: {goal.get('title')}",
            rationale="There are no active goals, but a high-priority planned goal is waiting.",
            command=f"python conscious_agent/main.py --set-goal-status {goal.get('id')} active --goal-note \"Started from session planner\"",
            follow_up_commands=[f"python conscious_agent/main.py --show-goal {goal.get('id')} --show-goal-full"],
            risk="low",
            linked_goal=goal.get("id", ""),
        ))

    if not open_goals:
        recommendations.append(_recommendation(
            priority="medium",
            category="goal_planning",
            title="Create a new structured goal",
            rationale="No open structured goals were found. Eidolon needs a target or it will philosophize into a corner again.",
            command="python conscious_agent/main.py --add-goal-structured \"Define the next Eidolon development goal\" --goal-priority high --goal-initial-status planned",
            risk="low",
        ))

    return recommendations


def _maintenance_recommendations(scans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not scans:
        return [_recommendation(
            priority="medium",
            category="maintenance",
            title="Run a maintenance scan",
            rationale="No saved maintenance scan exists yet. A scan gives the session planner better evidence.",
            command="python conscious_agent/main.py --maintenance-scan --no-ai-maintenance",
            follow_up_commands=["python conscious_agent/main.py --show-maintenance-scan latest --show-maintenance-full --hide-maintenance-ai"],
            risk="low",
        )]

    latest = scans[0]
    suggestions = latest.get("suggestions", []) or []
    high_priority = [item for item in suggestions if item.get("priority") in {"critical", "high"}]
    medium_priority = [item for item in suggestions if item.get("priority") == "medium"]

    if high_priority:
        item = high_priority[0]
        return [_recommendation(
            priority="high",
            category="maintenance",
            title=item.get("title", "Address high-priority maintenance suggestion"),
            rationale=item.get("evidence", "Latest maintenance scan found a high-priority suggestion."),
            command=item.get("recommended_command") or "python conscious_agent/main.py --show-maintenance-scan latest --show-maintenance-full --hide-maintenance-ai",
            follow_up_commands=["python conscious_agent/main.py --plan-session --no-ai-session"],
            risk="low",
            source="maintenance_scan",
        )]

    if medium_priority:
        item = medium_priority[0]
        return [_recommendation(
            priority="medium",
            category="maintenance",
            title=item.get("title", "Address maintenance suggestion"),
            rationale=item.get("evidence", "Latest maintenance scan found a medium-priority suggestion."),
            command=item.get("recommended_command") or "python conscious_agent/main.py --show-maintenance-scan latest --show-maintenance-full --hide-maintenance-ai",
            risk="low",
            source="maintenance_scan",
        )]

    return []


def _memory_recommendations(memories: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    total = len(memories)

    if total >= 120:
        recommendations.append(_recommendation(
            priority="medium",
            category="memory",
            title="Compact old memories",
            rationale=f"Active memories are at {total}. Compaction keeps memory useful instead of letting JSON become a landfill with timestamps.",
            command="python conscious_agent/main.py --compact-memory --dry-run",
            follow_up_commands=["python conscious_agent/main.py --compact-memory", "python conscious_agent/main.py --memory-status"],
            risk="low",
        ))
    elif not summaries and total >= 40:
        recommendations.append(_recommendation(
            priority="low",
            category="memory",
            title="Check memory status before it grows too much",
            rationale=f"There are {total} active memories and no saved summaries yet.",
            command="python conscious_agent/main.py --memory-status",
            risk="low",
        ))

    return recommendations


def _project_index_recommendations(index: dict[str, Any]) -> list[dict[str, Any]]:
    files = index.get("files", []) if isinstance(index, dict) else []
    if not index.get("indexed_at") or not files:
        return [_recommendation(
            priority="high",
            category="project_index",
            title="Build or refresh the project index",
            rationale="No usable project index was found. Code review and patch suggestions depend on this map more than anyone wants to admit.",
            command="python conscious_agent/main.py --index-project conscious_agent",
            follow_up_commands=["python conscious_agent/main.py --project-index-summary"],
            risk="low",
        )]

    parse_errors = []
    large_files = []
    for file in files:
        path = file.get("path", "")
        summary = file.get("summary", {}) or {}
        if file.get("extension") == ".py" and summary.get("parse_error"):
            parse_errors.append(path)
        line_count = summary.get("line_count") or 0
        if isinstance(line_count, int) and line_count > 500:
            large_files.append((path, line_count))

    recommendations: list[dict[str, Any]] = []
    if parse_errors:
        recommendations.append(_recommendation(
            priority="high",
            category="code_health",
            title="Review Python parse errors",
            rationale="Indexed Python files with parse errors: " + ", ".join(parse_errors[:5]),
            command=f"python conscious_agent/main.py --review-project-file {parse_errors[0]} --no-ai-review",
            risk="low",
        ))

    if large_files:
        path, count = sorted(large_files, key=lambda item: item[1], reverse=True)[0]
        recommendations.append(_recommendation(
            priority="low",
            category="code_health",
            title="Review unusually large file",
            rationale=f"{path} has {count} lines. Large files are where bugs rent apartments.",
            command=f"python conscious_agent/main.py --review-project-file {path} --no-ai-review",
            risk="low",
        ))

    return recommendations


def _latest_test_recommendation(test_reports: list[dict[str, Any]], test_reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not test_reports:
        return [_recommendation(
            priority="low",
            category="testing",
            title="Run the default test workflow",
            rationale="No saved test reports exist. A baseline report makes future patch safety easier to judge.",
            command="python conscious_agent/main.py --run-test-workflow --auto-review --no-ai-test-review",
            risk="low",
        )]

    latest_report = test_reports[0]
    if latest_report.get("recommendation") in {"rollback_or_review", "manual_review"}:
        return [_recommendation(
            priority="high",
            category="testing",
            title="Investigate latest failing test workflow",
            rationale=f"Latest test report recommendation is {latest_report.get('recommendation')}.",
            command="python conscious_agent/main.py --show-test-report latest --show-test-output",
            follow_up_commands=["python conscious_agent/main.py --review-test-report latest --no-ai-test-review"],
            risk="low",
        )]

    latest_review = test_reviews[0] if test_reviews else None
    if latest_review and latest_review.get("recommendation") in {"rollback_patch", "manual_review", "fix_test_workflow"}:
        return [_recommendation(
            priority="high",
            category="testing",
            title="Address latest test review recommendation",
            rationale=f"Latest test review recommends: {latest_review.get('recommendation')}.",
            command="python conscious_agent/main.py --show-test-review latest",
            risk="low",
        )]

    return []


def _task_queue_recommendations(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    open_tasks = [task for task in tasks if task.get("status") in {"planned", "active", "blocked", "paused"}]
    active = [task for task in open_tasks if task.get("status") == "active"]
    ready = [task for task in open_tasks if task.get("status") in {"planned", "active"}]
    blocked = [task for task in open_tasks if task.get("status") == "blocked"]

    if active:
        task = active[0]
        recommendations.append(_recommendation(
            priority=task.get("priority", "medium"),
            category="task_queue",
            title=f"Continue active task: {task.get('title')}",
            rationale="The task queue has an active item. Continue or complete it before creating more loose work, because humans apparently need queues to avoid becoming fog.",
            command=f"python conscious_agent/main.py --show-task {task.get('id')} --show-task-full",
            follow_up_commands=[f"python conscious_agent/main.py --complete-task {task.get('id')} --task-note \"Finished during session\""],
            risk=task.get("risk", "low"),
            linked_goal=task.get("linked_goal", ""),
        ))
        return recommendations

    if ready:
        task = ready[0]
        recommendations.append(_recommendation(
            priority=task.get("priority", "medium"),
            category="task_queue",
            title=f"Start queued task: {task.get('title')}",
            rationale="A ready task is already queued. Starting it is safer than inventing new work just to feel productive.",
            command=f"python conscious_agent/main.py --start-task {task.get('id')} --task-note \"Starting from session plan\"",
            follow_up_commands=[f"python conscious_agent/main.py --show-task {task.get('id')} --show-task-full"],
            risk=task.get("risk", "low"),
            linked_goal=task.get("linked_goal", ""),
        ))
        return recommendations

    if blocked:
        task = blocked[0]
        blocker = (task.get("blockers") or ["No blocker details recorded."])[0]
        recommendations.append(_recommendation(
            priority="medium",
            category="task_queue",
            title=f"Resolve blocked task: {task.get('title')}",
            rationale=f"A queued task is blocked. Blocker: {blocker}",
            command=f"python conscious_agent/main.py --show-task {task.get('id')} --show-task-full",
            risk="low",
            linked_goal=task.get("linked_goal", ""),
        ))

    return recommendations


def _rank_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        recommendations,
        key=lambda item: (
            PRIORITY_RANK.get(str(item.get("priority", "medium")).lower(), 2),
            str(item.get("category", "")),
        ),
    )


def _build_context() -> dict[str, Any]:
    active_project = get_active_project() or {}
    project_index = load_project_index()
    goals = _open_goals()
    patches = list_patch_proposals()
    maintenance_scans = list_maintenance_scans()
    memory_summaries = list_memory_summaries()
    test_reports = list_test_reports()
    test_reviews = list_test_reviews()
    self_improvement_runs = list_self_improvement_runs()
    tasks = list_tasks(include_cancelled=False)
    memories = load_memories(limit=60)
    action_log = _load_action_log()

    return {
        "active_project": active_project,
        "project_index": project_index,
        "open_goals": goals,
        "patches": patches,
        "maintenance_scans": maintenance_scans,
        "memory_summaries": memory_summaries,
        "test_reports": test_reports,
        "test_reviews": test_reviews,
        "self_improvement_runs": self_improvement_runs,
        "tasks": tasks,
        "recent_memories": memories,
        "action_log": action_log,
    }


def _context_counts(context: dict[str, Any]) -> dict[str, Any]:
    patches = context["patches"]
    return {
        "open_goals": len(context["open_goals"]),
        "project_index_files": len(context["project_index"].get("files", []) if isinstance(context["project_index"], dict) else []),
        "maintenance_scans": len(context["maintenance_scans"]),
        "memory_summaries": len(context["memory_summaries"]),
        "active_memories_sampled": len(context["recent_memories"]),
        "patches_total": len(patches),
        "patches_proposed": len([patch for patch in patches if patch.get("status") == "proposed"]),
        "patches_applied": len([patch for patch in patches if patch.get("status") == "applied"]),
        "test_reports": len(context["test_reports"]),
        "test_reviews": len(context["test_reviews"]),
        "self_improvements": len(context["self_improvement_runs"]),
        "tasks_total": len(context.get("tasks", [])),
        "tasks_open": len([task for task in context.get("tasks", []) if task.get("status") in {"planned", "active", "blocked", "paused"}]),
        "tasks_active": len([task for task in context.get("tasks", []) if task.get("status") == "active"]),
        "action_log_entries": len(context["action_log"]),
    }


def _heuristic_session_summary(context: dict[str, Any], recommendations: list[dict[str, Any]]) -> str:
    project = context["active_project"] or {}
    counts = _context_counts(context)
    primary = recommendations[0] if recommendations else None

    lines = [
        f"Active project: {project.get('name', '[none]')}",
        f"Open goals: {counts['open_goals']}",
        f"Indexed files: {counts['project_index_files']}",
        f"Proposed patches: {counts['patches_proposed']}",
        f"Applied patches: {counts['patches_applied']}",
        f"Test reports/reviews: {counts['test_reports']}/{counts['test_reviews']}",
        f"Maintenance scans: {counts['maintenance_scans']}",
        f"Open tasks: {counts.get('tasks_open', 0)}",
    ]

    if primary:
        lines.extend([
            "",
            f"Recommended next task: {primary.get('title')}",
            f"Why: {primary.get('rationale')}",
        ])
    else:
        lines.extend([
            "",
            "Recommended next task: Continue normal development; no urgent planner action was found.",
        ])

    return "\n".join(lines)


def _ai_session_summary(plan_context: dict[str, Any]) -> str:
    safe_context = {
        "active_project": plan_context.get("active_project"),
        "context_counts": plan_context.get("context_counts"),
        "open_goals": [
            {
                "id": goal.get("id"),
                "title": goal.get("title"),
                "status": goal.get("status"),
                "priority": goal.get("priority"),
                "next_actions": (goal.get("next_actions") or [])[:3],
                "blockers": (goal.get("blockers") or [])[:3],
            }
            for goal in plan_context.get("open_goals", [])[:8]
        ],
        "open_tasks": plan_context.get("open_tasks", [])[:8],
        "latest_maintenance_scan": plan_context.get("latest_maintenance_scan"),
        "latest_test_report": plan_context.get("latest_test_report"),
        "latest_test_review": plan_context.get("latest_test_review"),
        "recommendations": plan_context.get("recommendations", [])[:8],
    }

    prompt = f"""
You are Eidolon, a local AI assistant planning the next safe development session.

You are not applying changes. You are only summarizing the next best task.

SESSION CONTEXT JSON:
{_clip(json.dumps(safe_context, indent=2), MAX_AI_CONTEXT_CHARS)}

Write a concise session brief for Marcus.
Include:
1. the best next task
2. why it matters
3. the exact first command to run, if any
4. what not to do yet

Keep it under 220 words. Do not sign off like an email.
"""

    return local_generate(prompt, temperature=0.35, max_tokens=320)


def create_session_plan(use_ai: bool = True) -> SessionPlanResult:
    context = _build_context()
    recommendations: list[dict[str, Any]] = []

    recommendations.extend(_task_queue_recommendations(context.get("tasks", [])))
    recommendations.extend(_project_index_recommendations(context["project_index"]))
    recommendations.extend(_patch_recommendations(context["patches"], context["test_reports"], context["test_reviews"]))
    recommendations.extend(_latest_test_recommendation(context["test_reports"], context["test_reviews"]))
    recommendations.extend(_goal_recommendations(context["open_goals"]))
    recommendations.extend(_maintenance_recommendations(context["maintenance_scans"]))
    recommendations.extend(_memory_recommendations(context["recent_memories"], context["memory_summaries"]))

    recommendations = _rank_recommendations(recommendations)

    latest_maintenance = context["maintenance_scans"][0] if context["maintenance_scans"] else None
    latest_report = context["test_reports"][0] if context["test_reports"] else None
    latest_review = context["test_reviews"][0] if context["test_reviews"] else None
    latest_summary = context["memory_summaries"][0] if context["memory_summaries"] else None

    plan_context = {
        "active_project": context["active_project"],
        "context_counts": _context_counts(context),
        "open_goals": context["open_goals"][:12],
        "open_tasks": [task for task in context.get("tasks", []) if task.get("status") in {"planned", "active", "blocked", "paused"}][:12],
        "latest_maintenance_scan": {
            "id": latest_maintenance.get("id"),
            "suggestion_count": len(latest_maintenance.get("suggestions", []) or []),
            "created_at": latest_maintenance.get("created_at"),
        } if latest_maintenance else None,
        "latest_test_report": {
            "id": latest_report.get("id"),
            "patch_id": latest_report.get("patch_id"),
            "recommendation": latest_report.get("recommendation"),
            "status": latest_report.get("status"),
            "created_at": latest_report.get("created_at"),
        } if latest_report else None,
        "latest_test_review": {
            "id": latest_review.get("id"),
            "report_id": latest_review.get("report_id"),
            "recommendation": latest_review.get("recommendation"),
            "created_at": latest_review.get("created_at"),
        } if latest_review else None,
        "latest_memory_summary": {
            "id": latest_summary.get("id"),
            "created_at": latest_summary.get("created_at"),
            "compacted_count": latest_summary.get("compacted_count"),
        } if latest_summary else None,
        "recommendations": recommendations,
    }

    ai_summary = ""
    if use_ai:
        ai_summary = _ai_session_summary(plan_context)

    plan = {
        "id": _new_plan_id(),
        "created_at": _now(),
        "type": "session_plan",
        "active_project": context["active_project"],
        "context_counts": plan_context["context_counts"],
        "open_goals": plan_context["open_goals"],
        "open_tasks": plan_context["open_tasks"],
        "primary_recommendation": recommendations[0] if recommendations else None,
        "recommendations": recommendations,
        "heuristic_summary": _heuristic_session_summary(context, recommendations),
        "ai_summary": ai_summary,
        "latest_maintenance_scan_id": latest_maintenance.get("id") if latest_maintenance else "",
        "latest_test_report_id": latest_report.get("id") if latest_report else "",
        "latest_test_review_id": latest_review.get("id") if latest_review else "",
        "latest_memory_summary_id": latest_summary.get("id") if latest_summary else "",
    }

    save_session_plan(plan)

    store_memory({
        "type": "session_plan_event",
        "content": f"Created session plan {plan['id']} with {len(recommendations)} recommendation(s). Primary: {(plan.get('primary_recommendation') or {}).get('title', '[none]')}",
        "source": "session_planner",
        "plan_id": plan["id"],
        "recommendation_count": len(recommendations),
    })

    return SessionPlanResult(
        ok=True,
        plan_id=plan["id"],
        recommendation_count=len(recommendations),
        text=session_plan_text(plan),
    )


def session_plan_text(plan: dict[str, Any], include_ai: bool = True, full: bool = False) -> str:
    lines: list[str] = []
    lines.append(f"# Session Plan: {plan.get('id')}")
    lines.append(f"Created: {plan.get('created_at')}")
    active_project = plan.get("active_project") or {}
    lines.append(f"Active project: {active_project.get('name', '[none]')}")
    lines.append("")

    lines.append("## Summary")
    lines.append(plan.get("heuristic_summary", "No summary available."))
    lines.append("")

    if include_ai and plan.get("ai_summary"):
        lines.append("## Local AI Brief")
        lines.append(plan.get("ai_summary", ""))
        lines.append("")

    primary = plan.get("primary_recommendation")
    if primary:
        lines.append("## Primary Recommendation")
        lines.append(f"Priority: {primary.get('priority')}")
        lines.append(f"Category: {primary.get('category')}")
        lines.append(f"Task: {primary.get('title')}")
        lines.append(f"Why: {primary.get('rationale')}")
        if primary.get("recommended_command"):
            lines.append(f"First command: {primary.get('recommended_command')}")
        if primary.get("follow_up_commands"):
            lines.append("Follow-up commands:")
            for command in primary.get("follow_up_commands", []):
                lines.append(f"- {command}")
        lines.append("")

    recommendations = plan.get("recommendations", []) or []
    lines.append(f"## Recommendations ({len(recommendations)})")
    if not recommendations:
        lines.append("No recommendations were generated.")
    else:
        shown = recommendations if full else recommendations[:8]
        for index, recommendation in enumerate(shown, start=1):
            lines.append(f"{index}. [{recommendation.get('priority')}] {recommendation.get('title')}")
            lines.append(f"   Category: {recommendation.get('category')}")
            lines.append(f"   Why: {recommendation.get('rationale')}")
            if recommendation.get("recommended_command"):
                lines.append(f"   Command: {recommendation.get('recommended_command')}")
            if full and recommendation.get("follow_up_commands"):
                lines.append("   Follow-up:")
                for command in recommendation.get("follow_up_commands", []):
                    lines.append(f"   - {command}")
        if not full and len(recommendations) > len(shown):
            lines.append(f"... {len(recommendations) - len(shown)} more recommendation(s). Use --show-session-plan-full.")
    lines.append("")

    if full:
        lines.append("## Context Counts")
        for key, value in (plan.get("context_counts") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.append("")

        lines.append("## Open Goals")
        open_goals = plan.get("open_goals", []) or []
        if not open_goals:
            lines.append("No open goals found.")
        for goal in open_goals[:12]:
            lines.append(f"- {goal.get('id')} | {goal.get('priority')} | {goal.get('status')} | {goal.get('title')}")
            for action in (goal.get("next_actions") or [])[:3]:
                lines.append(f"  next: {action}")
        lines.append("")

        lines.append("## Open Tasks")
        open_tasks = plan.get("open_tasks", []) or []
        if not open_tasks:
            lines.append("No open tasks found.")
        for task in open_tasks[:12]:
            lines.append(f"- {task.get('id')} | {task.get('priority')} | {task.get('status')} | {task.get('title')}")
            if task.get("command"):
                lines.append(f"  command: {task.get('command')}")

    return "\n".join(lines)


def print_session_plan(use_ai: bool = True) -> None:
    result = create_session_plan(use_ai=use_ai)
    if not result.ok:
        print(f"Could not create session plan: {result.error}")
        return

    print(result.text)
    print()
    print("No-copy commands:")
    print("  python conscious_agent/main.py --show-session-plan latest")
    print("  python conscious_agent/main.py --show-session-plan latest --show-session-plan-full")
    print("  python conscious_agent/main.py --plan-session --no-ai-session")


def print_session_plans() -> None:
    plans = list_session_plans()
    if not plans:
        print("No session plans found.")
        return

    for plan in plans:
        primary = plan.get("primary_recommendation") or {}
        print(
            f"{plan.get('id')} | {plan.get('created_at')} | "
            f"recommendations={len(plan.get('recommendations', []) or [])} | "
            f"primary={primary.get('title', '[none]')}"
        )


def print_saved_session_plan(plan_id: str, include_ai: bool = True, full: bool = False) -> None:
    plan = load_session_plan(plan_id)
    if not plan:
        print(f"Session plan not found: {plan_id}")
        return
    print(session_plan_text(plan, include_ai=include_ai, full=full))
