from __future__ import annotations
"""v1293.6-v1293.8 campaign reliability and authority-boundary checks."""
from typing import Any, Iterable, Mapping
from bounded_development_campaigns_foundations import DENIED_AUTHORITY, TERMINAL_STAGES, valid_digest, validate_state_identity

CONTRACT_VERSION = "v1293.8"


def assess_bounded_campaign_reliability(states: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    violations: list[str] = []
    count = 0
    for row in states:
        count += 1
        cid = str(row.get("campaign_id") or f"row-{count}")
        if not validate_state_identity(row): violations.append(f"{cid}:identity_or_authority_violation")
        if int(row.get("event_sequence", 0)) > int(row.get("max_events", 0)): violations.append(f"{cid}:event_budget_exceeded")
        if int(row.get("recovery_attempts", 0)) > int(row.get("max_recovery_attempts", 0)): violations.append(f"{cid}:recovery_budget_exceeded")
        if len(tuple(row.get("event_digests") or ())) != len(set(row.get("event_digests") or ())): violations.append(f"{cid}:duplicate_event_history")
        if row.get("terminal") != (row.get("current_stage") in TERMINAL_STAGES): violations.append(f"{cid}:terminal_stage_incoherent")
        if row.get("current_stage") == "complete" and not row.get("completion_conditions_met"): violations.append(f"{cid}:false_completion")
        if row.get("current_stage") == "complete":
            evidence = row.get("completed_stage_evidence") or {}
            for prefix in ("implementation:implementation_ready", "verification:verification_pass", "quality_review:quality_review_pass", "operator_review:operator_review_complete"):
                if not any(str(k).startswith(prefix) and valid_digest(v) for k, v in evidence.items()): violations.append(f"{cid}:missing_{prefix.split(':')[0]}_evidence")
        failed = tuple(row.get("failed_strategy_digests") or ())
        if len(failed) != len(set(failed)): violations.append(f"{cid}:duplicate_failed_strategy")
        if row.get("selection_is_execution_authority") or row.get("selection_is_update_authority"): violations.append(f"{cid}:selection_authority_expansion")
        if any(bool(row.get(k)) for k in DENIED_AUTHORITY): violations.append(f"{cid}:campaign_authority_expansion")
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not violations,
        "status": "bounded_campaign_reliability_clear" if not violations else "bounded_campaign_reliability_blocked",
        "campaign_count": count,
        "violations": violations,
        "native_windows_restart_and_multiprocess_validation_pending": True,
        "content_free": True,
        "read_only": True,
        **DENIED_AUTHORITY,
    }
