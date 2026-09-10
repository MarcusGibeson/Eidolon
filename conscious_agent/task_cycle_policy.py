from __future__ import annotations

"""Lifecycle-aware task cycle decision policy.

v5.9 note:
    work_cycle.py uses this module to choose the next supervised cycle action
    from task lifecycle state instead of blindly asking the compatibility
    work_queue adapter for the next pending task. This module is deliberately
    policy-only: it explains which action should happen next and delegates the
    actual execution/mutation to existing task, approval, patch, and recovery
    modules.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from task_approval_bridge import request_task_work_approval
from task_lifecycle import derive_task_lifecycle, list_task_lifecycles
from task_patch_bridge import create_patch_followup_tasks
from task_queue import get_task
from task_recovery import build_task_recovery, mark_task_ready_for_retry, retry_task_work
from task_work_executor import execute_task_work_item

ACTION_NO_TASK = "no_task"
ACTION_REQUEST_APPROVAL = "request_approval"
ACTION_WAIT_APPROVAL = "wait_for_approval"
ACTION_EXECUTE_TASK = "execute_task"
ACTION_EXECUTE_APPROVED_TASK = "execute_approved_task"
ACTION_CREATE_PATCH_FOLLOWUPS = "create_patch_followups"
ACTION_REVIEW_RECOVERY = "review_recovery"
ACTION_WAIT_BLOCKER = "wait_for_blocker"
ACTION_WAIT_REJECTION = "wait_for_approval_revision"
ACTION_WAIT_FAILURE = "wait_for_approval_failure_review"
ACTION_MANUAL_REVIEW = "manual_review"

# The cycle now favors tasks that need supervision/triage before ordinary ready
# work, then executes safe ready work. Yes, actual prioritization in software,
# humanity finally crawls from the swamp.
STAGE_POLICY_ORDER = {
    "approval_required": 0,
    "recovery_needed": 1,
    "approval_rejected": 2,
    "approval_failed": 3,
    "patch_proposed": 4,
    "approved_ready": 5,
    "ready": 6,
    "active": 7,
    "approval_pending": 8,
    "blocked": 9,
    "unknown": 99,
}

PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

STAGE_ACTIONS = {
    "approval_required": ACTION_REQUEST_APPROVAL,
    "approval_pending": ACTION_WAIT_APPROVAL,
    "approved_ready": ACTION_EXECUTE_APPROVED_TASK,
    "ready": ACTION_EXECUTE_TASK,
    "active": ACTION_EXECUTE_TASK,
    "patch_proposed": ACTION_CREATE_PATCH_FOLLOWUPS,
    "recovery_needed": ACTION_REVIEW_RECOVERY,
    "approval_rejected": ACTION_REVIEW_RECOVERY,
    "approval_failed": ACTION_REVIEW_RECOVERY,
    "blocked": ACTION_WAIT_BLOCKER,
    "unknown": ACTION_MANUAL_REVIEW,
}


@dataclass
class TaskCycleDecision:
    ok: bool
    action: str = ACTION_NO_TASK
    task_id: str = ""
    title: str = ""
    stage: str = ""
    stage_label: str = ""
    reason: str = ""
    lifecycle: dict[str, Any] | None = None
    task: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskCycleActionResult:
    ok: bool
    action: str = ""
    task_id: str = ""
    dry_run: bool = True
    message: str = ""
    error: str = ""
    blocked: bool = False
    stop_cycle: bool = False
    stopped_reason: str = ""
    approval_id: str = ""
    patch_id: str = ""
    created_followup_task_ids: list[str] | None = None
    executed_task_id: str = ""
    execution: dict[str, Any] | None = None
    recovery: dict[str, Any] | None = None
    approval: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_priority(lifecycle: dict[str, Any]) -> int:
    return PRIORITY_ORDER.get(str(lifecycle.get("priority") or "medium").lower(), 2)


def _stage_policy_rank(lifecycle: dict[str, Any]) -> int:
    return STAGE_POLICY_ORDER.get(str(lifecycle.get("stage") or "unknown"), 99)


def _decision_reason(stage: str, action: str) -> str:
    reasons = {
        ACTION_REQUEST_APPROVAL: "Task requires approval before execution, so the cycle should create or refresh an approval request.",
        ACTION_WAIT_APPROVAL: "Task already has a pending approval request; the cycle should not execute it until that approval is resolved.",
        ACTION_EXECUTE_APPROVED_TASK: "Task has an approved execution path; it can run only when approval-required execution is explicitly allowed.",
        ACTION_EXECUTE_TASK: "Task is ready and does not need approval; the cycle may dry-run or execute it through the task work executor.",
        ACTION_CREATE_PATCH_FOLLOWUPS: "Task has a proposed patch link; the cycle should create review/apply/test follow-up tasks if they do not exist.",
        ACTION_REVIEW_RECOVERY: "Task needs recovery; the cycle should surface the recovery plan instead of blindly retrying.",
        ACTION_WAIT_BLOCKER: "Task is blocked without a recoverable executor marker; manual blocker resolution is needed.",
        ACTION_MANUAL_REVIEW: "Task lifecycle is unclear; manual review is safer than automatic action.",
    }
    return reasons.get(action, f"Lifecycle stage {stage} selected action {action}.")


def list_cycle_candidates(project: str = "") -> list[dict[str, Any]]:
    rows = list_task_lifecycles(project=project, include_closed=False, stage_filter="open")
    return sorted(rows, key=lambda row: (_stage_policy_rank(row), _task_priority(row), str(row.get("task_id") or "")))


def choose_next_cycle_decision(project: str = "") -> TaskCycleDecision:
    candidates = list_cycle_candidates(project=project)
    if not candidates:
        return TaskCycleDecision(
            True,
            action=ACTION_NO_TASK,
            reason="No open task lifecycle candidates found.",
            metadata={"project": project, "candidate_count": 0},
        )

    lifecycle = candidates[0]
    task_id = str(lifecycle.get("task_id") or "")
    task = get_task(task_id) if task_id else None
    stage = str(lifecycle.get("stage") or "unknown")
    action = STAGE_ACTIONS.get(stage, ACTION_MANUAL_REVIEW)
    return TaskCycleDecision(
        True,
        action=action,
        task_id=task_id,
        title=str(lifecycle.get("title") or (task or {}).get("title") or ""),
        stage=stage,
        stage_label=str(lifecycle.get("stage_label") or stage.replace("_", " ").title()),
        reason=_decision_reason(stage, action),
        lifecycle=lifecycle,
        task=task,
        metadata={
            "project": project,
            "candidate_count": len(candidates),
            "selected_at": _now(),
            "policy_order": STAGE_POLICY_ORDER,
        },
    )


def execute_cycle_decision(
    decision: TaskCycleDecision,
    dry_run: bool = True,
    use_ai: bool = True,
    approve_work_execution: bool = False,
    auto_create_patch_followups: bool = True,
    auto_request_approvals: bool = True,
    auto_retry_recovery: bool = False,
) -> TaskCycleActionResult:
    task_id = decision.task_id
    action = decision.action

    if action == ACTION_NO_TASK:
        return TaskCycleActionResult(
            True,
            action=action,
            task_id=task_id,
            dry_run=dry_run,
            message=decision.reason or "No task selected.",
            stop_cycle=True,
            stopped_reason="no_lifecycle_candidate",
        )

    if not task_id:
        return TaskCycleActionResult(
            False,
            action=action,
            dry_run=dry_run,
            error="Lifecycle decision did not include a task id.",
            stop_cycle=True,
            stopped_reason="decision_missing_task_id",
        )

    if action == ACTION_REQUEST_APPROVAL:
        if not auto_request_approvals:
            return TaskCycleActionResult(
                True,
                action=action,
                task_id=task_id,
                dry_run=dry_run,
                message="Approval request was selected but auto approval requests are disabled for this cycle.",
                blocked=True,
                stop_cycle=True,
                stopped_reason="approval_request_disabled",
            )
        result = request_task_work_approval(
            task_id,
            reason="Lifecycle-aware work cycle selected this approval-required task.",
            use_ai=use_ai,
            dry_run=dry_run,
        )
        return TaskCycleActionResult(
            result.ok,
            action=action,
            task_id=result.task_id or task_id,
            dry_run=dry_run,
            message=result.message,
            error=result.error,
            approval_id=result.approval_id,
            approval=result.approval,
            metadata=result.to_dict(),
            stop_cycle=bool(dry_run or not result.ok),
            stopped_reason="dry_run_lifecycle_preview_complete" if dry_run else ("approval_request_failed" if not result.ok else ""),
        )

    if action == ACTION_CREATE_PATCH_FOLLOWUPS:
        patch_id = str((decision.lifecycle or {}).get("patch_id") or (decision.task or {}).get("patch_id") or "").strip()
        if not patch_id:
            return TaskCycleActionResult(
                False,
                action=action,
                task_id=task_id,
                dry_run=dry_run,
                error="Patch-proposed lifecycle stage did not include a patch id.",
                stop_cycle=True,
                stopped_reason="patch_followup_missing_patch_id",
            )
        if dry_run or not auto_create_patch_followups:
            return TaskCycleActionResult(
                True,
                action=action,
                task_id=task_id,
                dry_run=dry_run,
                message="Dry run: would create review/apply/test follow-up tasks for the linked patch." if dry_run else "Patch follow-up creation is disabled for this cycle.",
                patch_id=patch_id,
                blocked=not auto_create_patch_followups and not dry_run,
                stop_cycle=True,
                stopped_reason="dry_run_lifecycle_preview_complete" if dry_run else "patch_followups_disabled",
            )
        followups = create_patch_followup_tasks(patch_id, project_id=str((decision.lifecycle or {}).get("project") or "eidolon"))
        ids = followups.created_task_ids or followups.created_work_ids or []
        return TaskCycleActionResult(
            followups.ok,
            action=action,
            task_id=task_id,
            dry_run=dry_run,
            message=followups.message,
            error=followups.error,
            patch_id=patch_id,
            created_followup_task_ids=ids,
            metadata=followups.to_dict(),
            stop_cycle=not followups.ok,
            stopped_reason="patch_followup_failed" if not followups.ok else "",
        )

    if action == ACTION_REVIEW_RECOVERY:
        recovery = build_task_recovery(task_id)
        if dry_run or not auto_retry_recovery:
            execution_preview = retry_task_work(task_id, dry_run=True, allow_approval_required=approve_work_execution, use_ai=use_ai)
            return TaskCycleActionResult(
                bool(recovery.get("ok", True)),
                action=action,
                task_id=task_id,
                dry_run=dry_run,
                message="Recovery plan selected. The cycle previewed retry safety but did not mutate task state." if dry_run else "Recovery plan selected. Auto retry recovery is disabled, so no task state changed.",
                error=str(recovery.get("error") or ""),
                recovery=recovery,
                execution=execution_preview.to_dict(),
                blocked=True,
                stop_cycle=True,
                stopped_reason="dry_run_lifecycle_preview_complete" if dry_run else "recovery_needs_manual_choice",
            )
        ready = mark_task_ready_for_retry(task_id, note="Lifecycle-aware cycle prepared this task for retry.")
        return TaskCycleActionResult(
            ready.ok,
            action=action,
            task_id=ready.task_id or task_id,
            dry_run=dry_run,
            message=ready.message or "Task recovery state updated.",
            error=ready.error,
            recovery=ready.recovery,
            metadata=ready.to_dict(),
            stop_cycle=not ready.ok,
            stopped_reason="recovery_prepare_failed" if not ready.ok else "",
        )

    if action == ACTION_EXECUTE_APPROVED_TASK:
        if not approve_work_execution:
            return TaskCycleActionResult(
                True,
                action=action,
                task_id=task_id,
                dry_run=dry_run,
                message="Task is approved-ready, but approval-required execution is disabled for this cycle. Use --approve-work-cycle-actions after review.",
                blocked=True,
                stop_cycle=True,
                stopped_reason="approved_task_execution_not_allowed",
            )
        execution = execute_task_work_item(task_id, dry_run=dry_run, allow_approval_required=True, use_ai=use_ai)
        return TaskCycleActionResult(
            execution.ok,
            action=action,
            task_id=task_id,
            dry_run=dry_run,
            message=execution.message,
            error=execution.error,
            blocked=execution.blocked,
            stop_cycle=bool(dry_run or execution.blocked or not execution.ok),
            stopped_reason="dry_run_lifecycle_preview_complete" if dry_run else ("task_blocked" if execution.blocked else ("task_failed" if not execution.ok else "")),
            executed_task_id=task_id,
            execution=execution.to_dict(),
            patch_id=str((execution.metadata or {}).get("patch_id") or ""),
        )

    if action == ACTION_EXECUTE_TASK:
        execution = execute_task_work_item(task_id, dry_run=dry_run, allow_approval_required=False, use_ai=use_ai)
        return TaskCycleActionResult(
            execution.ok,
            action=action,
            task_id=task_id,
            dry_run=dry_run,
            message=execution.message,
            error=execution.error,
            blocked=execution.blocked,
            stop_cycle=bool(dry_run or execution.blocked or not execution.ok),
            stopped_reason="dry_run_lifecycle_preview_complete" if dry_run else ("task_blocked" if execution.blocked else ("task_failed" if not execution.ok else "")),
            executed_task_id=task_id,
            execution=execution.to_dict(),
            patch_id=str((execution.metadata or {}).get("patch_id") or ""),
        )

    if action in {ACTION_WAIT_APPROVAL, ACTION_WAIT_BLOCKER, ACTION_WAIT_REJECTION, ACTION_WAIT_FAILURE, ACTION_MANUAL_REVIEW}:
        return TaskCycleActionResult(
            True,
            action=action,
            task_id=task_id,
            dry_run=dry_run,
            message=decision.reason,
            blocked=True,
            stop_cycle=True,
            stopped_reason=action,
            metadata={"lifecycle_stage": decision.stage},
        )

    return TaskCycleActionResult(
        False,
        action=action,
        task_id=task_id,
        dry_run=dry_run,
        error=f"Unsupported cycle decision action: {action}",
        stop_cycle=True,
        stopped_reason="unsupported_lifecycle_action",
    )


def cycle_decision_text(decision_or_result: TaskCycleDecision | TaskCycleActionResult | dict[str, Any], full: bool = False) -> str:
    data = decision_or_result.to_dict() if hasattr(decision_or_result, "to_dict") else dict(decision_or_result or {})
    lines = ["# Task cycle decision"]
    if data.get("task_id"):
        lines.append(f"Task: {data.get('task_id')}")
    if data.get("title"):
        lines.append(f"Title: {data.get('title')}")
    if data.get("stage_label") or data.get("stage"):
        lines.append(f"Lifecycle: {data.get('stage_label') or data.get('stage')}")
    if data.get("action"):
        lines.append(f"Action: {data.get('action')}")
    if data.get("dry_run") is not None:
        lines.append(f"Dry run: {data.get('dry_run')}")
    if data.get("message"):
        lines.append(f"Message: {data.get('message')}")
    if data.get("reason"):
        lines.append(f"Reason: {data.get('reason')}")
    if data.get("error"):
        lines.append(f"Error: {data.get('error')}")
    if data.get("approval_id"):
        lines.append(f"Approval: {data.get('approval_id')}")
    if data.get("patch_id"):
        lines.append(f"Patch: {data.get('patch_id')}")
    ids = data.get("created_followup_task_ids") or []
    if ids:
        lines.append("Created follow-up tasks: " + ", ".join(str(item) for item in ids))
    if full:
        import json
        lines.extend(["", "## Raw", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()
