from __future__ import annotations

"""Bounded operator-facing action-history review and follow-through projection.

The caller supplies already-bounded, content-free lifecycle records. This module
never opens a proposal ledger, invokes an executor, retries work, or grants any
authority. Exact status references select one proposal; otherwise the projection
remains a bounded history summary.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1179.2"
MAX_HISTORY_RECORDS = 32
MAX_REVIEW_BYTES = 8192
STATUS_REFERENCE_RE = re.compile(r"^(?:show\s+)?status\s+(?:for\s+)?(?:action\s+)?([a-z0-9_-]{1,80})[.!?]*$", re.I)
KNOWN_STATES = frozenset({
    "proposed", "awaiting_approval", "approved", "rejected", "cancelled",
    "expired", "superseded", "execution_admitted", "execution_in_progress",
    "execution_succeeded", "execution_failed", "execution_cancelled",
    "execution_timed_out",
})
TERMINAL_STATES = frozenset({
    "rejected", "cancelled", "expired", "superseded", "execution_succeeded",
    "execution_failed", "execution_cancelled", "execution_timed_out",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _bounded_id(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text[:80] if re.fullmatch(r"[a-z0-9_-]{1,80}", text) else ""


def _normalize(item: Mapping[str, Any]) -> dict[str, Any] | None:
    proposal_id = _bounded_id(item.get("proposal_id"))
    capability_id = _bounded_id(item.get("capability_id"))
    state = str(item.get("state") or "")
    proposal_digest = _hex64(item.get("proposal_digest"))
    if not (proposal_id and capability_id and state in KNOWN_STATES and proposal_digest):
        return None
    row = {
        "proposal_id": proposal_id,
        "capability_id": capability_id,
        "state": state,
        "proposal_digest": proposal_digest,
        "approval_decision_digest": _hex64(item.get("approval_decision_digest")),
        "authorization_digest": _hex64(item.get("authorization_digest")),
        "execution_admission_digest": _hex64(item.get("execution_admission_digest")),
        "terminal_result_digest": _hex64(item.get("terminal_result_digest") or item.get("execution_result_digest")),
        "updated_at": max(0.0, float(item.get("updated_at") or item.get("recorded_at") or 0.0)),
        "content_free": item.get("content_free", True) is True,
    }
    if not row["content_free"]:
        return None
    row["status_reference"] = f"status action {proposal_id}"
    return row


def _next_governed_step(state: str) -> tuple[str, bool]:
    return {
        "proposed": ("request_explicit_operator_approval", True),
        "awaiting_approval": ("await_operator_approval_decision", False),
        "approved": ("request_separate_execution_authorization", True),
        "execution_admitted": ("invoke_separate_supervised_execution_surface", True),
        "execution_in_progress": ("await_authoritative_terminal_result_or_stale_recovery", False),
        "execution_succeeded": ("review_authoritative_result", False),
        "execution_failed": ("review_failure_before_new_governed_operation", False),
        "execution_cancelled": ("review_cancellation_before_new_governed_operation", False),
        "execution_timed_out": ("review_timeout_before_new_governed_operation", False),
        "rejected": ("no_follow_through_terminal_rejection", False),
        "cancelled": ("no_follow_through_terminal_cancellation", False),
        "expired": ("create_new_proposal_if_still_needed", True),
        "superseded": ("review_newer_proposal", False),
    }.get(state, ("no_follow_through_available", False))


def build_action_history_review(
    records: Iterable[Mapping[str, Any]] = (),
    *,
    status_reference: str = "",
) -> dict[str, Any]:
    """Build a bounded review from caller-supplied content-free lifecycle records."""
    normalized: list[dict[str, Any]] = []
    for item in records:
        if isinstance(item, Mapping):
            row = _normalize(item)
            if row:
                normalized.append(row)
    # Keep the newest row for each exact proposal id, then bound oldest-to-newest.
    by_id: dict[str, dict[str, Any]] = {}
    for row in sorted(normalized, key=lambda value: (value["updated_at"], value["proposal_id"])):
        by_id[row["proposal_id"]] = row
    history = sorted(by_id.values(), key=lambda value: (value["updated_at"], value["proposal_id"]))[-MAX_HISTORY_RECORDS:]

    match = STATUS_REFERENCE_RE.fullmatch(str(status_reference or "").strip())
    referenced_id = _bounded_id(match.group(1)) if match else ""
    selected = next((row for row in history if row["proposal_id"] == referenced_id), None) if referenced_id else None
    exact_reference = bool(match and selected)
    next_step, operator_action_available = _next_governed_step(selected["state"] if selected else "")

    counts: dict[str, int] = {}
    for row in history:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    public_history = [
        {
            "proposal_id": row["proposal_id"],
            "capability_id": row["capability_id"],
            "state": row["state"],
            "status_reference": row["status_reference"],
            "updated_at": row["updated_at"],
            "terminal": row["state"] in TERMINAL_STATES,
        }
        for row in history
    ]
    selected_status = None if not selected else {
        "proposal_id": selected["proposal_id"],
        "capability_id": selected["capability_id"],
        "state": selected["state"],
        "status_reference": selected["status_reference"],
        "proposal_digest": selected["proposal_digest"],
        "approval_decision_digest": selected["approval_decision_digest"],
        "authorization_digest": selected["authorization_digest"],
        "execution_admission_digest": selected["execution_admission_digest"],
        "terminal_result_digest": selected["terminal_result_digest"],
        "terminal": selected["state"] in TERMINAL_STATES,
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "review_status": "exact_status" if exact_reference else ("invalid_reference" if status_reference else "history"),
        "record_count": len(public_history),
        "state_counts": counts,
        "history": public_history,
        "exact_status_reference": exact_reference,
        "referenced_proposal_id": referenced_id,
        "selected_status": selected_status,
        "follow_through": {
            "next_governed_step": next_step,
            "operator_action_available": operator_action_available,
            "automatic_retry": False,
            "automatic_approval": False,
            "automatic_authorization": False,
            "execution_invoked": False,
        },
        "ledger_discovered": False,
        "ledger_path_accepted": False,
        "raw_content_included": False,
        "argument_values_included": False,
        "authority_granted": False,
        "execution_invoked": False,
        "content_free": True,
    }
    result["review_digest"] = _digest(result)
    if len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) > MAX_REVIEW_BYTES:
        raise ValueError("Action history review exceeded bounded size")
    return result


def action_history_review_prompt(review: Mapping[str, Any]) -> str:
    """Bounded operator-facing wording contract; never claims authority or execution."""
    selected = review.get("selected_status") if isinstance(review.get("selected_status"), Mapping) else None
    if selected:
        return (
            "Bounded action status review:\n"
            f"- Proposal: {selected.get('proposal_id')}.\n"
            f"- Registered capability: {selected.get('capability_id')}.\n"
            f"- Exact lifecycle state: {selected.get('state')}.\n"
            f"- Next governed step: {review.get('follow_through', {}).get('next_governed_step')}.\n"
            "- Do not claim retry, approval, authorization, execution, raw output, or hidden ledger access."
        )
    return (
        "Bounded action-history review:\n"
        f"- Available bounded records: {int(review.get('record_count') or 0)}.\n"
        "- Use an exact status reference shown in the review to inspect one proposal.\n"
        "- Do not infer a proposal from conversation or discover a private ledger."
    )
