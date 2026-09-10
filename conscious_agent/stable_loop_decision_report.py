from __future__ import annotations

from release_metadata import RUNTIME_VERSION

"""Decision-aware reporting and cleanup for stable-loop records.

v6.7 note:
    v6.4 saved operator checklist/final-decision data. v6.5 turns those
    decisions into searchable/reportable history and cleanup candidates so the
    stable-loop archive can answer "what did we keep, fix, rollback, or leave
    unresolved?" without making the operator spelunk JSON by candlelight.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from stable_supervised_loop import list_stable_loops, load_stable_loop
from stable_loop_review import (
    REVIEW_STATUS_LABELS,
    loop_is_archived,
    review_status_for_loop,
    set_stable_loop_archived,
)
from stable_loop_operator_notes import (
    FINAL_DECISION_LABELS,
    VALID_FINAL_DECISIONS,
    ensure_operator_notes,
    normalize_final_decision,
)

DECISION_REPORT_VERSION = RUNTIME_VERSION
DECISION_FILTER_LABELS = {
    "all": "All decisions",
    "open": "Open decisions",
    "undecided": "Undecided",
    "keep": "Keep",
    "fix_forward": "Fix forward",
    "rollback": "Rollback",
    "needs_review": "Needs review",
    "action_required": "Action required",
    "decided": "Decided",
    "complete": "Checklist complete",
    "incomplete": "Checklist incomplete",
    "cleanup_default": "Cleanup candidates",
    "archived": "Archived",
}

ACTION_REQUIRED_DECISIONS = {"fix_forward", "rollback", "needs_review"}
CLEANUP_DECISIONS = {"keep", "rollback"}


@dataclass
class StableLoopDecisionCleanupResult:
    ok: bool
    dry_run: bool = True
    filter: str = "cleanup_default"
    filter_label: str = "Cleanup candidates"
    limit: int = 25
    include_live: bool = True
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


def normalize_decision_filter(value: str | None) -> str:
    token = str(value or "all").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "": "all",
        "any": "all",
        "pending": "undecided",
        "unresolved": "open",
        "todo": "action_required",
        "needs_action": "action_required",
        "requires_action": "action_required",
        "kept": "keep",
        "accepted": "keep",
        "fix": "fix_forward",
        "fixforward": "fix_forward",
        "revert": "rollback",
        "roll_back": "rollback",
        "review": "needs_review",
        "review_needed": "needs_review",
        "done": "decided",
        "closed": "decided",
        "checklist_done": "complete",
        "checklist_complete": "complete",
        "checklist_incomplete": "incomplete",
        "cleanup": "cleanup_default",
        "cleanup_candidates": "cleanup_default",
        "archive": "archived",
        "archives": "archived",
    }
    token = aliases.get(token, token)
    valid = set(DECISION_FILTER_LABELS) | set(VALID_FINAL_DECISIONS)
    return token if token in valid else "all"


def _notes(loop: dict[str, Any]) -> dict[str, Any]:
    # Build an in-memory normalized operator_notes structure. This does not save
    # unless callers explicitly use the operator-notes module themselves.
    return ensure_operator_notes(loop, save=False)


def _audit(loop: dict[str, Any]) -> dict[str, Any]:
    audit = loop.get("audit") if isinstance(loop.get("audit"), dict) else {}
    return audit


def final_decision_for_loop(loop: dict[str, Any] | None) -> str:
    if not loop:
        return "undecided"
    notes = loop.get("operator_notes") if isinstance(loop.get("operator_notes"), dict) else {}
    return normalize_final_decision(notes.get("final_decision"))


def decision_label(decision: str | None) -> str:
    normalized = normalize_final_decision(decision)
    return FINAL_DECISION_LABELS.get(normalized, normalized)


def stable_loop_decision_row(loop: dict[str, Any]) -> dict[str, Any]:
    notes = _notes(loop)
    summary = notes.get("summary") if isinstance(notes.get("summary"), dict) else {}
    audit = _audit(loop)
    decision = normalize_final_decision(notes.get("final_decision"))
    review_status = review_status_for_loop(loop)
    warnings = audit.get("warnings") if isinstance(audit.get("warnings"), list) else []
    rollback_notes = audit.get("rollback_notes") if isinstance(audit.get("rollback_notes"), list) else []
    complete = bool(summary.get("complete"))
    required_pending = int(summary.get("required_pending") or 0)
    next_action = recommended_decision_action(decision, complete=complete, required_pending=required_pending, archived=loop_is_archived(loop))
    return {
        "id": loop.get("id", ""),
        "version": loop.get("version", ""),
        "created_at": loop.get("created_at", ""),
        "project_id": loop.get("project_id", ""),
        "ok": bool(loop.get("ok")),
        "live": bool(loop.get("live")),
        "review_status": review_status,
        "review_label": REVIEW_STATUS_LABELS.get(review_status, review_status),
        "archived": loop_is_archived(loop),
        "final_decision": decision,
        "final_decision_label": decision_label(decision),
        "decision_note": notes.get("decision_note", ""),
        "decision_at": notes.get("decision_at", ""),
        "decision_by": notes.get("decision_by", ""),
        "check_total": int(summary.get("check_total") or 0),
        "check_done": int(summary.get("check_done") or 0),
        "check_pending": int(summary.get("check_pending") or 0),
        "required_pending": required_pending,
        "complete": complete,
        "ready_for_keep_decision": bool(summary.get("ready_for_keep_decision")),
        "audit_warning_count": len(warnings),
        "rollback_note_count": len(rollback_notes),
        "preview_cycle_id": loop.get("preview_cycle_id", ""),
        "live_cycle_id": loop.get("live_cycle_id", ""),
        "stopped_reason": loop.get("stopped_reason", ""),
        "recommended_action": next_action,
    }


def recommended_decision_action(decision: str, complete: bool = False, required_pending: int = 0, archived: bool = False) -> str:
    decision = normalize_final_decision(decision)
    if archived:
        return "Archived. Restore only if this record needs inspection again."
    if decision == "undecided":
        if required_pending:
            return "Complete required post-run checks, then set a final decision."
        return "Set a final decision: keep, fix_forward, rollback, or needs_review."
    if decision == "keep":
        return "Archive when no longer needed in active history." if complete else "Finish checklist, then archive if the result is stable."
    if decision == "fix_forward":
        return "Create or inspect follow-up tasks for the fix-forward work."
    if decision == "rollback":
        return "Review rollback notes and dry-run rollback commands before live rollback."
    if decision == "needs_review":
        return "Add operator notes or finish checklist before choosing keep/fix/rollback."
    return "Review this stable-loop decision."


def stable_loop_matches_decision_filter(
    loop: dict[str, Any],
    decision_filter: str | None = "all",
    include_archived: bool = False,
    include_live: bool = True,
) -> bool:
    archived = loop_is_archived(loop)
    token = normalize_decision_filter(decision_filter)
    if token == "archived":
        return archived
    if archived and not include_archived:
        return False
    if not include_live and bool(loop.get("live")):
        return False

    row = stable_loop_decision_row(loop)
    decision = row["final_decision"]
    complete = bool(row["complete"])
    required_pending = int(row["required_pending"] or 0)

    if token == "all":
        return True
    if token == "open":
        return decision == "undecided" or required_pending > 0 or decision in ACTION_REQUIRED_DECISIONS
    if token == "action_required":
        return decision in ACTION_REQUIRED_DECISIONS
    if token == "decided":
        return decision != "undecided"
    if token == "complete":
        return complete
    if token == "incomplete":
        return not complete
    if token == "cleanup_default":
        # Cleanup should not require every optional audit/rollback check to be
        # marked done. Required checks plus a terminal keep/rollback decision are
        # enough to archive from active history without deleting the record.
        return decision in CLEANUP_DECISIONS and required_pending == 0
    if token in VALID_FINAL_DECISIONS:
        return decision == token
    return True


def list_stable_loop_decision_rows(
    decision_filter: str | None = "all",
    include_archived: bool = False,
    include_live: bool = True,
    limit: int = 50,
) -> list[dict[str, Any]]:
    token = normalize_decision_filter(decision_filter)
    rows = [
        stable_loop_decision_row(loop)
        for loop in list_stable_loops()
        if stable_loop_matches_decision_filter(
            loop,
            token,
            include_archived=include_archived or token == "archived",
            include_live=include_live,
        )
    ]
    if limit and limit > 0:
        rows = rows[: max(1, min(int(limit), 500))]
    return rows


def stable_loop_decision_summary(
    decision_filter: str | None = "all",
    include_archived: bool = False,
    include_live: bool = True,
) -> dict[str, Any]:
    loops = list_stable_loops()
    visible_rows = [
        stable_loop_decision_row(loop)
        for loop in loops
        if (include_archived or not loop_is_archived(loop)) and (include_live or not bool(loop.get("live")))
    ]
    filtered_rows = list_stable_loop_decision_rows(
        decision_filter=decision_filter,
        include_archived=include_archived,
        include_live=include_live,
        limit=0,
    )
    counts = {decision: 0 for decision in sorted(VALID_FINAL_DECISIONS)}
    archived_count = 0
    for loop in loops:
        if loop_is_archived(loop):
            archived_count += 1
            if not include_archived:
                continue
        if not include_live and bool(loop.get("live")):
            continue
        decision = final_decision_for_loop(loop)
        counts[decision] = counts.get(decision, 0) + 1

    token = normalize_decision_filter(decision_filter)
    filter_tokens = [
        "all",
        "open",
        "undecided",
        "keep",
        "fix_forward",
        "rollback",
        "needs_review",
        "action_required",
        "decided",
        "complete",
        "incomplete",
        "cleanup_default",
        "archived",
    ]
    filter_counts = {
        item: len(list_stable_loop_decision_rows(item, include_archived=include_archived, include_live=include_live, limit=0))
        for item in filter_tokens
    }
    return {
        "version": DECISION_REPORT_VERSION,
        "generated_at": _now(),
        "selected_filter": token,
        "selected_filter_label": DECISION_FILTER_LABELS.get(token, token),
        "include_archived": include_archived,
        "include_live": include_live,
        "total": len(visible_rows),
        "total_including_archived": len(loops),
        "filtered_count": len(filtered_rows),
        "archived_count": archived_count,
        "counts": counts,
        "undecided_count": counts.get("undecided", 0),
        "keep_count": counts.get("keep", 0),
        "fix_forward_count": counts.get("fix_forward", 0),
        "rollback_count": counts.get("rollback", 0),
        "needs_review_count": counts.get("needs_review", 0),
        "action_required_count": filter_counts.get("action_required", 0),
        "cleanup_candidate_count": filter_counts.get("cleanup_default", 0),
        "filter_counts": filter_counts,
        "filtered_ids": [str(row.get("id", "")) for row in filtered_rows[:50]],
        "rows": filtered_rows[:50],
    }


def cleanup_stable_loop_decision_history(
    decision_filter: str | None = "cleanup_default",
    limit: int = 25,
    dry_run: bool = True,
    include_live: bool = True,
    reviewer: str = "operator",
) -> StableLoopDecisionCleanupResult:
    token = normalize_decision_filter(decision_filter or "cleanup_default")
    candidates = []
    for loop in list_stable_loops():
        if loop_is_archived(loop):
            continue
        if not include_live and bool(loop.get("live")):
            continue
        if stable_loop_matches_decision_filter(loop, token, include_archived=False, include_live=include_live):
            candidates.append(loop)
    limit_value = max(1, min(int(limit or 25), 500))
    selected = candidates[:limit_value]
    archived_ids: list[str] = []
    if not dry_run:
        for loop in selected:
            loop_id = str(loop.get("id", ""))
            if not loop_id:
                continue
            result = set_stable_loop_archived(
                loop_id,
                archived=True,
                note=f"Archived by stable-loop decision cleanup filter: {token}.",
                reviewer=reviewer,
            )
            if result.ok:
                archived_ids.append(result.loop_id)
    return StableLoopDecisionCleanupResult(
        ok=True,
        dry_run=dry_run,
        filter=token,
        filter_label=DECISION_FILTER_LABELS.get(token, token),
        limit=limit_value,
        include_live=include_live,
        candidate_count=len(candidates),
        selected_count=len(selected),
        selected_ids=[str(loop.get("id", "")) for loop in selected],
        archived_ids=archived_ids,
        message=(
            f"Dry-run found {len(selected)} stable-loop decision record(s) to archive."
            if dry_run else f"Archived {len(archived_ids)} stable-loop decision record(s)."
        ),
    )


def stable_loop_decision_report_text(data: dict[str, Any] | None = None, full: bool = False) -> str:
    report = data or stable_loop_decision_summary()
    lines = [
        "# Stable loop decision report",
        "",
        f"Version: {report.get('version', DECISION_REPORT_VERSION)}",
        f"Generated: {report.get('generated_at', '')}",
        f"Filter: {report.get('selected_filter_label', report.get('selected_filter', 'all'))}",
        f"Visible records: {report.get('total', 0)}",
        f"Filtered records: {report.get('filtered_count', 0)}",
        f"Archived records: {report.get('archived_count', 0)}",
        "",
        "## Decision counts",
    ]
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    for decision in ["undecided", "keep", "fix_forward", "rollback", "needs_review"]:
        lines.append(f"- {decision_label(decision)}: {counts.get(decision, 0)}")
    lines.extend([
        "",
        f"Action required: {report.get('action_required_count', 0)}",
        f"Cleanup candidates: {report.get('cleanup_candidate_count', 0)}",
    ])
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    if rows:
        lines.extend(["", "## Matching records"])
        for row in rows[:25]:
            lines.append(
                f"- {row.get('id')} | {row.get('final_decision_label')} | "
                f"live={row.get('live')} | checks={row.get('check_done')}/{row.get('check_total')} | "
                f"action={row.get('recommended_action')}"
            )
    if full:
        import json

        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def cleanup_result_text(result: StableLoopDecisionCleanupResult | dict[str, Any], full: bool = False) -> str:
    data = result.to_dict() if isinstance(result, StableLoopDecisionCleanupResult) else result
    lines = [
        "# Stable loop decision cleanup",
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
        lines.append("Selected IDs:")
        lines.extend(f"- {item}" for item in data.get("selected_ids") or [])
    if data.get("archived_ids"):
        lines.append("Archived IDs:")
        lines.extend(f"- {item}" for item in data.get("archived_ids") or [])
    if full:
        import json

        lines.extend(["", "## Raw cleanup result", json.dumps(data, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stable_loop_decision_report(
    decision_filter: str = "all",
    include_archived: bool = False,
    include_live: bool = True,
    full: bool = False,
) -> None:
    report = stable_loop_decision_summary(
        decision_filter=decision_filter,
        include_archived=include_archived,
        include_live=include_live,
    )
    print(stable_loop_decision_report_text(report, full=full))


def print_stable_loop_decision_rows(
    decision_filter: str = "all",
    include_archived: bool = False,
    include_live: bool = True,
    limit: int = 50,
) -> None:
    rows = list_stable_loop_decision_rows(
        decision_filter=decision_filter,
        include_archived=include_archived,
        include_live=include_live,
        limit=limit,
    )
    if not rows:
        print("No stable-loop decision records found.")
        return
    for row in rows:
        print(
            f"{row.get('id')} | {row.get('final_decision_label')} | live={row.get('live')} | "
            f"checks={row.get('check_done')}/{row.get('check_total')} | archived={row.get('archived')} | "
            f"action={row.get('recommended_action')}"
        )


def print_cleanup_stable_loop_decisions(
    decision_filter: str = "cleanup_default",
    limit: int = 25,
    dry_run: bool = True,
    include_live: bool = True,
    full: bool = False,
) -> None:
    result = cleanup_stable_loop_decision_history(
        decision_filter=decision_filter,
        limit=limit,
        dry_run=dry_run,
        include_live=include_live,
    )
    print(cleanup_result_text(result, full=full))
