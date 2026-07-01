from __future__ import annotations

"""Completion reporting and cleanup for stable-loop decision follow-up chains.

v6.8 note:
    v6.7 linked stable-loop final decisions to task-backed follow-ups and made
    those chains resolvable. This module makes the closure state reportable:
    unresolved chains, ready-to-resolve chains, resolved chains, and cleanup
    candidates can be filtered from CLI/API/dashboard without spelunking JSON.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from stable_loop_decision_report import decision_label, final_decision_for_loop
from stable_loop_followup_lifecycle import (
    FOLLOWUP_LIFECYCLE_VERSION,
    stable_loop_followup_lifecycle_summary,
    stable_loop_followup_tasks,
)
from stable_loop_operator_notes import ensure_operator_notes, summarize_operator_notes
from stable_loop_review import loop_is_archived, set_stable_loop_archived
from stable_supervised_loop import list_stable_loops, load_stable_loop, save_stable_loop
from task_queue import update_task_fields

FOLLOWUP_COMPLETION_VERSION = "1032.0"
ACTION_REQUIRED_DECISIONS = {"fix_forward", "rollback", "needs_review"}
TERMINAL_TASK_STATUSES = {"done", "cancelled"}

FOLLOWUP_COMPLETION_FILTER_LABELS = {
    "all": "All follow-up chains",
    "action_required": "Action-required decisions",
    "missing_followups": "Missing follow-up tasks",
    "open": "Open follow-up tasks",
    "unresolved": "Unresolved",
    "ready_to_resolve": "Ready to resolve",
    "resolved": "Resolved",
    "archived": "Archived",
    "cleanup_default": "Cleanup candidates",
}


@dataclass
class StableLoopFollowupCompletionCleanupResult:
    ok: bool
    dry_run: bool = True
    filter: str = "cleanup_default"
    filter_label: str = "Cleanup candidates"
    limit: int = 25
    include_archived: bool = False
    candidate_count: int = 0
    selected_count: int = 0
    selected_ids: list[str] | None = None
    archived_ids: list[str] | None = None
    message: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_followup_completion_filter(value: str | None) -> str:
    token = str(value or "all").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": "all",
        "any": "all",
        "needs_action": "action_required",
        "requires_action": "action_required",
        "missing": "missing_followups",
        "no_followups": "missing_followups",
        "open_tasks": "open",
        "in_progress": "open",
        "not_resolved": "unresolved",
        "unclosed": "unresolved",
        "ready": "ready_to_resolve",
        "ready_for_resolution": "ready_to_resolve",
        "closed": "resolved",
        "complete": "resolved",
        "completed": "resolved",
        "archive": "archived",
        "archives": "archived",
        "cleanup": "cleanup_default",
        "cleanup_candidates": "cleanup_default",
    }
    token = aliases.get(token, token)
    return token if token in FOLLOWUP_COMPLETION_FILTER_LABELS else "all"


def _resolution_for_loop(loop: dict[str, Any] | None) -> dict[str, Any]:
    if not loop:
        return {}
    notes = loop.get("operator_notes") if isinstance(loop.get("operator_notes"), dict) else {}
    resolution = notes.get("decision_followup_resolution") if isinstance(notes.get("decision_followup_resolution"), dict) else {}
    return resolution


def stable_loop_followup_completion_row(loop_or_id: dict[str, Any] | str | None) -> dict[str, Any]:
    loop = load_stable_loop(loop_or_id) if isinstance(loop_or_id, str) else loop_or_id
    if not loop:
        return {
            "ok": False,
            "id": str(loop_or_id or ""),
            "message": "Stable loop not found.",
        }

    loop_id = str(loop.get("id") or "")
    decision = final_decision_for_loop(loop)
    action_required = decision in ACTION_REQUIRED_DECISIONS
    tasks = stable_loop_followup_tasks(loop_id, include_closed=True) if loop_id else []
    task_ids = [str(task.get("id") or "") for task in tasks if task.get("id")]
    open_task_ids = [str(task.get("id") or "") for task in tasks if str(task.get("status") or "") not in TERMINAL_TASK_STATUSES]
    terminal_task_ids = [str(task.get("id") or "") for task in tasks if str(task.get("status") or "") in TERMINAL_TASK_STATUSES]
    resolution = _resolution_for_loop(loop)
    resolution_status = str(resolution.get("status") or "open")
    archived = loop_is_archived(loop)

    if resolution_status == "resolved":
        completion_status = "resolved"
        recommended_action = "Archive the stable-loop record when it no longer needs active inspection."
    elif action_required and not tasks:
        completion_status = "missing_followups"
        recommended_action = "Create task-backed follow-ups for this stable-loop decision."
    elif open_task_ids:
        completion_status = "open"
        recommended_action = "Complete or cancel the linked follow-up task(s), then resolve the chain."
    elif tasks and not open_task_ids:
        completion_status = "ready_to_resolve"
        recommended_action = "Resolve the stable-loop follow-up chain; optionally archive afterward."
    elif action_required:
        completion_status = "missing_followups"
        recommended_action = "Create follow-up task(s) or force-resolve with an operator note."
    else:
        completion_status = "not_required"
        recommended_action = "No decision follow-up chain is required for this final decision."

    if archived and completion_status != "resolved":
        recommended_action = "Archived. Restore only if this follow-up chain needs active inspection."

    return {
        "ok": True,
        "id": loop_id,
        "version": loop.get("version", ""),
        "project_id": loop.get("project_id", ""),
        "created_at": loop.get("created_at", ""),
        "live": bool(loop.get("live")),
        "ok_record": bool(loop.get("ok")),
        "archived": archived,
        "final_decision": decision,
        "final_decision_label": decision_label(decision),
        "action_required": action_required,
        "completion_status": completion_status,
        "completion_status_label": FOLLOWUP_COMPLETION_FILTER_LABELS.get(completion_status, completion_status.replace("_", " ").title()),
        "resolution_status": resolution_status,
        "resolution": resolution,
        "task_count": len(task_ids),
        "open_task_count": len(open_task_ids),
        "terminal_task_count": len(terminal_task_ids),
        "task_ids": task_ids,
        "open_task_ids": open_task_ids,
        "terminal_task_ids": terminal_task_ids,
        "ready_to_resolve": bool(tasks and not open_task_ids and resolution_status != "resolved"),
        "missing_followups": bool(action_required and not tasks and resolution_status != "resolved"),
        "unresolved": bool(action_required and resolution_status != "resolved"),
        "recommended_action": recommended_action,
    }


def stable_loop_followup_completion_matches(row: dict[str, Any], completion_filter: str | None = "all", include_archived: bool = False) -> bool:
    token = normalize_followup_completion_filter(completion_filter)
    if token == "archived":
        return bool(row.get("archived"))
    if row.get("archived") and not include_archived:
        return False
    if token == "all":
        return True
    if token == "action_required":
        return bool(row.get("action_required"))
    if token == "missing_followups":
        return bool(row.get("missing_followups"))
    if token == "open":
        return int(row.get("open_task_count") or 0) > 0
    if token == "unresolved":
        return bool(row.get("unresolved"))
    if token == "ready_to_resolve":
        return bool(row.get("ready_to_resolve"))
    if token == "resolved":
        return str(row.get("resolution_status") or "") == "resolved"
    if token == "cleanup_default":
        return str(row.get("resolution_status") or "") == "resolved" and not bool(row.get("archived"))
    return True


def list_stable_loop_followup_completion_rows(
    completion_filter: str | None = "all",
    include_archived: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = [stable_loop_followup_completion_row(loop) for loop in list_stable_loops()]
    rows = [row for row in rows if row.get("ok") and stable_loop_followup_completion_matches(row, completion_filter, include_archived=include_archived)]
    if limit and limit > 0:
        rows = rows[: max(1, min(int(limit), 500))]
    return rows


def stable_loop_followup_completion_summary(
    completion_filter: str | None = "all",
    include_archived: bool = False,
) -> dict[str, Any]:
    token = normalize_followup_completion_filter(completion_filter)
    all_rows = [stable_loop_followup_completion_row(loop) for loop in list_stable_loops()]
    all_rows = [row for row in all_rows if row.get("ok")]
    visible_rows = [row for row in all_rows if include_archived or not row.get("archived")]
    filtered_rows = [row for row in all_rows if stable_loop_followup_completion_matches(row, token, include_archived=include_archived)]
    filters = ["all", "action_required", "missing_followups", "open", "unresolved", "ready_to_resolve", "resolved", "cleanup_default", "archived"]
    filter_counts = {
        item: len([row for row in all_rows if stable_loop_followup_completion_matches(row, item, include_archived=include_archived or item == "archived")])
        for item in filters
    }
    lifecycle = stable_loop_followup_lifecycle_summary(include_closed=True, include_archived=include_archived)
    return {
        "version": FOLLOWUP_COMPLETION_VERSION,
        "lifecycle_version": FOLLOWUP_LIFECYCLE_VERSION,
        "generated_at": _now(),
        "selected_filter": token,
        "selected_filter_label": FOLLOWUP_COMPLETION_FILTER_LABELS.get(token, token),
        "include_archived": include_archived,
        "total": len(visible_rows),
        "total_including_archived": len(all_rows),
        "filtered_count": len(filtered_rows),
        "action_required_count": filter_counts.get("action_required", 0),
        "missing_followup_count": filter_counts.get("missing_followups", 0),
        "open_followup_chain_count": filter_counts.get("open", 0),
        "unresolved_count": filter_counts.get("unresolved", 0),
        "ready_to_resolve_count": filter_counts.get("ready_to_resolve", 0),
        "resolved_count": filter_counts.get("resolved", 0),
        "cleanup_candidate_count": filter_counts.get("cleanup_default", 0),
        "archived_count": filter_counts.get("archived", 0),
        "filter_counts": filter_counts,
        "lifecycle_summary": lifecycle,
        "filtered_ids": [str(row.get("id") or "") for row in filtered_rows[:50]],
        "rows": filtered_rows[:50],
    }


def mark_stable_loop_followup_chain_closed(
    loop_id: str,
    note: str = "",
    reviewer: str = "operator",
    archive: bool = False,
) -> dict[str, Any]:
    loop = load_stable_loop(loop_id)
    if not loop:
        return {"ok": False, "loop_id": loop_id, "error": f"Stable loop not found: {loop_id}"}
    row = stable_loop_followup_completion_row(loop)
    if row.get("resolution_status") != "resolved":
        return {"ok": False, "loop_id": row.get("id", loop_id), "row": row, "error": "Follow-up chain must be resolved before marking closure complete."}
    notes = ensure_operator_notes(loop, save=False)
    now = _now()
    closure = {
        "version": FOLLOWUP_COMPLETION_VERSION,
        "status": "closed",
        "closed_at": now,
        "closed_by": reviewer or "operator",
        "note": note or "Stable-loop follow-up chain closure confirmed.",
        "task_ids": row.get("task_ids") or [],
    }
    notes["decision_followup_closure"] = closure
    entries = notes.get("notes") if isinstance(notes.get("notes"), list) else []
    entries.append({
        "at": now,
        "by": reviewer or "operator",
        "note": closure["note"],
        "source": "stable_loop_followup_completion",
    })
    notes["notes"] = entries
    notes["updated_at"] = now
    notes["summary"] = summarize_operator_notes(notes)
    loop["operator_notes"] = notes
    save_stable_loop(loop)

    for task_id in row.get("task_ids") or []:
        update_task_fields(task_id, metadata={
            "stable_loop_followup_closure_status": "closed",
            "stable_loop_followup_closed_at": now,
            "stable_loop_followup_closed_by": reviewer or "operator",
        })

    archived = False
    if archive:
        archive_result = set_stable_loop_archived(row.get("id", loop_id), archived=True, note=closure["note"], reviewer=reviewer)
        archived = bool(archive_result.ok)
        loop = archive_result.loop or load_stable_loop(row.get("id", loop_id)) or loop

    return {
        "ok": True,
        "loop_id": row.get("id", loop_id),
        "closed": True,
        "archived": archived,
        "closure": closure,
        "row": stable_loop_followup_completion_row(loop),
        "message": f"Stable-loop follow-up chain closed for {row.get('id', loop_id)}.",
    }


def cleanup_stable_loop_followup_completions(
    completion_filter: str | None = "cleanup_default",
    limit: int = 25,
    dry_run: bool = True,
    include_archived: bool = False,
    reviewer: str = "operator",
) -> StableLoopFollowupCompletionCleanupResult:
    token = normalize_followup_completion_filter(completion_filter or "cleanup_default")
    candidates = list_stable_loop_followup_completion_rows(token, include_archived=include_archived, limit=0)
    candidates = [row for row in candidates if not row.get("archived")]
    limit_value = max(1, min(int(limit or 25), 500))
    selected = candidates[:limit_value]
    archived_ids: list[str] = []
    if not dry_run:
        for row in selected:
            result = set_stable_loop_archived(
                str(row.get("id") or ""),
                archived=True,
                note=f"Archived by stable-loop follow-up completion cleanup filter: {token}.",
                reviewer=reviewer,
            )
            if result.ok:
                archived_ids.append(result.loop_id)
    return StableLoopFollowupCompletionCleanupResult(
        ok=True,
        dry_run=dry_run,
        filter=token,
        filter_label=FOLLOWUP_COMPLETION_FILTER_LABELS.get(token, token),
        limit=limit_value,
        include_archived=include_archived,
        candidate_count=len(candidates),
        selected_count=len(selected),
        selected_ids=[str(row.get("id") or "") for row in selected],
        archived_ids=archived_ids,
        message=(
            f"Dry-run found {len(selected)} resolved follow-up completion record(s) to archive."
            if dry_run else f"Archived {len(archived_ids)} resolved follow-up completion record(s)."
        ),
    )


def stable_loop_followup_completion_report_text(data: dict[str, Any] | None = None, full: bool = False) -> str:
    report = data or stable_loop_followup_completion_summary()
    lines = [
        "# Stable-loop follow-up completion report",
        "",
        f"Version: {report.get('version', FOLLOWUP_COMPLETION_VERSION)}",
        f"Generated: {report.get('generated_at', '')}",
        f"Filter: {report.get('selected_filter_label', report.get('selected_filter', 'all'))}",
        f"Visible stable-loop records: {report.get('total', 0)}",
        f"Filtered records: {report.get('filtered_count', 0)}",
        f"Action-required decisions: {report.get('action_required_count', 0)}",
        f"Missing follow-up tasks: {report.get('missing_followup_count', 0)}",
        f"Open follow-up chains: {report.get('open_followup_chain_count', 0)}",
        f"Ready to resolve: {report.get('ready_to_resolve_count', 0)}",
        f"Resolved chains: {report.get('resolved_count', 0)}",
        f"Cleanup candidates: {report.get('cleanup_candidate_count', 0)}",
        f"Archived: {report.get('archived_count', 0)}",
    ]
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    if rows:
        lines.extend(["", "## Matching records"])
        for row in rows[:25]:
            lines.append(
                f"- {row.get('id')} | {row.get('completion_status_label')} | "
                f"decision={row.get('final_decision_label')} | tasks={row.get('task_count')} "
                f"open={row.get('open_task_count')} | archived={row.get('archived')} | "
                f"next={row.get('recommended_action')}"
            )
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def stable_loop_followup_completion_cleanup_text(result: StableLoopFollowupCompletionCleanupResult | dict[str, Any], full: bool = False) -> str:
    data = result.to_dict() if isinstance(result, StableLoopFollowupCompletionCleanupResult) else result
    lines = [
        "# Stable-loop follow-up completion cleanup",
        "",
        f"OK: {data.get('ok')}",
        f"Dry-run: {data.get('dry_run')}",
        f"Filter: {data.get('filter_label', data.get('filter'))}",
        f"Candidates: {data.get('candidate_count', 0)}",
        f"Selected: {data.get('selected_count', 0)}",
        f"Archived: {len(data.get('archived_ids') or [])}",
        f"Message: {data.get('message', '')}",
    ]
    if data.get("selected_ids"):
        lines.extend(["", "Selected IDs:"])
        lines.extend(f"- {item}" for item in data.get("selected_ids") or [])
    if data.get("archived_ids"):
        lines.extend(["", "Archived IDs:"])
        lines.extend(f"- {item}" for item in data.get("archived_ids") or [])
    if full:
        lines.extend(["", "## Raw cleanup result", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def stable_loop_followup_closure_text(result: dict[str, Any], full: bool = False) -> str:
    lines = [
        "# Stable-loop follow-up closure",
        "",
        f"OK: {result.get('ok')}",
        f"Loop: {result.get('loop_id', '')}",
        f"Closed: {result.get('closed')}",
        f"Archived: {result.get('archived')}",
        f"Message: {result.get('message', '')}",
    ]
    if result.get("error"):
        lines.append(f"Error: {result.get('error')}")
    row = result.get("row") if isinstance(result.get("row"), dict) else {}
    if row:
        lines.extend([
            "",
            "## Follow-up chain",
            f"Status: {row.get('completion_status_label')}",
            f"Decision: {row.get('final_decision_label')}",
            f"Tasks: {row.get('task_count')} total, {row.get('open_task_count')} open",
        ])
    if full:
        lines.extend(["", "## Raw result", json.dumps(result, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stable_loop_followup_completion_report(completion_filter: str = "all", include_archived: bool = False, full: bool = False) -> None:
    report = stable_loop_followup_completion_summary(completion_filter=completion_filter, include_archived=include_archived)
    print(stable_loop_followup_completion_report_text(report, full=full))


def print_stable_loop_followup_completion_rows(completion_filter: str = "all", include_archived: bool = False, limit: int = 50) -> None:
    rows = list_stable_loop_followup_completion_rows(completion_filter=completion_filter, include_archived=include_archived, limit=limit)
    if not rows:
        print("No stable-loop follow-up completion records found.")
        return
    for row in rows:
        print(
            f"{row.get('id')} | {row.get('completion_status_label')} | {row.get('final_decision_label')} | "
            f"tasks={row.get('task_count')} open={row.get('open_task_count')} archived={row.get('archived')} | "
            f"next={row.get('recommended_action')}"
        )


def print_mark_stable_loop_followup_closed(loop_id: str, note: str = "", archive: bool = False, full: bool = False) -> None:
    result = mark_stable_loop_followup_chain_closed(loop_id, note=note, reviewer="cli", archive=archive)
    print(stable_loop_followup_closure_text(result, full=full))


def print_cleanup_stable_loop_followup_completions(completion_filter: str = "cleanup_default", limit: int = 25, dry_run: bool = True, include_archived: bool = False, full: bool = False) -> None:
    result = cleanup_stable_loop_followup_completions(
        completion_filter=completion_filter,
        limit=limit,
        dry_run=dry_run,
        include_archived=include_archived,
        reviewer="cli",
    )
    print(stable_loop_followup_completion_cleanup_text(result, full=full))
