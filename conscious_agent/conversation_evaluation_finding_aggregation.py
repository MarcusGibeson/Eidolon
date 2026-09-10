from __future__ import annotations

"""Privacy-safe v1089.3 aggregation of explicit evaluation findings.

The aggregator consumes redacted finding, reproducibility, repair-reference, and
triage evidence. It returns descriptive counts and digests only. It never reads
private finding text, reproduction notes, environment labels, reference values,
transcripts, prompts, memories, or provider payloads, and it creates no task,
priority, patch, approval, or release decision.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation_protocol import ISSUE_DOMAINS, ISSUE_SEVERITIES
from conversation_evaluation_finding import FINDING_STATES, finding_public_summary, iter_evaluation_findings_private
from conversation_evaluation_finding_reproducibility import build_finding_reproducibility
from conversation_evaluation_finding_repair_candidates import REFERENCE_STATES, build_finding_repair_candidates

FINDING_AGGREGATION_SCHEMA_VERSION = "1"
MAX_AGGREGATED_FINDINGS = 256


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _triage_public(record: Mapping[str, Any]) -> dict[str, Any]:
    triage = record.get("triage") if isinstance(record.get("triage"), Mapping) else {}
    return {
        "triage_state": str(triage.get("state") or "not_started"),
        "triage_disposition": str(triage.get("disposition") or ""),
        "triage_note_present": bool(str(triage.get("private_note") or "")),
    }


def build_evaluation_finding_aggregation(*, campaign_id: str = "", evaluation_id: str = "", limit: int = MAX_AGGREGATED_FINDINGS) -> dict[str, Any]:
    cap = max(1, min(MAX_AGGREGATED_FINDINGS, int(limit or MAX_AGGREGATED_FINDINGS)))
    records = []
    for record in iter_evaluation_findings_private() or ():
        if campaign_id and str(record.get("campaign_id") or "") != str(campaign_id):
            continue
        if evaluation_id and str(record.get("evaluation_id") or "") != str(evaluation_id):
            continue
        records.append(record)
    records = records[-cap:]
    state_counts = {state: 0 for state in FINDING_STATES}
    domain_counts = {domain: 0 for domain in ISSUE_DOMAINS}
    severity_counts = {severity: 0 for severity in ISSUE_SEVERITIES}
    reproducibility_counts = {key: 0 for key in ("confirmed", "mixed", "not_reproduced", "inconclusive", "not_reviewed")}
    reference_state_counts = {state: 0 for state in REFERENCE_STATES}
    triage_state_counts = {state: 0 for state in ("not_started", "in_review", "completed")}
    triage_disposition_counts = {key: 0 for key in ("acknowledged", "reproduction_required", "repair_candidate_review", "deferred", "dismissed", "unassigned")}
    rows: list[dict[str, Any]] = []
    for record in records:
        summary = finding_public_summary(record)
        repro = build_finding_reproducibility(summary["finding_id"])
        refs = build_finding_repair_candidates(summary["finding_id"])
        triage = _triage_public(record)
        state = summary["state"] if summary["state"] in state_counts else "open"
        domain = summary["issue_domain"] if summary["issue_domain"] in domain_counts else "none"
        severity = summary["severity"] if summary["severity"] in severity_counts else "none"
        repro_status = str(repro.get("reproducibility_status") or "not_reviewed")
        disposition = triage["triage_disposition"] or "unassigned"
        state_counts[state] += 1; domain_counts[domain] += 1; severity_counts[severity] += 1
        reproducibility_counts[repro_status] = reproducibility_counts.get(repro_status, 0) + 1
        triage_state_counts[triage["triage_state"]] = triage_state_counts.get(triage["triage_state"], 0) + 1
        triage_disposition_counts[disposition] = triage_disposition_counts.get(disposition, 0) + 1
        for ref_state, count in dict(refs.get("state_counts") or {}).items():
            reference_state_counts[str(ref_state)] = reference_state_counts.get(str(ref_state), 0) + max(0, int(count or 0))
        rows.append({
            "finding_id": summary["finding_id"], "state": state, "revision": summary["revision"],
            "campaign_id": summary["campaign_id"], "evaluation_id": summary["evaluation_id"],
            "issue_domain": domain, "severity": severity, "reproducibility_status": repro_status,
            "reproduction_attempt_count": repro["attempt_count"], "repair_candidate_reference_count": refs["reference_count"],
            **triage, "record_digest": summary["record_digest"], "reproducibility_digest": repro["attempts_digest"],
            "repair_references_digest": refs["references_digest"],
        })
    stable = {
        "finding_count": len(rows), "maximum_findings": MAX_AGGREGATED_FINDINGS,
        "campaign_id_filter": str(campaign_id or ""), "evaluation_id_filter": str(evaluation_id or ""),
        "state_counts": state_counts, "issue_domain_counts": domain_counts, "severity_counts": severity_counts,
        "reproducibility_counts": reproducibility_counts, "repair_reference_state_counts": reference_state_counts,
        "triage_state_counts": triage_state_counts, "triage_disposition_counts": triage_disposition_counts,
        "findings": rows,
    }
    return {
        "ok": True, "type": "desktop_alpha_evaluation_finding_aggregation", "schema_version": FINDING_AGGREGATION_SCHEMA_VERSION,
        **stable, "aggregation_digest": _digest(stable), "descriptive_counts_only": True,
        "findings_ranked": False, "priority_assigned": False, "autonomous_prioritization": False,
        "automatic_task_created": False, "automatic_work_item_created": False, "patch_generated": False,
        "patch_applied": False, "approval_granted": False, "rollback_authorized": False,
        "installation_performed": False, "promotion_performed": False, "release_recommendation_produced": False,
        "release_certified": False, "transcript_inspected": False, "prompt_inspected": False,
        "private_finding_content_inspected": False, "private_notes_inspected": False,
        "private_reference_values_inspected": False, "provider_invoked": False, "writes_state": False,
        "read_only": True, "content_free": True, "redacted": True,
    }


def finding_aggregation_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {"private_title", "private_details", "finding_title", "finding_details", "private_note", "note", "notes", "environment_label", "private_environment_label", "reference_value", "private_reference_value", "content", "text", "message", "messages", "transcript", "prompt", "provider_payload", "credentials", "vectors", "embedding", "hidden_reasoning", "chain_of_thought"}
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}: return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)): stack.extend(current)
    return False
