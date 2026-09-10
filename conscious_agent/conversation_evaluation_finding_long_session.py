from __future__ import annotations

"""Bounded v1089.8 long-session windows for evaluation findings.

The window is assembled only from redacted finding summaries. It never returns
private finding content, reproduction notes, environment labels, repair
reference values, transcripts, prompts, memories, or provider payloads.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_evaluation_finding import (
    MAX_FINDINGS_RETURNED,
    finding_public_summary,
    iter_evaluation_findings_private,
)

FINDING_LONG_SESSION_SCHEMA_VERSION = "1"
INITIAL_FINDING_WINDOW = 80
EARLIER_FINDING_WINDOW = 120
MAX_LONG_SESSION_FINDINGS = MAX_FINDINGS_RETURNED


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _bounded_nonnegative(value: int | str | None, *, default: int = 0) -> int:
    try:
        number = int(value if value is not None else default)
    except (TypeError, ValueError):
        number = default
    return max(0, min(MAX_LONG_SESSION_FINDINGS, number))


def _matching_rows(*, campaign_id: str, evaluation_id: str, state: str) -> list[dict[str, Any]]:
    campaign = str(campaign_id or "").strip()
    evaluation = str(evaluation_id or "").strip()
    state_token = str(state or "").strip().lower()
    rows: list[dict[str, Any]] = []
    for record in iter_evaluation_findings_private() or ():
        if campaign and str(record.get("campaign_id") or "") != campaign:
            continue
        if evaluation and str(record.get("evaluation_id") or "") != evaluation:
            continue
        if state_token and str(record.get("state") or "") != state_token:
            continue
        rows.append(finding_public_summary(record))
    rows.sort(
        key=lambda row: (str(row.get("updated_at") or ""), str(row.get("finding_id") or "")),
        reverse=True,
    )
    return rows[:MAX_LONG_SESSION_FINDINGS]


def build_evaluation_finding_window(
    *,
    campaign_id: str = "",
    evaluation_id: str = "",
    state: str = "",
    offset: int = 0,
    limit: int | None = None,
) -> dict[str, Any]:
    bounded_offset = _bounded_nonnegative(offset)
    default_limit = INITIAL_FINDING_WINDOW if bounded_offset == 0 else EARLIER_FINDING_WINDOW
    requested_limit = _bounded_nonnegative(limit, default=default_limit) if limit is not None else default_limit
    maximum_for_window = INITIAL_FINDING_WINDOW if bounded_offset == 0 else EARLIER_FINDING_WINDOW
    bounded_limit = max(1, min(maximum_for_window, requested_limit or default_limit))
    rows = _matching_rows(campaign_id=campaign_id, evaluation_id=evaluation_id, state=state)
    page = rows[bounded_offset : bounded_offset + bounded_limit]
    next_offset = bounded_offset + len(page)
    has_more = next_offset < len(rows)
    stable = {
        "campaign_id_filter": str(campaign_id or "").strip(),
        "evaluation_id_filter": str(evaluation_id or "").strip(),
        "state_filter": str(state or "").strip().lower(),
        "total_matching_findings": len(rows),
        "offset": bounded_offset,
        "limit": bounded_limit,
        "returned_count": len(page),
        "next_offset": next_offset,
        "has_more": has_more,
        "findings": page,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_evaluation_finding_long_session_window",
        "schema_version": FINDING_LONG_SESSION_SCHEMA_VERSION,
        **stable,
        "initial_window_limit": INITIAL_FINDING_WINDOW,
        "earlier_window_limit": EARLIER_FINDING_WINDOW,
        "maximum_findings": MAX_LONG_SESSION_FINDINGS,
        "window_kind": "initial" if bounded_offset == 0 else "earlier",
        "window_digest": _digest(stable),
        "stable_ordering": "updated_at_desc_finding_id_desc",
        "complete_finding_rows_only": True,
        "private_finding_content_returned": False,
        "private_notes_returned": False,
        "private_environment_labels_returned": False,
        "private_reference_values_returned": False,
        "transcript_inspected": False,
        "prompt_inspected": False,
        "memory_inspected": False,
        "provider_invoked": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
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


def finding_window_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_title",
        "private_details",
        "finding_title",
        "finding_details",
        "private_note",
        "note",
        "notes",
        "environment_label",
        "private_environment_label",
        "reference_value",
        "private_reference_value",
        "content",
        "text",
        "message",
        "messages",
        "transcript",
        "prompt",
        "provider_payload",
        "credentials",
        "vectors",
        "embedding",
        "hidden_reasoning",
        "chain_of_thought",
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
