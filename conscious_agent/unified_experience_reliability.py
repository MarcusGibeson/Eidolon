from __future__ import annotations

"""v1190.6-v1190.8 unified experience reliability and privacy hardening."""

import hashlib, json, re
from typing import Any, Mapping

CONTRACT_VERSION = "v1190.8"
SCHEMA_VERSION = "1"
MAX_CONTRACT_BYTES = 262_144
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
DECISIONS = frozenset({"approve", "reject", "defer"})
ACTIONS = frozenset({"hold", "refresh_snapshot", "return_to_conversation", "abandon_navigation"})
INTERRUPTIONS = frozenset({"none", "stale_snapshot", "stale_context", "stale_focus", "privacy_block", "transition_failure"})
_FORBIDDEN = ("prompt", "message_text", "conversation_text", "memory_content", "private_reasoning", "raw_source", "raw_patch", "stdout", "stderr", "secret", "credential", "provider_payload", "release_authority")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _is_digest(value: object) -> bool:
    return bool(DIGEST_RE.fullmatch(str(value or "").lower()))


def _verify(row: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(row); claimed = str(unsigned.pop(field, "")).lower()
    return _is_digest(claimed) and claimed == _digest(unsigned)


def _bounded(value: object) -> bool:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()) <= MAX_CONTRACT_BYTES


