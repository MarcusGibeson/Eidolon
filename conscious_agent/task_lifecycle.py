from __future__ import annotations

"""Task lifecycle helpers for dashboard/API clarity.

v5.7 note:
    task_queue.py remains the source of truth. This module does not mutate task
    state; it derives a readable lifecycle stage from task status, risk,
    approval metadata, linked approvals, and patch metadata. v5.7 adds
    filter helpers so dashboard/API callers can query stage-specific work
    without re-implementing lifecycle logic in the UI layer.
"""

from typing import Any

from approval_manager import list_approvals
from task_queue import get_task, list_tasks

APPROVAL_RISKS = {"medium", "high", "critical"}
OPEN_STATUSES = {"planned", "active", "blocked", "paused"}

STAGE_ORDER = {
    "ready": 0,
    "active": 1,
    "approval_required": 2,
    "approval_pending": 3,
    "approved_ready": 4,
    "approval_rejected": 5,
    "approval_failed": 6,
    "blocked": 7,
    "patch_proposed": 8,
    "done": 9,
    "cancelled": 10,
    "unknown": 99,
}

STAGE_LABELS = {
    "ready": "Ready",
    "active": "Active",
    "approval_required": "Needs approval request",
    "approval_pending": "Approval pending",
    "approved_ready": "Approved, ready to run",
    "approval_rejected": "Approval rejected",
    "approval_failed": "Approval failed",
    "blocked": "Blocked",
    "patch_proposed": "Patch proposed",
    "done": "Done",
    "cancelled": "Cancelled",
    "unknown": "Unknown",
}

STAGE_NEXT_ACTIONS = {
    "ready": "Dry-run or execute the task work executor.",
    "active": "Review the current result, then mark done, block, or continue execution.",
    "approval_required": "Create an approval request before executing this task.",
    "approval_pending": "Review, dry-run, approve, or reject the linked approval request.",
    "approved_ready": "Run the approved approval command or execute with approval override.",
    "approval_rejected": "Revise the task or cancel it; approval was rejected.",
    "approval_failed": "Inspect the failed approval result before retrying.",
    "blocked": "Resolve the blocker or request approval if risk is the blocker.",
    "patch_proposed": "Review the linked patch and create/apply follow-up tasks as needed.",
    "done": "No action needed.",
    "cancelled": "No action needed unless this should be restored manually.",
    "unknown": "Inspect the raw task record.",
}


STAGE_FILTER_LABELS = {
    "all": "All",
    "open": "Open",
    "needs_attention": "Needs attention",
    "ready_to_act": "Ready to act",
    "ready": "Ready",
    "active": "Active",
    "approval_required": "Needs approval request",
    "approval_pending": "Approval pending",
    "approved_ready": "Approved, ready to run",
    "approval_rejected": "Approval rejected",
    "approval_failed": "Approval failed",
    "blocked": "Blocked",
    "patch_proposed": "Patch proposed",
    "done": "Done",
    "cancelled": "Cancelled",
    "unknown": "Unknown",
}

STAGE_FILTER_ALIASES = {
    "": "all",
    "all": "all",
    "any": "all",
    "open": "open",
    "needs-attention": "needs_attention",
    "needs_attention": "needs_attention",
    "attention": "needs_attention",
    "ready-to-act": "ready_to_act",
    "ready_to_act": "ready_to_act",
    "actionable": "ready_to_act",
    "ready": "ready",
    "active": "active",
    "needs-approval": "approval_required",
    "needs_approval": "approval_required",
    "approval-required": "approval_required",
    "approval_required": "approval_required",
    "approval-pending": "approval_pending",
    "approval_pending": "approval_pending",
    "pending-approval": "approval_pending",
    "pending_approval": "approval_pending",
    "approved-ready": "approved_ready",
    "approved_ready": "approved_ready",
    "approved": "approved_ready",
    "blocked": "blocked",
    "patch-proposed": "patch_proposed",
    "patch_proposed": "patch_proposed",
    "patch": "patch_proposed",
    "done": "done",
    "completed": "done",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "approval-rejected": "approval_rejected",
    "approval_rejected": "approval_rejected",
    "rejected": "approval_rejected",
    "approval-failed": "approval_failed",
    "approval_failed": "approval_failed",
    "failed": "approval_failed",
    "unknown": "unknown",
}

