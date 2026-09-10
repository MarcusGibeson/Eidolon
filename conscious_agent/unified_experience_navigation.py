from __future__ import annotations

"""v1190.3-v1190.5 operator navigation and coordinated experience transitions.

The contract changes only the operator's content-free focus and presentation. It
never changes subsystem state, consumes approval, executes action, or mutates
source/runtime records.
"""

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1190.5"
SCHEMA_VERSION = "1"
MAX_CONTRACT_BYTES = 262_144
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
DOMAINS = (
    "conversation", "cognition", "reasoning", "planning", "campaign",
    "approval", "action", "result", "learning",
)
DECISIONS = frozenset({"approve", "reject", "defer"})
REASONS = frozenset({"operator_navigation", "review_required", "result_available", "blocked_attention", "return_to_conversation"})
_FORBIDDEN = ("prompt", "message_text", "conversation_text", "memory_content", "private_reasoning", "raw_source", "raw_patch", "stdout", "stderr", "secret", "credential", "provider_payload", "release_authority")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _is_digest(value: object) -> bool:
    return bool(DIGEST_RE.fullmatch(str(value or "").lower()))


def _bounded(value: object) -> bool:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()) <= MAX_CONTRACT_BYTES


def _contains_forbidden(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).lower()
            if any(word in token for word in _FORBIDDEN) or _contains_forbidden(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden(item) for item in value)
    return False


def _verify(row: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(row)
    claimed = str(unsigned.pop(field, "")).lower()
    return _is_digest(claimed) and claimed == _digest(unsigned)


def create_navigation_request(*, navigation_id: str, experience_id: str, snapshot_digest: str,
                              from_surface_id: str, from_domain: str, to_surface_id: str,
                              to_domain: str, reason: str, context_digest: str,
                              operator_review_digest: str) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "navigation_id": str(navigation_id or ""),
        "experience_id": str(experience_id or ""),
        "snapshot_digest": str(snapshot_digest or "").lower(),
        "from_surface_id": str(from_surface_id or ""),
        "from_domain": str(from_domain or ""),
        "to_surface_id": str(to_surface_id or ""),
        "to_domain": str(to_domain or ""),
        "reason": str(reason or ""),
        "context_digest": str(context_digest or "").lower(),
        "operator_review_digest": str(operator_review_digest or "").lower(),
        "content_free": True,
        "state_mutation_requested": False,
        "execution_requested": False,
        "authority_requested": False,
    }
    row["navigation_digest"] = _digest(row)
    return row


def create_navigation_review(*, navigation_digest: str, decision: str, review_id: str,
                             operator_review_digest: str) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "navigation_digest": str(navigation_digest or "").lower(),
        "decision": str(decision or ""),
        "review_id": str(review_id or ""),
        "operator_review_digest": str(operator_review_digest or "").lower(),
        "content_free": True,
        "approval_consumed": False,
        "authority_granted": False,
    }
    row["review_digest"] = _digest(row)
    return row


