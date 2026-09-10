from __future__ import annotations

"""v1090.8 bounded long-session windows for registered repair candidates.

Rows are assembled only from redacted candidate registration summaries stored
inside private finding records. The window never returns candidate labels,
references, review notes, verification notes, lineage notes, transcripts,
prompts, provider payloads, credentials, vectors, or hidden reasoning.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_evaluation_finding import iter_evaluation_findings_private
from repair_candidate_registration import build_repair_candidate_registrations

REPAIR_CANDIDATE_LONG_SESSION_SCHEMA_VERSION = "1"
INITIAL_CANDIDATE_WINDOW = 80
EARLIER_CANDIDATE_WINDOW = 120
MAX_LONG_SESSION_CANDIDATES = 512


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _bounded_nonnegative(value: int | str | None, *, default: int = 0) -> int:
    try:
        result = int(value if value is not None else default)
    except (TypeError, ValueError):
        result = default
    return max(0, min(MAX_LONG_SESSION_CANDIDATES, result))


def _candidate_rows(*, finding_id: str, candidate_kind: str, review_state: str) -> list[dict[str, Any]]:
    finding_token = str(finding_id or "").strip()
    kind_token = str(candidate_kind or "").strip().lower()
    state_token = str(review_state or "").strip().lower()
    rows: list[dict[str, Any]] = []
    for finding in iter_evaluation_findings_private() or ():
        current_finding_id = str(finding.get("finding_id") or "")
        if finding_token and current_finding_id != finding_token:
            continue
        registrations = build_repair_candidate_registrations(current_finding_id)
        for candidate in list(registrations.get("candidates") or ()):
            if not isinstance(candidate, Mapping):
                continue
            if kind_token and str(candidate.get("candidate_kind") or "") != kind_token:
                continue
            if state_token and str(candidate.get("review_state") or "") != state_token:
                continue
            rows.append({
                "finding_id": current_finding_id,
                "finding_revision": max(0, int(registrations.get("finding_revision") or 0)),
                "candidate_id": str(candidate.get("candidate_id") or ""),
                "candidate_kind": str(candidate.get("candidate_kind") or ""),
                "artifact_sha256": str(candidate.get("artifact_sha256") or ""),
                "source_manifest_sha256": str(candidate.get("source_manifest_sha256") or ""),
                "evidence_digest": str(candidate.get("evidence_digest") or ""),
                "review_state": str(candidate.get("review_state") or "registered"),
                "registered_at": str(candidate.get("registered_at") or ""),
                "updated_at": str(candidate.get("updated_at") or ""),
                "reproducibility_status_at_registration": str(candidate.get("reproducibility_status_at_registration") or "not_reviewed"),
                "review_event_count": max(0, int(candidate.get("review_event_count") or 0)),
                "review_events_digest": str(candidate.get("review_events_digest") or ""),
                "private_label_present": bool(candidate.get("private_label_present")),
                "private_label_digest": str(candidate.get("private_label_digest") or ""),
                "private_reference_present": bool(candidate.get("private_reference_present")),
                "private_reference_digest": str(candidate.get("private_reference_digest") or ""),
            })
    rows.sort(
        key=lambda row: (
            str(row.get("updated_at") or ""),
            str(row.get("candidate_id") or ""),
            str(row.get("finding_id") or ""),
        ),
        reverse=True,
    )
    return rows[:MAX_LONG_SESSION_CANDIDATES]


def build_repair_candidate_window(
    *,
    finding_id: str = "",
    candidate_kind: str = "",
    review_state: str = "",
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    bounded_offset = _bounded_nonnegative(offset)
    default_limit = INITIAL_CANDIDATE_WINDOW if bounded_offset == 0 else EARLIER_CANDIDATE_WINDOW
    requested_limit = _bounded_nonnegative(limit, default=default_limit) if limit is not None else default_limit
    maximum_for_page = INITIAL_CANDIDATE_WINDOW if bounded_offset == 0 else EARLIER_CANDIDATE_WINDOW
    bounded_limit = max(1, min(maximum_for_page, requested_limit or default_limit))
    rows = _candidate_rows(
        finding_id=finding_id,
        candidate_kind=candidate_kind,
        review_state=review_state,
    )
    page = rows[bounded_offset : bounded_offset + bounded_limit]
    next_offset = bounded_offset + len(page)
    has_more = next_offset < len(rows)
    stable = {
        "finding_id_filter": str(finding_id or "").strip(),
        "candidate_kind_filter": str(candidate_kind or "").strip().lower(),
        "review_state_filter": str(review_state or "").strip().lower(),
        "total_matching_candidates": len(rows),
        "offset": bounded_offset,
        "limit": bounded_limit,
        "returned_count": len(page),
        "next_offset": next_offset,
        "has_more": has_more,
        "candidates": page,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_long_session_window",
        "schema_version": REPAIR_CANDIDATE_LONG_SESSION_SCHEMA_VERSION,
        **stable,
        "initial_window_limit": INITIAL_CANDIDATE_WINDOW,
        "earlier_window_limit": EARLIER_CANDIDATE_WINDOW,
        "maximum_candidates": MAX_LONG_SESSION_CANDIDATES,
        "window_kind": "initial" if bounded_offset == 0 else "earlier",
        "window_digest": _digest(stable),
        "stable_ordering": "updated_at_desc_candidate_id_desc_finding_id_desc",
        "complete_candidate_rows_only": True,
        "private_labels_returned": False,
        "private_references_returned": False,
        "private_review_notes_returned": False,
        "private_verification_notes_returned": False,
        "private_lineage_notes_returned": False,
        "transcript_inspected": False,
        "prompt_inspected": False,
        "memory_inspected": False,
        "provider_invoked": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
        "candidate_ranked": False,
        "winner_selected": False,
        "patch_generated": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def repair_candidate_window_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_label", "private_reference", "private_note", "note", "notes", "content", "text",
        "transcript", "prompt", "provider_payload", "credentials", "vectors", "embedding",
        "hidden_reasoning", "chain_of_thought",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
