from __future__ import annotations
"""v1299.0-v1299.2 foundations for the final supervised-autonomy rehearsal.

The rehearsal binds a real repaired Eidolon defect to evidence produced across
existing supervised-development layers.  It records and evaluates work but does
not grant standing execution, update, release, or rollback authority.
"""
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v1299.2"
REAL_DEFECT_ID = "self_generated_evidence_digest_recomputation_gap"
REAL_DEFECT_AFFECTED_PATHS = (
    "conscious_agent/canary_self_updates.py",
    "conscious_agent/automated_recovery.py",
    "conscious_agent/repeated_self_maintenance.py",
)
REHEARSAL_STAGES = (
    "inspect",
    "propose",
    "prioritize",
    "plan",
    "build",
    "test",
    "repair",
    "retest",
    "review",
    "update_request",
)
OPERATOR_CONTROLS = frozenset({"inspect", "defer", "reject", "cancel", "rollback_request"})
DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "source_application_authorized": False,
    "self_update_authorized": False,
    "update_authorization_consumed": False,
    "rollback_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "standing_authority_granted": False,
    "autonomous_authority_granted": False,
}
ARCHITECTURE_LINEAGE = {
    "improvement_proposals": "v1291",
    "value_risk_deliberation": "v1292",
    "bounded_campaigns": "v1293",
    "candidate_evaluation": "v1294",
    "comprehensive_verification": "v1295",
    "canary_self_updates": "v1296",
    "automated_recovery": "v1297",
    "repeated_maintenance": "v1298",
    "governed_self_update": "v1269",
    "operator_review": "v1268",
}


def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def valid_digest(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return len(token) == 64 and all(ch in "0123456789abcdef" for ch in token)


def seal_rehearsal_identity(
    *,
    baseline_source_digest: str,
    repaired_source_digest: str,
    defect_evidence_digest: str,
    proposal_digest: str,
    deliberation_digest: str,
    plan_digest: str,
    candidate_evaluation_digest: str,
    verification_digest: str,
    review_digest: str,
    affected_paths: Iterable[str] = REAL_DEFECT_AFFECTED_PATHS,
) -> dict[str, Any]:
    digests = (
        baseline_source_digest,
        repaired_source_digest,
        defect_evidence_digest,
        proposal_digest,
        deliberation_digest,
        plan_digest,
        candidate_evaluation_digest,
        verification_digest,
        review_digest,
    )
    if not all(valid_digest(x) for x in digests):
        raise ValueError("sealed_rehearsal_lineage_required")
    if baseline_source_digest == repaired_source_digest:
        raise ValueError("repaired_source_must_differ_from_baseline")
    paths = tuple(sorted(dict.fromkeys(str(p).strip().replace("\\", "/") for p in affected_paths if str(p).strip())))
    if paths != tuple(sorted(REAL_DEFECT_AFFECTED_PATHS)):
        raise ValueError("real_defect_affected_paths_required")
    body = {
        "contract_version": CONTRACT_VERSION,
        "defect_id": REAL_DEFECT_ID,
        "affected_paths": list(paths),
        "affected_paths_digest": digest(list(paths)),
        "baseline_source_digest": baseline_source_digest,
        "repaired_source_digest": repaired_source_digest,
        "defect_evidence_digest": defect_evidence_digest,
        "proposal_digest": proposal_digest,
        "deliberation_digest": deliberation_digest,
        "plan_digest": plan_digest,
        "candidate_evaluation_digest": candidate_evaluation_digest,
        "verification_digest": verification_digest,
        "review_digest": review_digest,
        "architecture_lineage": dict(ARCHITECTURE_LINEAGE),
        "real_source_repair": True,
        "active_installation_modified": False,
        "content_free": True,
    }
    body["rehearsal_id"] = "rehearsal_" + digest(body)[:24]
    body["identity_digest"] = digest(body)
    return body | DENIED_AUTHORITY


def rehearsal_step(identity: Mapping[str, Any], *, sequence: int, stage: str, evidence_digest: str,
                   source_digest: str, prior_step_digest: str = "", result: str = "recorded",
                   native_windows: bool = False, native_attested: bool = False) -> dict[str, Any]:
    stage = str(stage)
    if stage not in REHEARSAL_STAGES:
        raise ValueError("known_rehearsal_stage_required")
    if int(sequence) < 1 or int(sequence) > len(REHEARSAL_STAGES):
        raise ValueError("bounded_rehearsal_sequence_required")
    if not valid_digest(identity.get("identity_digest")) or not valid_digest(evidence_digest) or not valid_digest(source_digest):
        raise ValueError("sealed_rehearsal_step_required")
    if prior_step_digest and not valid_digest(prior_step_digest):
        raise ValueError("valid_prior_step_digest_required")
    row = {
        "contract_version": CONTRACT_VERSION,
        "rehearsal_id": identity.get("rehearsal_id"),
        "identity_digest": identity.get("identity_digest"),
        "sequence": int(sequence),
        "stage": stage,
        "evidence_digest": evidence_digest,
        "source_digest": source_digest,
        "prior_step_digest": str(prior_step_digest or ""),
        "result": str(result),
        "native_windows": bool(native_windows),
        "native_attested": bool(native_attested),
        "content_free": True,
    }
    row["step_digest"] = digest(row)
    return row | DENIED_AUTHORITY


def operator_control_record(identity: Mapping[str, Any], *, control: str, evidence_digest: str) -> dict[str, Any]:
    control = str(control)
    if control not in OPERATOR_CONTROLS:
        raise ValueError("supported_operator_control_required")
    if not valid_digest(identity.get("identity_digest")) or not valid_digest(evidence_digest):
        raise ValueError("sealed_operator_control_evidence_required")
    disposition = {
        "inspect": "inspection_only",
        "defer": "rehearsal_deferred",
        "reject": "rehearsal_rejected",
        "cancel": "rehearsal_cancelled",
        "rollback_request": "rollback_request_requires_separate_governance",
    }[control]
    body = {
        "contract_version": CONTRACT_VERSION,
        "rehearsal_id": identity.get("rehearsal_id"),
        "identity_digest": identity.get("identity_digest"),
        "control": control,
        "disposition": disposition,
        "evidence_digest": evidence_digest,
        "control_is_authorization": False,
        "content_free": True,
    }
    body["control_digest"] = digest(body)
    return body | DENIED_AUTHORITY
