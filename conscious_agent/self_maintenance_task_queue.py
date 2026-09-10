from __future__ import annotations

"""Scoring and selection helpers for the supervised maintenance task queue."""

from typing import Any


def _score_maintenance_goal_components(text: str, selected: list[str]) -> dict[str, Any]:
    priority = 40
    risk = 20
    reasons: list[str] = []
    if any(token in text for token in ("safety", "privacy", "source-only", "package", "release")):
        priority += 25
        risk += 20
        reasons.append("release/privacy boundary")
    if any(token in text for token in ("dashboard", "api", "queue", "visibility")):
        priority += 18
        risk += 15
        reasons.append("operator surface")
    if any(token in text for token in ("performance", "slow", "cache", "render")):
        priority += 15
        risk += 10
        reasons.append("operator performance")
    if any(token in text for token in ("apply", "rollback", "approval", "destructive", "live")):
        priority += 5
        risk += 35
        reasons.append("mutation boundary")
    if "conscious_agent/self_maintenance.py" in selected:
        risk += 10
    if any(path.startswith("data/") for path in selected):
        risk += 30
        reasons.append("runtime data touch")
    priority = min(100, max(0, priority))
    risk = min(100, max(0, risk))
    risk_level = "high" if risk >= 70 else "medium" if risk >= 35 else "low"
    return {
        "priority_score": priority,
        "risk_score": risk,
        "risk_level": risk_level,
        "reasons": reasons or ["bounded maintenance goal"],
        "planned_files": selected,
    }


def _queue_sort_key(task: dict[str, Any]) -> tuple[int, int, str]:
    return (-int(task.get("priority_score") or 0), int(task.get("risk_score") or 0), str(task.get("task_id", "")))


def _select_next_maintenance_task(
    tasks: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    active = [
        task
        for task in tasks
        if str(task.get("state")) in {"selected", "cycle_running", "checkpoint_required", "apply_handoff_ready"}
    ]
    candidates = sorted(
        [task for task in tasks if str(task.get("state", "queued")) in {"queued", "blocked"}],
        key=_queue_sort_key,
    )
    return (None if active else (candidates[0] if candidates else None)), active, candidates
