from __future__ import annotations

"""Pure attention-scheduler primitives extracted for v1253.4.

This module contains scoring/data-shaping only. It cannot mutate projects,
consume approvals, contact providers, or authorize maintenance execution.
"""

from typing import Any, Callable

CONTRACT_VERSION = "v1253.4"


def attention_budget_records(project_id: str = "eidolon") -> list[dict[str, Any]]:
    _ = project_id
    return [
        {"bucket": "maintenance", "budget_units": 45, "used_units": 0, "purpose": "self-maintenance queue cycles and verification"},
        {"bucket": "reflection", "budget_units": 20, "used_units": 0, "purpose": "self-model and continuity review"},
        {"bucket": "project_work", "budget_units": 25, "used_units": 0, "purpose": "user-requested project tasks"},
        {"bucket": "reserve", "budget_units": 10, "used_units": 0, "purpose": "interruptions, blockers, and recovery"},
    ]


def attention_score_task(
    task: dict[str, Any],
    now_iso: str,
    *,
    age_seconds: Callable[[str | None], int | None],
) -> dict[str, Any]:
    created_age = age_seconds(str(task.get("created_at") or now_iso)) or 0
    age_bonus = min(20, created_age // 86400)
    priority = int(task.get("priority_score") or 0)
    risk = int(task.get("risk_score") or 0)
    state = str(task.get("state") or "queued")
    blocked_penalty = 25 if state == "blocked" else 0
    attention_score = max(0, min(100, priority + age_bonus - (risk // 3) - blocked_penalty))
    reason_codes: list[str] = []
    if priority >= 75:
        reason_codes.append("priority.high")
    elif priority >= 50:
        reason_codes.append("priority.medium")
    else:
        reason_codes.append("priority.low")
    if risk >= 70:
        reason_codes.append("risk.high.operator_review_required")
    elif risk >= 40:
        reason_codes.append("risk.medium.supervised_only")
    else:
        reason_codes.append("risk.low")
    if age_bonus:
        reason_codes.append("freshness.aged_queue_item")
    else:
        reason_codes.append("freshness.current")
    if state in {"selected", "cycle_running", "checkpoint_required", "apply_handoff_ready"}:
        decision = "resume_active_task"
        reason = "task already owns the one-cycle-at-a-time slot"
        reason_codes.append("state.active_resume")
        next_safe_action = "Review the active cycle/checkpoint before any source-apply handoff."
    elif risk >= 70:
        decision = "defer_for_human_review"
        reason = "high-risk task cannot be auto-selected by attention scheduler"
        reason_codes.append("decision.deferred_human_review")
        next_safe_action = "Require operator review; do not run apply/publish/live actions from attention."
    elif state == "blocked":
        decision = "surface_blocker"
        reason = "blocked task needs operator action before execution"
        reason_codes.append("state.blocked_surface")
        next_safe_action = "Resolve the blocker or change task state through the guarded queue path."
    else:
        decision = "candidate_focus"
        reason = "priority/risk/age score makes it eligible for supervised focus"
        reason_codes.append("decision.candidate_focus")
        next_safe_action = "Run a supervised one-cycle queue check or inspect the task drill-down."
    return {
        "task_id": task.get("task_id"),
        "goal": task.get("goal"),
        "state": state,
        "priority_score": priority,
        "risk_score": risk,
        "age_seconds": created_age,
        "age_bonus": age_bonus,
        "attention_score": attention_score,
        "decision": decision,
        "reason": reason,
        "reason_codes": reason_codes,
        "explanation": {
            "priority": f"priority={priority} contributes directly to attention score",
            "risk": f"risk={risk} subtracts {risk // 3} and may force deferral at 70+",
            "freshness": f"age_bonus={age_bonus} rewards older unresolved queue items",
            "state": f"state={state} can force resume, blocker surfacing, or ordinary candidacy",
            "score_formula": "priority + min(age_days, 20) - risk//3 - blocked_penalty",
        },
        "next_safe_action": next_safe_action,
    }


__all__ = ["CONTRACT_VERSION", "attention_budget_records", "attention_score_task"]