NEEDS_ATTENTION_STAGES = {"approval_required", "approval_pending", "approval_rejected", "approval_failed", "blocked"}
READY_TO_ACT_STAGES = {"ready", "active", "approved_ready", "patch_proposed"}
OPEN_LIFECYCLE_STAGES = set(STAGE_ORDER) - {"done", "cancelled"}


def normalize_lifecycle_stage_filter(stage: str | None = "") -> str:
    token = str(stage or "").strip().lower().replace(" ", "_")
    return STAGE_FILTER_ALIASES.get(token, STAGE_FILTER_ALIASES.get(token.replace("_", "-"), token if token in STAGE_ORDER else "all"))


def lifecycle_stage_matches(lifecycle: dict[str, Any], stage_filter: str | None = "") -> bool:
    stage_filter = normalize_lifecycle_stage_filter(stage_filter)
    if stage_filter == "all":
        return True
    stage = str(lifecycle.get("stage") or "unknown")
    if stage_filter == "open":
        return stage in OPEN_LIFECYCLE_STAGES
    if stage_filter == "needs_attention":
        return stage in NEEDS_ATTENTION_STAGES
    if stage_filter == "ready_to_act":
        return stage in READY_TO_ACT_STAGES
    return stage == stage_filter


def _metadata(task: dict[str, Any] | None) -> dict[str, Any]:
    raw = (task or {}).get("metadata") if isinstance(task, dict) else {}
    return dict(raw) if isinstance(raw, dict) else {}


def _approval_matches_task(approval: dict[str, Any], task_id: str) -> bool:
    if not task_id:
        return False
    metadata = approval.get("metadata") if isinstance(approval.get("metadata"), dict) else {}
    if metadata.get("task_id") == task_id or metadata.get("work_item_id") == task_id:
        return True
    if approval.get("object_id") == task_id:
        return True
    command = str(approval.get("command") or "")
    return f"--execute-task-work-id {task_id}" in command


def approvals_for_task(task_id: str, include_closed: bool = True) -> list[dict[str, Any]]:
    return [
        approval for approval in list_approvals(include_closed=include_closed)
        if _approval_matches_task(approval, task_id)
    ]


def _latest_approval(task: dict[str, Any], linked_approvals: list[dict[str, Any]]) -> dict[str, Any] | None:
    metadata = _metadata(task)
    approval_id = str(metadata.get("approval_id") or "").strip()
    if approval_id:
        for approval in linked_approvals:
            if approval.get("id") == approval_id:
                return approval
    return linked_approvals[0] if linked_approvals else None


def _needs_approval(task: dict[str, Any]) -> bool:
    risk = str(task.get("risk") or "low").lower().strip()
    return bool(task.get("requires_approval")) or risk in APPROVAL_RISKS


def derive_task_lifecycle(
    task: dict[str, Any] | None,
    linked_approvals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not task:
        return {
            "task_id": "",
            "stage": "unknown",
            "stage_label": STAGE_LABELS["unknown"],
            "next_action": STAGE_NEXT_ACTIONS["unknown"],
            "approval_id": "",
            "approval_status": "",
            "patch_id": "",
            "patch_status": "",
            "needs_approval": False,
            "linked_approvals": [],
            "css_class": "stage-unknown",
        }

    task_id = str(task.get("id") or "")
    metadata = _metadata(task)
    if linked_approvals is None:
        linked_approvals = approvals_for_task(task_id, include_closed=True)
    latest = _latest_approval(task, linked_approvals)

    status = str(task.get("status") or "planned").lower().strip()
    risk = str(task.get("risk") or "low").lower().strip()
    patch_id = str(task.get("patch_id") or metadata.get("patch_id") or "").strip()
    patch_status = str(task.get("patch_status") or metadata.get("patch_status") or "").strip()
    needs_approval = _needs_approval(task)
    approval_id = str((latest or {}).get("id") or metadata.get("approval_id") or "").strip()
    approval_status = str((latest or {}).get("status") or metadata.get("approval_status") or "").strip()

    if status == "done":
        stage = "done"
    elif status == "cancelled":
        stage = "cancelled"
    elif approval_status == "pending":
        stage = "approval_pending"
    elif approval_status == "approved" and needs_approval and status in OPEN_STATUSES:
        stage = "approved_ready"
    elif approval_status == "rejected":
        stage = "approval_rejected"
    elif approval_status == "failed":
        stage = "approval_failed"
    elif needs_approval and not approval_id and status in OPEN_STATUSES:
        stage = "approval_required"
    elif status == "blocked":
        stage = "blocked"
    elif status == "active":
        stage = "active"
    elif patch_id and patch_status in {"proposed", "queued", "needs_review"}:
        stage = "patch_proposed"
    elif status == "planned":
        stage = "ready"
    else:
        stage = "unknown"

    return {
        "task_id": task_id,
        "title": task.get("title", ""),
        "project": task.get("project", ""),
        "status": status,
        "priority": task.get("priority", ""),
        "risk": risk,
        "requires_approval": bool(task.get("requires_approval")),
        "needs_approval": needs_approval,
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage, STAGE_LABELS["unknown"]),
        "stage_order": STAGE_ORDER.get(stage, STAGE_ORDER["unknown"]),
        "next_action": STAGE_NEXT_ACTIONS.get(stage, STAGE_NEXT_ACTIONS["unknown"]),
        "approval_id": approval_id,
        "approval_status": approval_status,
        "linked_approval_ids": [str(approval.get("id") or "") for approval in linked_approvals if approval.get("id")],
        "linked_approvals": linked_approvals,
        "patch_id": patch_id,
        "patch_status": patch_status,
        "action_type": str(metadata.get("action_type") or ""),
        "target_file": str(metadata.get("patch_target_file") or metadata.get("target_file") or ""),
        "css_class": f"stage-{stage.replace('_', '-')}",
    }


