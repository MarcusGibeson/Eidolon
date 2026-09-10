from __future__ import annotations

"""Review helpers for stable supervised loop records.

v6.2 note:
    Stable loop records are operator review artifacts. This module keeps review
    state in the saved stable-loop JSON instead of adding yet another storage
    pile for future archaeology goblins.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from stable_supervised_loop import load_stable_loop, save_stable_loop, run_stable_supervised_loop, list_stable_loops


VALID_REVIEW_STATUSES = {
    "unreviewed",
    "reviewed",
    "approved_for_live",
    "rejected",
    "superseded",
}

REVIEW_STATUS_LABELS = {
    "unreviewed": "Unreviewed",
    "reviewed": "Reviewed",
    "approved_for_live": "Approved for live",
    "rejected": "Rejected",
    "superseded": "Superseded",
}


@dataclass
class StableLoopReviewResult:
    ok: bool
    loop_id: str = ""
    review_status: str = "unreviewed"
    message: str = ""
    error: str = ""
    loop: dict[str, Any] | None = None
    live_loop_id: str = ""
    live_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_review_status(status: str | None) -> str:
    token = str(status or "unreviewed").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "approve": "approved_for_live",
        "approved": "approved_for_live",
        "approved_live": "approved_for_live",
        "live_approved": "approved_for_live",
        "needs_changes": "rejected",
        "reject": "rejected",
        "not_ok": "rejected",
        "done": "reviewed",
        "mark_reviewed": "reviewed",
    }
    token = aliases.get(token, token)
    return token if token in VALID_REVIEW_STATUSES else "unreviewed"


def _ensure_review(loop: dict[str, Any]) -> dict[str, Any]:
    review = loop.get("review")
    if not isinstance(review, dict):
        review = {}
    review.setdefault("status", "unreviewed")
    review.setdefault("notes", [])
    review.setdefault("updated_at", "")
    review.setdefault("reviewed_by", "")
    loop["review"] = review
    return review


def review_status_for_loop(loop: dict[str, Any] | None) -> str:
    if not loop:
        return "unreviewed"
    review = loop.get("review") if isinstance(loop.get("review"), dict) else {}
    return normalize_review_status(review.get("status"))


def review_label_for_loop(loop: dict[str, Any] | None) -> str:
    return REVIEW_STATUS_LABELS.get(review_status_for_loop(loop), "Unreviewed")


def loop_is_live_ready(loop: dict[str, Any] | None) -> bool:
    if not loop:
        return False
    return (
        bool(loop.get("ok"))
        and not bool(loop.get("live"))
        and bool(loop.get("preview_cycle_id"))
        and review_status_for_loop(loop) == "approved_for_live"
    )


def update_stable_loop_review(
    loop_id: str,
    status: str,
    note: str = "",
    reviewer: str = "operator",
) -> StableLoopReviewResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopReviewResult(ok=False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")

    normalized = normalize_review_status(status)
    review = _ensure_review(loop)
    now = _now()
    review["status"] = normalized
    review["updated_at"] = now
    review["reviewed_by"] = reviewer or "operator"
    if normalized == "reviewed":
        review["reviewed_at"] = now
    elif normalized == "approved_for_live":
        review["approved_at"] = now
    elif normalized == "rejected":
        review["rejected_at"] = now
    elif normalized == "superseded":
        review["superseded_at"] = now

    if note:
        notes = review.get("notes")
        if not isinstance(notes, list):
            notes = []
        notes.append({"at": now, "by": reviewer or "operator", "status": normalized, "note": note})
        review["notes"] = notes

    loop["review"] = review
    save_stable_loop(loop)
    return StableLoopReviewResult(
        ok=True,
        loop_id=str(loop.get("id", loop_id)),
        review_status=normalized,
        message=f"Stable loop {loop.get('id', loop_id)} marked {REVIEW_STATUS_LABELS.get(normalized, normalized)}.",
        loop=loop,
    )


REVIEW_FILTER_LABELS = {
    "all": "All",
    "open": "Open review queue",
    "unreviewed": "Unreviewed",
    "reviewed": "Reviewed",
    "approved_for_live": "Approved for live",
    "approved_ready": "Approved/live-ready",
    "rejected": "Rejected",
    "superseded": "Superseded",
    "archived": "Archived",
    "preview": "Preview runs",
    "live": "Live runs",
    "failed": "Attention / failed",
    "cleanup_default": "Cleanup candidates",
}


def _review(loop: dict[str, Any] | None) -> dict[str, Any]:
    if not loop:
        return {}
    return loop.get("review") if isinstance(loop.get("review"), dict) else {}


def loop_is_archived(loop: dict[str, Any] | None) -> bool:
    review = _review(loop)
    return bool(review.get("archived"))


def normalize_review_filter(value: str | None) -> str:
    token = str(value or "all").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "": "all",
        "any": "all",
        "pending": "unreviewed",
        "review_queue": "open",
        "needs_review": "unreviewed",
        "approved": "approved_for_live",
        "live_ready": "approved_ready",
        "ready_for_live": "approved_ready",
        "rejections": "rejected",
        "archive": "archived",
        "archives": "archived",
        "cleanup": "cleanup_default",
        "cleanup_candidates": "cleanup_default",
        "failed_preview": "failed",
        "attention": "failed",
    }
    token = aliases.get(token, token)
    valid = set(REVIEW_FILTER_LABELS) | VALID_REVIEW_STATUSES
    return token if token in valid else "all"


def stable_loop_matches_review_filter(
    loop: dict[str, Any],
    review_filter: str | None = "all",
    include_archived: bool = False,
) -> bool:
    if not include_archived and loop_is_archived(loop):
        return False

    token = normalize_review_filter(review_filter)
    status = review_status_for_loop(loop)

    if token == "all":
        return True
    if token == "archived":
        return loop_is_archived(loop)
    if token == "open":
        return status in {"unreviewed", "reviewed", "approved_for_live"} and not bool(loop.get("live"))
    if token == "approved_ready":
        return loop_is_live_ready(loop)
    if token == "preview":
        return not bool(loop.get("live"))
    if token == "live":
        return bool(loop.get("live"))
    if token == "failed":
        return not bool(loop.get("ok")) or str(loop.get("stopped_reason") or "").lower() in {"preflight_failed", "preview_failed"}
    if token == "cleanup_default":
        return status in {"superseded", "rejected"} or bool(loop.get("live"))
    if token in VALID_REVIEW_STATUSES:
        return status == token
    return True


def stable_loop_review_row(loop: dict[str, Any]) -> dict[str, Any]:
    review = _review(loop)
    status = review_status_for_loop(loop)
    return {
        "id": loop.get("id", ""),
        "version": loop.get("version", ""),
        "created_at": loop.get("created_at", ""),
        "project_id": loop.get("project_id", ""),
        "ok": bool(loop.get("ok")),
        "live": bool(loop.get("live")),
        "review_status": status,
        "review_label": REVIEW_STATUS_LABELS.get(status, status),
        "archived": loop_is_archived(loop),
        "archived_at": review.get("archived_at", ""),
        "live_ready": loop_is_live_ready(loop),
        "preview_cycle_id": loop.get("preview_cycle_id", ""),
        "live_cycle_id": loop.get("live_cycle_id", ""),
        "stopped_reason": loop.get("stopped_reason", ""),
        "message": loop.get("message", ""),
        "source_review_loop_id": review.get("source_review_loop_id", ""),
        "live_loop_id": review.get("live_loop_id", ""),
    }


def list_stable_loop_reviews(
    review_filter: str | None = "all",
    include_archived: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    token = normalize_review_filter(review_filter)
    rows = [
        stable_loop_review_row(loop)
        for loop in list_stable_loops()
        if stable_loop_matches_review_filter(loop, token, include_archived=include_archived or token == "archived")
    ]
    if limit and limit > 0:
        rows = rows[: max(1, min(int(limit), 500))]
    return rows


def stable_loop_review_summary(
    review_filter: str | None = "all",
    include_archived: bool = False,
) -> dict[str, Any]:
    loops = list_stable_loops()
    visible_loops = [loop for loop in loops if include_archived or not loop_is_archived(loop)]
    filtered_loops = [
        loop for loop in loops
        if stable_loop_matches_review_filter(loop, review_filter, include_archived=include_archived or normalize_review_filter(review_filter) == "archived")
    ]
    counts = {status: 0 for status in sorted(VALID_REVIEW_STATUSES)}
    unreviewed_preview_ids: list[str] = []
    approved_ready_ids: list[str] = []
    rejected_ids: list[str] = []
    archived_ids: list[str] = []

    for loop in loops:
        if loop_is_archived(loop):
            archived_ids.append(str(loop.get("id", "")))
            if not include_archived:
                continue
        status = review_status_for_loop(loop)
        counts[status] = counts.get(status, 0) + 1
        loop_id = str(loop.get("id", ""))
        if status == "unreviewed" and not loop.get("live"):
            unreviewed_preview_ids.append(loop_id)
        if loop_is_live_ready(loop):
            approved_ready_ids.append(loop_id)
        if status == "rejected":
            rejected_ids.append(loop_id)

    return {
        "total": len(visible_loops),
        "total_including_archived": len(loops),
        "archived_count": len(archived_ids),
        "selected_filter": normalize_review_filter(review_filter),
        "selected_filter_label": REVIEW_FILTER_LABELS.get(normalize_review_filter(review_filter), normalize_review_filter(review_filter)),
        "filtered_count": len(filtered_loops),
        "counts": counts,
        "unreviewed_preview_count": len(unreviewed_preview_ids),
        "approved_ready_count": len(approved_ready_ids),
        "rejected_count": len(rejected_ids),
        "unreviewed_preview_ids": unreviewed_preview_ids[:25],
        "approved_ready_ids": approved_ready_ids[:25],
        "rejected_ids": rejected_ids[:25],
        "archived_ids": archived_ids[:25],
        "filter_counts": {
            key: len(list_stable_loop_reviews(key, include_archived=include_archived, limit=0))
            for key in ["all", "open", "unreviewed", "reviewed", "approved_ready", "rejected", "superseded", "failed", "cleanup_default", "archived"]
        },
    }


def set_stable_loop_archived(
    loop_id: str,
    archived: bool = True,
    note: str = "",
    reviewer: str = "operator",
) -> StableLoopReviewResult:
    loop = load_stable_loop(loop_id)
    if not loop:
        return StableLoopReviewResult(ok=False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")

    review = _ensure_review(loop)
    now = _now()
    review["archived"] = bool(archived)
    review["updated_at"] = now
    review["archived_by" if archived else "restored_by"] = reviewer or "operator"
    if archived:
        review["archived_at"] = now
    else:
        review["restored_at"] = now
        review["archived_at"] = ""
    notes = review.get("notes") if isinstance(review.get("notes"), list) else []
    notes.append({
        "at": now,
        "by": reviewer or "operator",
        "status": review.get("status", "unreviewed"),
        "note": note or ("Archived stable loop history record." if archived else "Restored stable loop history record."),
    })
    review["notes"] = notes
    loop["review"] = review
    save_stable_loop(loop)
    return StableLoopReviewResult(
        ok=True,
        loop_id=str(loop.get("id", loop_id)),
        review_status=review_status_for_loop(loop),
        message=f"Stable loop {loop.get('id', loop_id)} {'archived' if archived else 'restored'}.",
        loop=loop,
    )


def cleanup_stable_loop_history(
    review_filter: str | None = "cleanup_default",
    limit: int = 25,
    dry_run: bool = True,
    include_live: bool = True,
    reviewer: str = "operator",
) -> dict[str, Any]:
    token = normalize_review_filter(review_filter or "cleanup_default")
    candidates: list[dict[str, Any]] = []
    for loop in list_stable_loops():
        if loop_is_archived(loop):
            continue
        if not include_live and bool(loop.get("live")):
            continue
        if stable_loop_matches_review_filter(loop, token, include_archived=False):
            candidates.append(loop)
    limit_value = max(1, min(int(limit or 25), 500))
    selected = candidates[:limit_value]
    archived_ids: list[str] = []
    if not dry_run:
        for loop in selected:
            result = set_stable_loop_archived(
                str(loop.get("id", "")),
                archived=True,
                note=f"Archived by stable-loop history cleanup filter: {token}.",
                reviewer=reviewer,
            )
            if result.ok:
                archived_ids.append(result.loop_id)
    return {
        "ok": True,
        "dry_run": dry_run,
        "filter": token,
        "filter_label": REVIEW_FILTER_LABELS.get(token, token),
        "limit": limit_value,
        "include_live": include_live,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "selected_ids": [str(loop.get("id", "")) for loop in selected],
        "archived_ids": archived_ids,
        "message": (
            f"Dry-run found {len(selected)} stable loop history record(s) to archive."
            if dry_run else f"Archived {len(archived_ids)} stable loop history record(s)."
        ),
    }


def run_approved_stable_loop_live(
    loop_id: str,
    use_ai: Optional[bool] = None,
    approve_work_execution: Optional[bool] = None,
    note: str = "",
) -> StableLoopReviewResult:
    source = load_stable_loop(loop_id)
    if not source:
        return StableLoopReviewResult(ok=False, loop_id=loop_id, error=f"Stable loop not found: {loop_id}")
    source_id = str(source.get("id", loop_id))
    if not loop_is_live_ready(source):
        status = review_status_for_loop(source)
        return StableLoopReviewResult(
            ok=False,
            loop_id=source_id,
            review_status=status,
            error="Stable loop must be an ok preview record marked approved_for_live before running live.",
            loop=source,
        )

    result = run_stable_supervised_loop(
        project_id=source.get("project_id") or "eidolon",
        max_steps=int(source.get("max_steps") or 1),
        live=True,
        use_ai=bool(source.get("use_ai")) if use_ai is None else bool(use_ai),
        approve_work_execution=bool(source.get("approve_work_execution")) if approve_work_execution is None else bool(approve_work_execution),
        seed_if_empty=bool(source.get("seed_if_empty", True)),
        auto_create_patch_followups=bool(source.get("auto_create_patch_followups", True)),
        auto_request_approvals=bool(source.get("auto_request_approvals", True)),
        auto_retry_recovery=bool(source.get("auto_retry_recovery", False)),
    )

    if not result.ok:
        updated_source = load_stable_loop(source_id) or source
        review = _ensure_review(updated_source)
        now = _now()
        review["updated_at"] = now
        notes = review.get("notes") if isinstance(review.get("notes"), list) else []
        notes.append({
            "at": now,
            "by": "stable_loop_review",
            "status": review.get("status", "approved_for_live"),
            "note": result.error or result.message or "Approved live run did not complete.",
        })
        review["notes"] = notes
        updated_source["review"] = review
        save_stable_loop(updated_source)
        return StableLoopReviewResult(
            ok=False,
            loop_id=source_id,
            review_status=str(review.get("status") or "approved_for_live"),
            message=result.message,
            loop=updated_source,
            live_loop_id=result.loop_id,
            live_result=result.to_dict(),
            error=result.error or "Approved live stable loop failed or was blocked.",
        )

    updated_source = load_stable_loop(source_id) or source
    review = _ensure_review(updated_source)
    now = _now()
    review["status"] = "superseded"
    review["updated_at"] = now
    review["superseded_at"] = now
    review["live_loop_id"] = result.loop_id
    notes = review.get("notes") if isinstance(review.get("notes"), list) else []
    notes.append({
        "at": now,
        "by": "stable_loop_review",
        "status": "superseded",
        "note": note or f"Live stable loop created from approved preview: {result.loop_id}",
    })
    review["notes"] = notes
    updated_source["review"] = review
    save_stable_loop(updated_source)

    live_loop = load_stable_loop(result.loop_id) or result.to_dict()
    live_review = _ensure_review(live_loop)
    live_review["source_review_loop_id"] = source_id
    live_review["status"] = "unreviewed"
    live_review["updated_at"] = now
    live_loop["review"] = live_review
    if isinstance(live_loop, dict) and live_loop.get("id"):
        save_stable_loop(live_loop)

    return StableLoopReviewResult(
        ok=result.ok,
        loop_id=source_id,
        review_status="superseded",
        message=f"Live stable loop created from approved preview: {result.loop_id}",
        loop=updated_source,
        live_loop_id=result.loop_id,
        live_result=result.to_dict(),
        error=result.error,
    )


def stable_loop_review_text(loop_or_result: dict[str, Any] | StableLoopReviewResult | None, full: bool = False) -> str:
    if isinstance(loop_or_result, StableLoopReviewResult):
        data = loop_or_result.to_dict()
        loop = data.get("loop") or {}
        status = data.get("review_status") or review_status_for_loop(loop)
        lines = [
            "# Stable loop review",
            "",
            f"OK: {data.get('ok')}",
            f"Loop: {data.get('loop_id')}",
            f"Review status: {REVIEW_STATUS_LABELS.get(status, status)}",
        ]
        if data.get("live_loop_id"):
            lines.append(f"Live loop: {data.get('live_loop_id')}")
        if data.get("message"):
            lines.append(f"Message: {data.get('message')}")
        if data.get("error"):
            lines.append(f"Error: {data.get('error')}")
        if full:
            lines.extend(["", "## Raw result", _json(data)])
        return "\n".join(lines).strip()

    loop = loop_or_result or {}
    status = review_status_for_loop(loop)
    review = loop.get("review") if isinstance(loop.get("review"), dict) else {}
    lines = [
        "# Stable loop review",
        "",
        f"Loop: {loop.get('id', '')}",
        f"Review status: {REVIEW_STATUS_LABELS.get(status, status)}",
        f"Live ready: {loop_is_live_ready(loop)}",
        f"Reviewed by: {review.get('reviewed_by', '')}",
        f"Updated: {review.get('updated_at', '')}",
        f"Live loop: {review.get('live_loop_id', '')}",
    ]
    notes = review.get("notes") if isinstance(review.get("notes"), list) else []
    if notes:
        lines.append("")
        lines.append("## Notes")
        for note in notes[-10:]:
            if isinstance(note, dict):
                lines.append(f"- {note.get('at', '')} [{note.get('status', '')}] {note.get('note', '')}")
            else:
                lines.append(f"- {note}")
    if full:
        lines.extend(["", "## Raw review", _json(review)])
    return "\n".join(lines).strip()


def _json(data: Any) -> str:
    import json

    return json.dumps(data, indent=2, default=str)



def print_stable_loop_reviews(review_filter: str = "all", include_archived: bool = False, limit: int = 50, full: bool = False) -> None:
    rows = list_stable_loop_reviews(review_filter=review_filter, include_archived=include_archived, limit=limit)
    if not rows:
        print("No stable loop review records found.")
        return
    for row in rows:
        print(
            f"{row.get('id')} | {row.get('review_label')} | live={row.get('live')} | "
            f"archived={row.get('archived')} | ok={row.get('ok')} | stopped={row.get('stopped_reason')}"
        )
        if full:
            print(_json(row))
            print("-" * 72)


def print_archive_stable_loop(loop_id: str, archived: bool = True, note: str = "", full: bool = False) -> None:
    result = set_stable_loop_archived(loop_id, archived=archived, note=note, reviewer="cli")
    print(stable_loop_review_text(result, full=full))


def print_cleanup_stable_loop_history(
    review_filter: str = "cleanup_default",
    limit: int = 25,
    dry_run: bool = True,
    include_live: bool = True,
    full: bool = False,
) -> None:
    result = cleanup_stable_loop_history(
        review_filter=review_filter,
        limit=limit,
        dry_run=dry_run,
        include_live=include_live,
        reviewer="cli",
    )
    print("# Stable loop history cleanup")
    print("")
    print(f"Dry run: {result.get('dry_run')}")
    print(f"Filter: {result.get('filter_label')} ({result.get('filter')})")
    print(f"Candidates: {result.get('candidate_count')}")
    print(f"Selected: {result.get('selected_count')}")
    print(f"Archived: {len(result.get('archived_ids') or [])}")
    print(f"Message: {result.get('message')}")
    if full:
        print("")
        print(_json(result))

def print_stable_loop_review_summary(full: bool = False) -> None:
    summary = stable_loop_review_summary()
    print("# Stable loop review summary")
    print("")
    print(f"Visible loops: {summary.get('total', 0)}")
    print(f"Archived loops: {summary.get('archived_count', 0)}")
    print(f"Unreviewed previews: {summary.get('unreviewed_preview_count', 0)}")
    print(f"Approved/live-ready: {summary.get('approved_ready_count', 0)}")
    print(f"Rejected: {summary.get('rejected_count', 0)}")
    print("Counts:")
    for status, count in sorted((summary.get("counts") or {}).items()):
        print(f"- {REVIEW_STATUS_LABELS.get(status, status)}: {count}")
    if full:
        print("")
        print(_json(summary))


def print_stable_loop_review(loop_id: str = "latest", full: bool = False) -> None:
    loop = load_stable_loop(loop_id)
    if not loop:
        print(f"Stable loop not found: {loop_id}")
        return
    print(stable_loop_review_text(loop, full=full))


def print_update_stable_loop_review(loop_id: str, status: str, note: str = "", full: bool = False) -> None:
    result = update_stable_loop_review(loop_id, status=status, note=note, reviewer="cli")
    print(stable_loop_review_text(result, full=full))


def print_run_approved_stable_loop_live(loop_id: str, note: str = "", full: bool = False) -> None:
    result = run_approved_stable_loop_live(loop_id, note=note)
    print(stable_loop_review_text(result, full=full))
