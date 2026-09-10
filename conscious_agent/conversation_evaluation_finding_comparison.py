from __future__ import annotations

"""Bounded v1089.5 descriptive comparison of repair-intake findings."""

from typing import Any, Iterable, Mapping
import hashlib
import json

from conversation_evaluation_finding import EvaluationFindingError, load_evaluation_finding
from conversation_evaluation_finding_reproducibility import build_finding_reproducibility
from conversation_evaluation_finding_repair_candidates import build_finding_repair_candidates
from conversation_evaluation_finding_triage import build_evaluation_finding_triage

FINDING_COMPARISON_SCHEMA_VERSION = "1"
MIN_COMPARISON_FINDINGS = 2
MAX_COMPARISON_FINDINGS = 8


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _normalize(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in values:
        token = str(raw or "").strip()
        if token and token not in result: result.append(token)
    if len(result) < MIN_COMPARISON_FINDINGS: raise EvaluationFindingError("At least two distinct findings are required for comparison.")
    if len(result) > MAX_COMPARISON_FINDINGS: raise EvaluationFindingError(f"At most {MAX_COMPARISON_FINDINGS} findings may be compared.")
    return result


def _row(finding_id: str) -> dict[str, Any]:
    summary = load_evaluation_finding(finding_id); repro = build_finding_reproducibility(finding_id); refs = build_finding_repair_candidates(finding_id); triage = build_evaluation_finding_triage(finding_id)
    return {"finding_id": finding_id, "finding_state": summary["state"], "finding_revision": summary["revision"], "campaign_id": summary["campaign_id"], "evaluation_id": summary["evaluation_id"], "issue_domain": summary["issue_domain"], "severity": summary["severity"], "reproducibility_status": repro["reproducibility_status"], "reproduction_attempt_count": repro["attempt_count"], "repair_candidate_reference_count": refs["reference_count"], "proposed_reference_count": int((refs.get("state_counts") or {}).get("proposed") or 0), "under_review_reference_count": int((refs.get("state_counts") or {}).get("under_review") or 0), "triage_state": triage["triage_state"], "triage_disposition": triage["triage_disposition"], "triage_note_present": triage["triage_note_present"], "record_digest": summary["record_digest"], "reproducibility_digest": repro["attempts_digest"], "repair_references_digest": refs["references_digest"], "triage_digest": triage["triage_digest"]}


def build_evaluation_finding_comparison(finding_ids: Iterable[str]) -> dict[str, Any]:
    normalized = _normalize(finding_ids); rows = [_row(fid) for fid in normalized]; baseline = rows[0]
    deltas = []
    for row in rows[1:]:
        deltas.append({"baseline_finding_id": baseline["finding_id"], "finding_id": row["finding_id"], "count_deltas": {key: int(row[key]) - int(baseline[key]) for key in ("reproduction_attempt_count", "repair_candidate_reference_count", "proposed_reference_count", "under_review_reference_count")}, "same_issue_domain": row["issue_domain"] == baseline["issue_domain"], "same_severity": row["severity"] == baseline["severity"], "same_reproducibility_status": row["reproducibility_status"] == baseline["reproducibility_status"], "same_triage_disposition": row["triage_disposition"] == baseline["triage_disposition"]})
    stable = {"finding_count": len(rows), "minimum_findings": MIN_COMPARISON_FINDINGS, "maximum_findings": MAX_COMPARISON_FINDINGS, "baseline_finding_id": baseline["finding_id"], "findings": rows, "deltas": deltas}
    return {"ok": True, "type": "desktop_alpha_evaluation_finding_comparison", "schema_version": FINDING_COMPARISON_SCHEMA_VERSION, **stable, "comparison_digest": _digest(stable), "descriptive_counts_only": True, "findings_ranked": False, "winner_selected": False, "priority_assigned": False, "autonomous_prioritization": False, "statistical_significance_claimed": False, "automatic_task_created": False, "automatic_work_item_created": False, "patch_generated": False, "patch_reviewed": False, "patch_applied": False, "approval_granted": False, "rollback_authorized": False, "installation_performed": False, "promotion_performed": False, "release_recommendation_produced": False, "release_certified": False, "transcript_inspected": False, "prompt_inspected": False, "private_finding_content_inspected": False, "private_notes_inspected": False, "private_reference_values_inspected": False, "provider_invoked": False, "writes_state": False, "read_only": True, "content_free": True, "redacted": True}


def finding_comparison_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {"private_title", "private_details", "finding_title", "finding_details", "private_note", "note", "notes", "environment_label", "private_environment_label", "reference_value", "private_reference_value", "content", "text", "message", "messages", "transcript", "prompt", "provider_payload", "credentials", "vectors", "embedding", "hidden_reasoning", "chain_of_thought"}
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}: return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)): stack.extend(current)
    return False