def list_task_lifecycles(
    project: str = "",
    include_closed: bool = True,
    stage_filter: str | None = "",
) -> list[dict[str, Any]]:
    rows = [derive_task_lifecycle(task) for task in list_tasks(project=project, include_cancelled=include_closed)]
    if stage_filter:
        rows = [row for row in rows if lifecycle_stage_matches(row, stage_filter)]
    return sorted(rows, key=lambda item: (item.get("stage_order", 99), str(item.get("priority", "")), str(item.get("task_id", ""))))


def task_lifecycle_summary(project: str = "", stage_filter: str | None = "") -> dict[str, Any]:
    all_rows = list_task_lifecycles(project=project, include_closed=True, stage_filter="")
    selected_filter = normalize_lifecycle_stage_filter(stage_filter)
    rows = [row for row in all_rows if lifecycle_stage_matches(row, selected_filter)]
    counts = {key: 0 for key in STAGE_ORDER}
    for row in all_rows:
        counts[row.get("stage", "unknown")] = counts.get(row.get("stage", "unknown"), 0) + 1
    open_rows = [row for row in all_rows if row.get("stage") not in {"done", "cancelled"}]
    return {
        "total": len(all_rows),
        "open": len(open_rows),
        "counts": counts,
        "needs_attention": sum(counts.get(stage, 0) for stage in NEEDS_ATTENTION_STAGES),
        "ready_to_act": sum(counts.get(stage, 0) for stage in READY_TO_ACT_STAGES),
        "selected_filter": selected_filter,
        "selected_filter_label": STAGE_FILTER_LABELS.get(selected_filter, selected_filter.replace("_", " ").title()),
        "filtered_total": len(rows),
        "next": open_rows[0] if open_rows else None,
        "rows": rows,
        "all_rows": all_rows,
        "filters": [
            {"key": key, "label": label, "count": _filter_count(all_rows, key)}
            for key, label in STAGE_FILTER_LABELS.items()
        ],
    }


def _filter_count(rows: list[dict[str, Any]], stage_filter: str) -> int:
    return sum(1 for row in rows if lifecycle_stage_matches(row, stage_filter))


def task_lifecycle_text(task_or_id: dict[str, Any] | str | None, full: bool = False) -> str:
    task = get_task(task_or_id) if isinstance(task_or_id, str) else task_or_id
    lifecycle = derive_task_lifecycle(task)
    lines = [
        f"Lifecycle: {lifecycle.get('stage_label')}",
        f"Task: {lifecycle.get('task_id')}",
        f"Status: {lifecycle.get('status') or '[none]'}",
        f"Risk: {lifecycle.get('risk') or '[none]'}",
        f"Approval: {lifecycle.get('approval_id') or '[none]'} ({lifecycle.get('approval_status') or 'none'})",
        f"Patch: {lifecycle.get('patch_id') or '[none]'} ({lifecycle.get('patch_status') or 'none'})",
        f"Next action: {lifecycle.get('next_action')}",
    ]
    if full:
        lines.extend(["", "Raw lifecycle:", __import__("json").dumps(lifecycle, indent=2, default=str)])
    return "\n".join(lines)
