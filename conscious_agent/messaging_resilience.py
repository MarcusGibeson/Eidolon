from __future__ import annotations

"""Content-free recovery, ownership, and soak evidence for reliable messaging.

These helpers never read message text, call a provider, change a draft, or grant
release authority. They summarize already-persisted operation and coordination
truth for the v1103.6-v1103.8 product surfaces.
"""

from typing import Any, Iterable

SCHEMA_VERSION = "1"
_TERMINAL = {"completed", "failed", "cancelled", "uncertain"}


def _bounded(value: Any, *, maximum: int = 1_000_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 0
    return max(0, min(maximum, parsed))


def build_operation_reconciliation(
    marker: dict[str, Any] | None,
    *,
    runtime_active: bool = False,
    session_turn_present: bool = False,
    resend_lineage_present: bool = False,
) -> dict[str, Any]:
    row = dict(marker or {})
    state = str(row.get("public_state") or "uncertain").strip().lower()
    if state not in {"running", *_TERMINAL}:
        state = "uncertain"
    cancellation_requested = bool(row.get("cancellation_requested"))
    late_ignored = _bounded(row.get("late_result_ignored_count"), maximum=10_000)
    retry_of = str(row.get("retry_of_operation_id") or "")
    retry_child = str(row.get("explicit_retry_operation_id") or "")
    terminal = state in _TERMINAL
    if state == "running" and not runtime_active:
        status = "runtime_uncertain"
    elif state == "running" and cancellation_requested:
        status = "cancelling"
    elif terminal and late_ignored:
        status = "late_result_ignored"
    elif retry_child:
        status = "retry_linked"
    else:
        status = state
    explicit_retry_allowed = terminal and state in {"failed", "cancelled", "uncertain"} and not retry_child
    return {
        "type": "message_operation_reconciliation",
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "public_state": state,
        "terminal": terminal,
        "runtime_active": bool(runtime_active),
        "cancellation_requested": cancellation_requested,
        "cancellation_won": state == "cancelled",
        "completion_won_before_cancellation": cancellation_requested and state == "completed",
        "late_result_ignored_count": late_ignored,
        "terminal_truth_preserved": terminal and late_ignored >= 0,
        "session_turn_present": bool(session_turn_present),
        "explicit_retry_allowed": explicit_retry_allowed,
        "explicit_retry_required": explicit_retry_allowed,
        "automatic_retry_allowed": False,
        "retry_of_operation_id": retry_of,
        "explicit_retry_operation_id": retry_child,
        "resend_lineage_present": bool(resend_lineage_present),
        "content_free": True,
        "contains_message_text": False,
        "contains_response_text": False,
        "provider_payload_included": False,
    }


def build_tab_recovery_state(coordination: dict[str, Any] | None) -> dict[str, Any]:
    row = dict(coordination or {})
    status = str(row.get("status") or "snapshot")
    owner_present = bool(row.get("owner_present"))
    is_owner = bool(row.get("is_owner"))
    renew = bool(row.get("renew_tab_id"))
    expired = status == "ownership_expired" or not owner_present
    if renew or status == "identity_conflict":
        recovery = "renew_identity"
    elif is_owner:
        recovery = "owner"
    elif expired:
        recovery = "take_control_available"
    else:
        recovery = "following"
    return {
        "type": "message_tab_recovery_state",
        "schema_version": SCHEMA_VERSION,
        "status": recovery,
        "owner_present": owner_present,
        "is_owner": is_owner,
        "renew_tab_identity": renew or status == "identity_conflict",
        "take_control_available": recovery == "take_control_available",
        "explicit_transfer_required": recovery == "following",
        "automatic_takeover": False,
        "stale_tab_may_send": is_owner,
        "content_free": True,
        "contains_draft_text": False,
        "contains_conversation_content": False,
    }


def build_long_session_soak_report(
    *,
    iterations: Any,
    accepted_operations: Any,
    provider_requests: Any,
    duplicate_submissions: Any = 0,
    cancellations: Any = 0,
    explicit_retries: Any = 0,
    automatic_retries: Any = 0,
    late_results_ignored: Any = 0,
    ownership_transfers: Any = 0,
    stale_mutations_rejected: Any = 0,
    continuity_digest_count: Any = 1,
    source_mutations: Any = 0,
    failures: Iterable[str] = (),
) -> dict[str, Any]:
    total = _bounded(iterations, maximum=100_000)
    accepted = _bounded(accepted_operations, maximum=100_000)
    requests = _bounded(provider_requests, maximum=100_000)
    duplicates = _bounded(duplicate_submissions, maximum=100_000)
    auto_retries = _bounded(automatic_retries, maximum=100_000)
    digests = _bounded(continuity_digest_count, maximum=100_000)
    mutations = _bounded(source_mutations, maximum=100_000)
    failure_codes = sorted({str(item)[:80] for item in failures if str(item).strip()})
    passed = (
        total >= 1
        and accepted == total
        and requests <= accepted
        and auto_retries == 0
        and digests == 1
        and mutations == 0
        and not failure_codes
    )
    return {
        "type": "message_long_session_soak",
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if passed else "blocked",
        "passed": passed,
        "iterations": total,
        "accepted_operations": accepted,
        "provider_requests": requests,
        "duplicate_submissions": duplicates,
        "cancellations": _bounded(cancellations),
        "explicit_retries": _bounded(explicit_retries),
        "automatic_retries": auto_retries,
        "late_results_ignored": _bounded(late_results_ignored),
        "ownership_transfers": _bounded(ownership_transfers),
        "stale_mutations_rejected": _bounded(stale_mutations_rejected),
        "continuity_digest_count": digests,
        "source_mutations": mutations,
        "failure_codes": failure_codes,
        "exactly_once_preserved": accepted == total and requests <= accepted,
        "automatic_replay": False,
        "content_free": True,
        "contains_message_text": False,
        "contains_response_text": False,
        "private_paths_included": False,
        "provider_payload_included": False,
    }
