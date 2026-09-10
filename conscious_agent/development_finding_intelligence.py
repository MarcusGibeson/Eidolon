from __future__ import annotations

"""Portable v1526-v1550 development finding and feedback intelligence.

This layer deliberately reuses the existing private evaluation-finding owner.
It consumes only redacted summaries/aggregation rows and optional content-free
runtime event projections.  It does not persist private conversation text,
create a second finding store, or grant proposal/installation authority.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v1550.9"
FINDING_CONTRACT_VERSION = "v1533.9"
REPRODUCTION_CONTRACT_VERSION = "v1541.9"
FEEDBACK_CONTRACT_VERSION = "v1550.9"

_FEEDBACK_KINDS = (
    "dashboard_feedback",
    "action_failure",
    "provider_failure",
    "operator_trial_score",
)
_INACTIVE = {"resolved", "dismissed", "superseded", "retracted", "cancelled"}
_PRIVATE_FIELDS = frozenset({
    "content", "conversation", "conversations", "details", "expected_text",
    "actual_text", "finding_details", "finding_title", "message", "messages",
    "note", "notes", "private_details", "private_note", "private_title",
    "prompt", "provider_payload", "raw_response", "reference_value", "response",
    "text", "transcript", "credentials", "secret", "secrets",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _bounded_float(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _freshness(row: Mapping[str, Any]) -> str:
    explicit = str(row.get("freshness") or "").strip().lower()
    if explicit in {"current", "recent", "aging", "stale"}:
        return explicit
    stamp = str(row.get("updated_at") or row.get("observed_at") or row.get("created_at") or "")
    if not stamp:
        return "unknown"
    try:
        observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        days = max(0.0, (datetime.now(timezone.utc) - observed).total_seconds() / 86400.0)
    except (TypeError, ValueError):
        return "unknown"
    return "current" if days <= 1 else "recent" if days <= 14 else "aging" if days <= 60 else "stale"


def development_finding_contract() -> dict[str, Any]:
    contract = {
        "contract_version": FINDING_CONTRACT_VERSION,
        "private_record_owner": "conversation_evaluation_finding",
        "duplicate_private_store_created": False,
        "required_product_concepts": [
            "reproduction_steps", "affected_surface", "expected_behavior",
            "actual_behavior", "severity", "frequency", "evidence_digest",
            "operator_correction",
        ],
        "portable_public_representation": [
            "finding_id", "finding_digest", "state", "revision", "issue_domain",
            "severity", "frequency_score", "freshness", "affected_surface",
            "reproducibility_status", "reproduction_attempt_count",
            "repair_candidate_reference_count", "triage_state", "triage_disposition",
            "expected_behavior_contract", "actual_behavior_evidence_digest",
            "operator_correction_supported", "implementation_candidate_id",
            "source_module", "content_free",
        ],
        "migration_deferred_fields": [
            "structured_private_reproduction_steps",
            "structured_private_expected_behavior",
            "structured_private_actual_behavior",
            "structured_private_frequency_history",
        ],
        "authority_boundary": {
            "automatic_finding_creation": False,
            "proposal_creation_authorized": False,
            "provider_contact_authorized": False,
            "source_mutation_authorized": False,
            "installation_authorized": False,
            "promotion_authorized": False,
        },
        "content_free": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def _finding_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    finding_id = str(row.get("finding_id") or "").strip()
    record_digest = str(row.get("record_digest") or "").strip().lower()
    state = str(row.get("state") or "open").strip().lower()
    if not finding_id or not record_digest or state in _INACTIVE:
        return None
    attempts = max(0, int(row.get("reproduction_attempt_count") or 0))
    repro = str(row.get("reproducibility_status") or "not_reviewed")
    confidence = 0.82 if repro == "confirmed" else 0.68 if repro == "mixed" else 0.58 if attempts else 0.5
    frequency_score = 0.15 if attempts == 0 else 0.35 if attempts == 1 else 0.6 if attempts <= 3 else 0.85
    issue_domain = str(row.get("issue_domain") or "unknown")
    affected_surface = {
        "model_quality": "conversation",
        "interface": "dashboard_or_chat_ui",
        "session_continuity": "conversation_continuity",
    }.get(issue_domain, issue_domain or "unknown")
    candidate_id = str(row.get("candidate_id") or "")
    source_module = str(row.get("source_module") or "")
    stable = {
        "finding_id": finding_id,
        "finding_digest": record_digest,
        "state": state,
        "revision": max(0, int(row.get("revision") or 0)),
        "issue_domain": issue_domain,
        "severity": str(row.get("severity") or "medium"),
        "frequency_score": frequency_score,
        "freshness": _freshness(row),
        "affected_surface": affected_surface,
        "reproducibility_status": repro,
        "reproduction_attempt_count": attempts,
        "reproducibility_digest": str(row.get("reproducibility_digest") or ""),
        "repair_candidate_reference_count": max(0, int(row.get("repair_candidate_reference_count") or 0)),
        "repair_references_digest": str(row.get("repair_references_digest") or ""),
        "triage_state": str(row.get("triage_state") or "not_started"),
        "triage_disposition": str(row.get("triage_disposition") or ""),
        "expected_behavior_contract": "operator_reported_expected_behavior_preserved_privately",
        "actual_behavior_evidence_digest": record_digest,
        "operator_correction_supported": True,
        "operator_confirmed": True,
        "confidence": confidence,
        "candidate_id": candidate_id,
        "source_module": source_module,
        "content_free": True,
    }
    stable["development_finding_digest"] = _digest(stable)
    return stable


def build_development_finding_projection(aggregation: Mapping[str, Any] | None) -> dict[str, Any]:
    """Adapt existing redacted evaluation findings into development evidence."""

    rows = []
    rejected = 0
    for raw in list((aggregation or {}).get("findings") or []):
        if not isinstance(raw, Mapping):
            rejected += 1
            continue
        projected = _finding_row(raw)
        if projected:
            rows.append(projected)
        else:
            rejected += 1
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["finding_digest"])
        previous = unique.get(key)
        if previous is None or int(row["revision"]) > int(previous["revision"]):
            unique[key] = row
    rows = sorted(unique.values(), key=lambda item: (item["finding_id"], -int(item["revision"])))
    result = {
        "ok": True,
        "contract_version": FINDING_CONTRACT_VERSION,
        "private_record_owner": "conversation_evaluation_finding",
        "findings": rows,
        "finding_count": len(rows),
        "rejected_or_inactive_count": rejected,
        "private_content_inspected": False,
        "duplicate_private_store_created": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["projection_digest"] = _digest([(row["finding_id"], row["development_finding_digest"]) for row in rows])
    return result


def reproduction_pipeline_contract() -> dict[str, Any]:
    contract = {
        "contract_version": REPRODUCTION_CONTRACT_VERSION,
        "input": "content_free_development_finding_projection",
        "outputs": ["synthetic_scenario_contract", "fixture_identity", "acceptance_signals"],
        "private_conversation_content_stored": False,
        "automatic_replay_of_private_conversation": False,
        "automatic_provider_contact": False,
        "automatic_source_mutation": False,
        "deterministic": True,
        "content_free": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def build_synthetic_reproduction_scenario(finding: Mapping[str, Any]) -> dict[str, Any]:
    finding_id = str(finding.get("finding_id") or "")
    finding_digest = str(finding.get("development_finding_digest") or finding.get("finding_digest") or "")
    if not finding_id or not finding_digest:
        return {"ok": False, "reason": "finding_identity_required", "content_free": True}
    repro = str(finding.get("reproducibility_status") or "not_reviewed")
    scenario = {
        "scenario_kind": "synthetic_development_finding",
        "finding_id": finding_id,
        "finding_digest": finding_digest,
        "affected_surface": str(finding.get("affected_surface") or "unknown"),
        "issue_domain": str(finding.get("issue_domain") or "unknown"),
        "severity": str(finding.get("severity") or "medium"),
        "reproducibility_status": repro,
        "source_module": str(finding.get("source_module") or ""),
        "candidate_id": str(finding.get("candidate_id") or ""),
        "setup_contract": [
            "use_synthetic_or_operator_supplied_fixture_only",
            "do_not_load_private_conversation_content",
            "bind_fixture_to_finding_digest",
        ],
        "acceptance_signals": [
            "target_behavior_observable",
            "finding_digest_attributable",
            "no_unrelated_regression",
        ],
        "operator_retrial_required": str(finding.get("affected_surface") or "") in {"conversation", "dashboard_or_chat_ui", "conversation_continuity"},
        "private_content_required": False,
        "provider_contact_authorized": False,
        "source_mutation_authorized": False,
        "content_free": True,
    }
    scenario["fixture_id"] = f"devfixture_{_digest(scenario)[:24]}"
    scenario["scenario_digest"] = _digest(scenario)
    return {"ok": True, **scenario}


def build_reproduction_pipeline(findings: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    scenarios = []
    rejected = 0
    for finding in findings:
        scenario = build_synthetic_reproduction_scenario(finding)
        if scenario.get("ok"):
            scenarios.append(scenario)
        else:
            rejected += 1
    unique = {str(row["scenario_digest"]): row for row in scenarios}
    scenarios = sorted(unique.values(), key=lambda row: row["fixture_id"])
    result = {
        "ok": True,
        "contract_version": REPRODUCTION_CONTRACT_VERSION,
        "scenarios": scenarios,
        "scenario_count": len(scenarios),
        "rejected_count": rejected,
        "private_conversation_content_stored": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["pipeline_digest"] = _digest([(row["fixture_id"], row["scenario_digest"]) for row in scenarios])
    return result


def live_feedback_contract() -> dict[str, Any]:
    contract = {
        "contract_version": FEEDBACK_CONTRACT_VERSION,
        "feedback_kinds": list(_FEEDBACK_KINDS),
        "accepted_public_identity": ["feedback_id", "evidence_digest"],
        "lifecycle": ["open", "corrected", "retracted", "resolved", "dismissed"],
        "deduplication": "evidence_digest",
        "freshness_preserved": True,
        "private_payloads_allowed": False,
        "operator_trial_is_subjective_evidence_not_execution_authority": True,
        "provider_failure_receipt_is_evidence_not_provider_authority": True,
        "content_free": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def normalize_live_feedback(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    rejected = 0
    inactive = 0
    for raw in rows:
        if not isinstance(raw, Mapping):
            rejected += 1
            continue
        keys = {str(k) for k in raw}
        if keys & _PRIVATE_FIELDS:
            rejected += 1
            continue
        kind = str(raw.get("feedback_kind") or "").strip().lower()
        state = str(raw.get("state") or "open").strip().lower()
        feedback_id = str(raw.get("feedback_id") or raw.get("finding_id") or "").strip()
        evidence_digest = str(raw.get("evidence_digest") or raw.get("record_digest") or raw.get("failure_digest") or "").strip().lower()
        if kind not in _FEEDBACK_KINDS or not feedback_id or len(evidence_digest) != 64:
            rejected += 1
            continue
        if state in _INACTIVE:
            inactive += 1
            continue
        stable = {
            "feedback_kind": kind,
            "feedback_id": feedback_id,
            "state": state,
            "evidence_digest": evidence_digest,
            "issue_domain": str(raw.get("issue_domain") or ("provider" if kind == "provider_failure" else "unknown")),
            "severity": str(raw.get("severity") or "medium"),
            "frequency": max(0, int(raw.get("frequency") or raw.get("recurrence_count") or 1)),
            "confidence": _bounded_float(raw.get("confidence"), 0.8 if kind == "operator_trial_score" else 0.65),
            "freshness": _freshness(raw),
            "candidate_id": str(raw.get("candidate_id") or ""),
            "source_module": str(raw.get("source_module") or ""),
            "operator_confirmed": bool(raw.get("operator_confirmed") or kind in {"dashboard_feedback", "operator_trial_score"}),
            "acceptance_criteria": [str(v) for v in list(raw.get("acceptance_criteria") or []) if str(v)][:8],
            "content_free": True,
        }
        stable["feedback_digest"] = _digest(stable)
        records.append(stable)
    # Keep the newest/effective row supplied for each evidence digest. Input order is a
    # caller-owned event order; this prevents duplicate receipts from inflating frequency.
    unique: dict[str, dict[str, Any]] = {}
    for row in records:
        unique[str(row["evidence_digest"])] = row
    records = sorted(unique.values(), key=lambda row: (row["feedback_kind"], row["feedback_id"]))
    result = {
        "ok": True,
        "contract_version": FEEDBACK_CONTRACT_VERSION,
        "records": records,
        "record_count": len(records),
        "rejected_count": rejected,
        "inactive_count": inactive,
        "deduplicated_count": len(records),
        "provider_contacted": False,
        "private_content_inspected": False,
        "runtime_mutated": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["feedback_digest"] = _digest([(row["evidence_digest"], row["feedback_digest"]) for row in records])
    return result


def feedback_as_initiative_inputs(feedback: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Translate content-free feedback to the established evidence intake classes."""
    operator: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    conversation: list[dict[str, Any]] = []
    for row in list(feedback.get("records") or []):
        base = {
            "finding_id": row.get("feedback_id"),
            "record_digest": row.get("evidence_digest"),
            "state": row.get("state"),
            "issue_domain": row.get("issue_domain"),
            "severity": row.get("severity"),
            "frequency": row.get("frequency"),
            "confidence": row.get("confidence"),
            "freshness": row.get("freshness"),
            "candidate_id": row.get("candidate_id"),
            "source_module": row.get("source_module"),
            "operator_confirmed": row.get("operator_confirmed"),
            "acceptance_criteria": row.get("acceptance_criteria"),
        }
        kind = str(row.get("feedback_kind") or "")
        if kind == "provider_failure" or kind == "action_failure":
            diagnostics.append(base)
        elif str(row.get("issue_domain") or "") in {"model_quality", "interface", "session_continuity", "conversation"}:
            conversation.append(base)
        else:
            operator.append(base)
    return {"operator_findings": operator, "diagnostics": diagnostics, "conversation_findings": conversation}


def development_feedback_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if _PRIVATE_FIELDS & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False


__all__ = [
    "CONTRACT_VERSION", "FINDING_CONTRACT_VERSION", "REPRODUCTION_CONTRACT_VERSION", "FEEDBACK_CONTRACT_VERSION",
    "development_finding_contract", "build_development_finding_projection",
    "reproduction_pipeline_contract", "build_synthetic_reproduction_scenario", "build_reproduction_pipeline",
    "live_feedback_contract", "normalize_live_feedback", "feedback_as_initiative_inputs",
    "development_feedback_contains_private_fields",
]
