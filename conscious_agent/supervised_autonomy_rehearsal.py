from __future__ import annotations
"""v1299.3-v1299.5 integrated supervised-autonomy rehearsal evidence reducer."""
from typing import Any, Iterable, Mapping
from supervised_autonomy_rehearsal_foundations import (
    ARCHITECTURE_LINEAGE, DENIED_AUTHORITY, REHEARSAL_STAGES, digest, valid_digest,
)

CONTRACT_VERSION = "v1299.5"


def _payload_without_seal(row: Mapping[str, Any], seal: str) -> dict[str, Any]:
    return {k: v for k, v in dict(row).items() if k != seal and k not in DENIED_AUTHORITY}


def evaluate_supervised_rehearsal(identity: Mapping[str, Any], steps: Iterable[Mapping[str, Any]], *,
                                  repaired_consumer_checks: Mapping[str, bool],
                                  native_windows_status: str = "pending") -> dict[str, Any]:
    ident = dict(identity)
    rows = [dict(x) for x in steps]
    violations: list[str] = []
    if not valid_digest(ident.get("identity_digest")) or not str(ident.get("rehearsal_id") or "").startswith("rehearsal_"):
        violations.append("invalid_rehearsal_identity")
    if ident.get("active_installation_modified") is not False:
        violations.append("active_installation_mutation_not_allowed")
    if any(bool(ident.get(k)) for k in DENIED_AUTHORITY):
        violations.append("identity_authority_expansion")
    expected_prior = ""
    seen_sequences: set[int] = set()
    seen_stages: set[str] = set()
    for row in rows:
        seq = int(row.get("sequence") or 0)
        stage = str(row.get("stage") or "")
        if row.get("rehearsal_id") != ident.get("rehearsal_id") or row.get("identity_digest") != ident.get("identity_digest"):
            violations.append(f"step_identity_mismatch:{seq}")
        if row.get("step_digest") != digest(_payload_without_seal(row, "step_digest")):
            violations.append(f"step_digest_mismatch:{seq}")
        if seq in seen_sequences:
            violations.append(f"duplicate_sequence:{seq}")
        seen_sequences.add(seq)
        if stage in seen_stages:
            violations.append(f"duplicate_stage:{stage}")
        seen_stages.add(stage)
        expected_stage = REHEARSAL_STAGES[seq - 1] if 1 <= seq <= len(REHEARSAL_STAGES) else ""
        if stage != expected_stage:
            violations.append(f"stage_sequence_mismatch:{seq}:{stage}")
        if str(row.get("prior_step_digest") or "") != expected_prior:
            violations.append(f"step_chain_mismatch:{seq}")
        if any(bool(row.get(k)) for k in DENIED_AUTHORITY):
            violations.append(f"step_authority_expansion:{seq}")
        if stage in {"inspect", "propose", "prioritize", "plan"} and row.get("source_digest") != ident.get("baseline_source_digest"):
            violations.append(f"prebuild_source_mismatch:{stage}")
        if stage in {"build", "test", "repair", "retest", "review", "update_request"} and row.get("source_digest") != ident.get("repaired_source_digest"):
            violations.append(f"repaired_source_mismatch:{stage}")
        expected_prior = str(row.get("step_digest") or "")
    if len(rows) != len(REHEARSAL_STAGES):
        violations.append("incomplete_rehearsal_stage_set")
    checks = {str(k): bool(v) for k, v in repaired_consumer_checks.items()}
    required_checks = {"canary_observation_resealed", "recovery_trigger_resealed", "maintenance_event_resealed"}
    if set(checks) != required_checks or not all(checks.values()):
        violations.append("real_integrity_repair_not_verified")
    native = str(native_windows_status or "pending")
    if native not in {"passed", "pending", "unavailable"}:
        violations.append("invalid_native_windows_state")
    if native == "passed":
        # Native pass must come from a separately attested Desktop run; this portable reducer cannot mint it.
        violations.append("portable_rehearsal_cannot_self_attest_native_windows")
    if violations:
        status = "supervised_autonomy_rehearsal_blocked"
        ready = False
    else:
        status = "rehearsal_candidate_ready_for_exact_operator_update_review"
        ready = True
    out = {
        "contract_version": CONTRACT_VERSION,
        "ok": ready,
        "status": status,
        "rehearsal_id": ident.get("rehearsal_id", ""),
        "defect_id": ident.get("defect_id", ""),
        "affected_paths": list(ident.get("affected_paths") or []),
        "stage_count": len(rows),
        "stage_sequence": [r.get("stage") for r in rows],
        "repaired_consumer_checks": checks,
        "integrity_violations": violations,
        "native_windows_status": native,
        "portable_rehearsal_complete": ready,
        "operator_may_inspect": True,
        "operator_may_defer": True,
        "operator_may_reject": True,
        "operator_may_cancel": True,
        "operator_may_request_separately_governed_rollback": True,
        "exact_v1269_update_authorization_required": ready,
        "exact_v1269_update_authorization_consumed": False,
        "generic_authorization_phrase_is_sufficient": False,
        "active_installation_modified": False,
        "architecture_lineage": dict(ARCHITECTURE_LINEAGE),
        "content_free": True,
        "read_only": True,
        **DENIED_AUTHORITY,
    }
    out["rehearsal_digest"] = digest(out)
    return out