def _contains_forbidden(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(any(word in str(k).lower() for word in _FORBIDDEN) or _contains_forbidden(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden(v) for v in value)
    return False


def create_reliability_assessment(*, reliability_id: str, experience_id: str, snapshot_digest: str,
                                  transition_digest: str, expected_context_digest: str,
                                  observed_context_digest: str, expected_focus_surface_id: str,
                                  observed_focus_surface_id: str, interruption: str,
                                  privacy_finding_count: int, authority_claim_count: int) -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "reliability_id": str(reliability_id or ""), "experience_id": str(experience_id or ""),
        "snapshot_digest": str(snapshot_digest or "").lower(), "transition_digest": str(transition_digest or "").lower(),
        "expected_context_digest": str(expected_context_digest or "").lower(), "observed_context_digest": str(observed_context_digest or "").lower(),
        "expected_focus_surface_id": str(expected_focus_surface_id or ""), "observed_focus_surface_id": str(observed_focus_surface_id or ""),
        "interruption": str(interruption or ""), "privacy_finding_count": int(privacy_finding_count),
        "authority_claim_count": int(authority_claim_count), "content_free": True,
        "recovery_executed": False, "state_mutation_requested": False, "authority_requested": False,
    }
    row["reliability_digest"] = _digest(row)
    return row


def create_reliability_review(*, reliability_digest: str, decision: str, action: str,
                              review_id: str, operator_review_digest: str) -> dict[str, Any]:
    row = {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
           "reliability_digest": str(reliability_digest or "").lower(), "decision": str(decision or ""),
           "action": str(action or ""), "review_id": str(review_id or ""),
           "operator_review_digest": str(operator_review_digest or "").lower(), "content_free": True,
           "recovery_executed": False, "authority_granted": False}
    row["review_digest"] = _digest(row)
    return row


def assess_unified_experience_reliability(*, snapshot: Mapping[str, Any], transition: Mapping[str, Any],
                                          assessment: Mapping[str, Any], review: Mapping[str, Any],
                                          current_snapshot_digest: str, current_context_digest: str,
                                          current_focus_surface_id: str) -> dict[str, Any]:
    snap, trans, row, rev = map(dict, (snapshot, transition, assessment, review)); errors: list[str] = []
    if not _bounded([snap, trans, row, rev]): errors.append("oversized_contract")
    if _contains_forbidden([snap, trans, row, rev]): errors.append("private_or_authority_content_present")
    if not _verify(row, "reliability_digest"): errors.append("tampered_reliability")
    if not _verify(rev, "review_digest"): errors.append("tampered_review")
    if row.get("contract_version") != CONTRACT_VERSION or rev.get("contract_version") != CONTRACT_VERSION: errors.append("contract_mismatch")
    for field in ("snapshot_digest", "transition_digest", "expected_context_digest", "observed_context_digest"):
        if not _is_digest(row.get(field)): errors.append(f"invalid_{field}")
    if not _is_digest(rev.get("operator_review_digest")): errors.append("invalid_operator_review_digest")
    if rev.get("decision") not in DECISIONS: errors.append("unsupported_decision")
    if rev.get("action") not in ACTIONS: errors.append("unsupported_action")
    if row.get("interruption") not in INTERRUPTIONS: errors.append("unsupported_interruption")
    if row.get("reliability_digest") != rev.get("reliability_digest"): errors.append("review_mismatch")
    if row.get("experience_id") != snap.get("experience_id"): errors.append("experience_mismatch")
    if row.get("snapshot_digest") != snap.get("unified_experience_digest") or row.get("snapshot_digest") != str(current_snapshot_digest).lower(): errors.append("stale_snapshot")
    if row.get("transition_digest") != trans.get("transition_digest"): errors.append("transition_mismatch")
    if row.get("expected_context_digest") != snap.get("context_digest"): errors.append("expected_context_mismatch")
    if row.get("observed_context_digest") != str(current_context_digest).lower(): errors.append("stale_context")
    if row.get("expected_context_digest") != row.get("observed_context_digest"): errors.append("context_drift")
    if row.get("expected_focus_surface_id") != trans.get("presented_surface_id"): errors.append("expected_focus_mismatch")
    if row.get("observed_focus_surface_id") != str(current_focus_surface_id): errors.append("stale_focus")
    if row.get("expected_focus_surface_id") != row.get("observed_focus_surface_id"): errors.append("focus_drift")
    if int(row.get("privacy_finding_count", -1)) != 0: errors.append("privacy_findings_present")
    if int(row.get("authority_claim_count", -1)) != 0: errors.append("authority_claims_present")
    if row.get("content_free") is not True or rev.get("content_free") is not True: errors.append("privacy_contract_violation")
    if row.get("recovery_executed") is not False or row.get("state_mutation_requested") is not False or row.get("authority_requested") is not False: errors.append("authority_or_execution_expansion")
    if rev.get("recovery_executed") is not False or rev.get("authority_granted") is not False: errors.append("authority_or_execution_expansion")
    errors = sorted(set(errors)); decision = str(rev.get("decision") or "")
    status = "reliability_ready" if not errors and decision == "approve" else ("reliability_rejected" if not errors and decision == "reject" else ("reliability_deferred" if not errors and decision == "defer" else "blocked"))
    result = {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
              "reliability_id": row.get("reliability_id", ""), "experience_id": row.get("experience_id", ""),
              "status": status, "decision": decision, "action": rev.get("action", ""), "errors": errors,
              "error_count": len(errors), "interruption": row.get("interruption", ""),
              "snapshot_current": "stale_snapshot" not in errors, "context_current": not ({"stale_context", "context_drift"} & set(errors)),
              "focus_current": not ({"stale_focus", "focus_drift"} & set(errors)), "privacy_clear": "privacy_findings_present" not in errors,
              "authority_clear": "authority_claims_present" not in errors, "operator_review_required": True,
              "recovery_executed": False, "subsystem_state_changed": False, "execution_invoked": False,
              "automatic_continuation": False, "source_modified": False, "runtime_modified": False,
              "provider_contacted": False, "model_contacted": False, "authority_granted": False, "content_free": True}
    result["reliability_result_digest"] = _digest(result)
    return result


def reliability_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {k: result.get(k) for k in ("contract_version", "reliability_id", "status", "decision", "action", "interruption", "error_count", "snapshot_current", "context_current", "focus_current", "privacy_clear", "authority_clear", "operator_review_required", "reliability_result_digest")} | {"content_free": True, "authority_granted": False, "recovery_executed": False}