def coordinate_experience_navigation(*, snapshot: Mapping[str, Any], navigation: Mapping[str, Any],
                                     review: Mapping[str, Any], current_context_digest: str,
                                     current_snapshot_digest: str) -> dict[str, Any]:
    errors: list[str] = []
    snapshot_row, nav, review_row = dict(snapshot), dict(navigation), dict(review)
    current_context = str(current_context_digest or "").lower()
    current_snapshot = str(current_snapshot_digest or "").lower()
    if not _bounded([snapshot_row, nav, review_row]): errors.append("oversized_contract")
    if _contains_forbidden([snapshot_row, nav, review_row]): errors.append("private_or_authority_content_present")
    if not _verify(nav, "navigation_digest"): errors.append("tampered_navigation")
    if not _verify(review_row, "review_digest"): errors.append("tampered_review")
    if nav.get("contract_version") != CONTRACT_VERSION or review_row.get("contract_version") != CONTRACT_VERSION: errors.append("contract_mismatch")
    for field in ("navigation_id", "experience_id", "from_surface_id", "to_surface_id"):
        if not IDENTIFIER_RE.fullmatch(str(nav.get(field) or "")): errors.append(f"invalid_{field}")
    if not IDENTIFIER_RE.fullmatch(str(review_row.get("review_id") or "")): errors.append("invalid_review_id")
    for field in ("snapshot_digest", "context_digest", "operator_review_digest"):
        if not _is_digest(nav.get(field)): errors.append(f"invalid_{field}")
    if not _is_digest(review_row.get("operator_review_digest")): errors.append("invalid_review_operator_digest")
    if review_row.get("decision") not in DECISIONS: errors.append("unsupported_decision")
    if nav.get("reason") not in REASONS: errors.append("unsupported_navigation_reason")
    if nav.get("from_domain") not in DOMAINS or nav.get("to_domain") not in DOMAINS: errors.append("unsupported_domain")
    if nav.get("navigation_digest") != review_row.get("navigation_digest"): errors.append("review_navigation_mismatch")
    if nav.get("experience_id") != snapshot_row.get("experience_id"): errors.append("experience_mismatch")
    if nav.get("snapshot_digest") != current_snapshot or nav.get("snapshot_digest") != snapshot_row.get("unified_experience_digest"): errors.append("stale_snapshot")
    if nav.get("context_digest") != current_context or nav.get("context_digest") != snapshot_row.get("context_digest"): errors.append("stale_context")
    surfaces = list(snapshot_row.get("surfaces") or [])
    by_id = {str(row.get("surface_id")): row for row in surfaces}
    from_row = by_id.get(str(nav.get("from_surface_id")))
    to_row = by_id.get(str(nav.get("to_surface_id")))
    if not from_row: errors.append("unknown_from_surface")
    if not to_row: errors.append("unknown_to_surface")
    if from_row and from_row.get("domain") != nav.get("from_domain"): errors.append("from_domain_mismatch")
    if to_row and to_row.get("domain") != nav.get("to_domain"): errors.append("to_domain_mismatch")
    if snapshot_row.get("selected_surface_id") != nav.get("from_surface_id"): errors.append("stale_focus")
    if nav.get("from_surface_id") == nav.get("to_surface_id"): errors.append("no_op_navigation")
    if nav.get("content_free") is not True or review_row.get("content_free") is not True: errors.append("privacy_contract_violation")
    for field in ("state_mutation_requested", "execution_requested", "authority_requested"):
        if nav.get(field) is not False: errors.append("authority_or_execution_expansion")
    if review_row.get("approval_consumed") is not False or review_row.get("authority_granted") is not False: errors.append("authority_or_execution_expansion")

    errors = sorted(set(errors))
    decision = str(review_row.get("decision") or "")
    changed = not errors and decision == "approve"
    status = "navigation_ready" if changed else ("navigation_rejected" if not errors and decision == "reject" else ("navigation_deferred" if not errors and decision == "defer" else "blocked"))
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "navigation_id": nav.get("navigation_id", ""),
        "experience_id": nav.get("experience_id", ""),
        "status": status,
        "decision": decision,
        "errors": errors,
        "error_count": len(errors),
        "from_surface_id": nav.get("from_surface_id", ""),
        "from_domain": nav.get("from_domain", ""),
        "to_surface_id": nav.get("to_surface_id", ""),
        "to_domain": nav.get("to_domain", ""),
        "focus_changed": changed,
        "presented_surface_id": nav.get("to_surface_id", "") if changed else nav.get("from_surface_id", ""),
        "presented_domain": nav.get("to_domain", "") if changed else nav.get("from_domain", ""),
        "presented_state": str((to_row if changed else from_row or {}).get("state", "")),
        "accountable_transition": changed,
        "content_free": True,
        "private_content_included": False,
        "subsystem_state_changed": False,
        "approval_created": False,
        "approval_consumed": False,
        "execution_invoked": False,
        "automatic_continuation": False,
        "source_modified": False,
        "runtime_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "authority_granted": False,
    }
    result["transition_digest"] = _digest(result)
    return result


def navigation_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "navigation_id": result.get("navigation_id", ""),
        "status": result.get("status", ""),
        "decision": result.get("decision", ""),
        "from_domain": result.get("from_domain", ""),
        "presented_domain": result.get("presented_domain", ""),
        "presented_state": result.get("presented_state", ""),
        "focus_changed": bool(result.get("focus_changed")),
        "error_count": int(result.get("error_count", 0) or 0),
        "transition_digest": result.get("transition_digest", ""),
        "content_free": True,
        "authority_granted": False,
        "execution_invoked": False,
    }
