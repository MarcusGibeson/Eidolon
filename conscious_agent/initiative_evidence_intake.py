from __future__ import annotations

"""Content-free v1501.3 evidence intake for supervised initiatives.

The intake layer normalizes attributable development evidence without reading
private finding text or turning evidence into execution authority.  Candidate
selection remains advisory and implementation remains separately governed.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable, Mapping


CONTRACT_VERSION = "v1501.3"
EVIDENCE_CLASSES = (
    "operator_reported_defect",
    "failing_test",
    "diagnostic_finding",
    "performance_regression",
    "conversation_quality_finding",
    "missing_capability",
    "security_debt",
    "structural_debt",
)
PRIVATE_FIELDS = frozenset({
    "content",
    "details",
    "finding_details",
    "finding_title",
    "message",
    "messages",
    "note",
    "notes",
    "private_details",
    "private_note",
    "private_title",
    "prompt",
    "provider_payload",
    "raw_response",
    "response",
    "text",
    "transcript",
})

_SEVERITY = {
    "none": 0.1,
    "minor": 0.25,
    "low": 0.25,
    "medium": 0.55,
    "major": 0.8,
    "high": 0.8,
    "blocking": 1.0,
    "critical": 1.0,
}
_CLASS_VALUE = {
    "operator_reported_defect": 0.82,
    "failing_test": 0.78,
    "diagnostic_finding": 0.62,
    "performance_regression": 0.72,
    "conversation_quality_finding": 0.78,
    "missing_capability": 0.76,
    "security_debt": 0.88,
    "structural_debt": 0.24,
}
_DEFAULT_ACCEPTANCE = {
    "operator_reported_defect": ("reported_behavior_reproduced", "reported_behavior_repaired", "regression_fixture_passes"),
    "failing_test": ("failure_reproduced", "failing_test_passes", "affected_suite_remains_green"),
    "diagnostic_finding": ("diagnostic_warning_reproduced", "diagnostic_warning_resolved", "diagnostic_receipt_verified"),
    "performance_regression": ("baseline_timing_recorded", "target_budget_met", "no_correctness_regression"),
    "conversation_quality_finding": ("operator_scenario_reproduced", "targeted_conversation_fixture_passes", "operator_retrial_required"),
    "missing_capability": ("capability_contract_defined", "acceptance_scenario_passes", "authority_boundary_preserved"),
    "security_debt": ("security_finding_reproduced", "adversarial_fixture_passes", "authority_boundary_preserved"),
    "structural_debt": ("compatible_imports_preserved", "attributable_tests_pass", "source_manifest_boundary_preserved"),
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _bounded_float(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _frequency_score(row: Mapping[str, Any]) -> float:
    count = max(0, int(row.get("frequency") or row.get("recurrence_count") or row.get("attempt_count") or 0))
    return 0.15 if count <= 0 else 0.35 if count == 1 else 0.6 if count <= 3 else 0.85


def _freshness(row: Mapping[str, Any]) -> str:
    explicit = str(row.get("freshness") or "").strip().lower()
    if explicit in {"current", "recent", "aging", "stale", "current_source_snapshot"}:
        return explicit
    age_days = row.get("age_days")
    try:
        age = max(0.0, float(age_days))
    except (TypeError, ValueError):
        stamp = str(row.get("updated_at") or row.get("observed_at") or "")
        try:
            observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            age = max(0.0, (datetime.now(timezone.utc) - observed).total_seconds() / 86400.0)
        except (TypeError, ValueError):
            return "unknown"
    return "current" if age <= 1 else "recent" if age <= 14 else "aging" if age <= 60 else "stale"


def _acceptance_criteria(evidence_class: str, row: Mapping[str, Any]) -> list[str]:
    supplied = [
        str(value).strip()
        for value in row.get("acceptance_criteria") or ()
        if str(value).strip() and len(str(value).strip()) <= 80
    ]
    return list(dict.fromkeys(supplied or _DEFAULT_ACCEPTANCE[evidence_class]))[:8]


def _normalize(evidence_class: str, row: Mapping[str, Any]) -> dict[str, Any] | None:
    state = str(row.get("state") or "open").strip().lower()
    if state in {"resolved", "dismissed", "superseded", "retracted"}:
        return None
    candidate_id = str(row.get("candidate_id") or "")
    source_digest = str(
        row.get("record_digest")
        or row.get("evidence_digest")
        or row.get("failure_digest")
        or row.get("diagnostic_digest")
        or ""
    )
    provenance_id = str(
        row.get("finding_id")
        or row.get("test_id")
        or row.get("diagnostic_id")
        or row.get("observation_id")
        or candidate_id
        or source_digest
    )
    if not provenance_id and not source_digest:
        return None
    severity_name = str(row.get("severity") or ("low" if evidence_class == "structural_debt" else "medium")).lower()
    severity = _SEVERITY.get(severity_name, _SEVERITY["medium"])
    confidence = _bounded_float(row.get("confidence"), 0.7 if row.get("operator_confirmed") else 0.55)
    frequency = _frequency_score(row)
    class_value = _CLASS_VALUE[evidence_class]
    impact_score = round(.45 * class_value + .25 * severity + .15 * frequency + .15 * confidence, 4)
    if evidence_class == "structural_debt":
        impact_score = round(min(0.42, impact_score), 4)
    freshness = _freshness(row)
    stale = freshness == "stale"
    if stale:
        impact_score = round(impact_score * 0.6, 4)
    acceptance = _acceptance_criteria(evidence_class, row)
    implementation_ready = bool(candidate_id and row.get("source_module") and acceptance)
    issue_domain = str(row.get("issue_domain") or ("structural" if evidence_class == "structural_debt" else "unknown"))
    stable = {
        "evidence_class": evidence_class,
        "provenance_id": provenance_id,
        "source_evidence_digest": source_digest,
        "candidate_id": candidate_id,
        "source_module": str(row.get("source_module") or ""),
        "issue_domain": issue_domain,
        "severity": severity_name if severity_name in _SEVERITY else "medium",
        "frequency_score": frequency,
        "confidence": confidence,
        "freshness": freshness,
        "impact_score": impact_score,
        "practical_benefit": "maintainability_and_regression_risk_reduction" if evidence_class == "structural_debt" else "observable_product_or_capability_improvement",
        "acceptance_criteria": acceptance,
        "implementation_ready": implementation_ready,
        "capability_change_expected": evidence_class in {"missing_capability", "conversation_quality_finding"},
        "structural_only": evidence_class == "structural_debt",
        "operator_confirmed": bool(row.get("operator_confirmed")),
        "content_free": True,
    }
    stable["evidence_id"] = f"initev_{_digest(stable)[:24]}"
    stable["evidence_digest"] = _digest(stable)
    return stable


def _structural_rows(candidates: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        row = dict(candidate or {})
        normalized = _normalize("structural_debt", {
            **row,
            "severity": "low",
            "frequency": 1,
            "freshness": "current_source_snapshot",
            "source_evidence_digest": row.get("evidence_digest"),
            "acceptance_criteria": _DEFAULT_ACCEPTANCE["structural_debt"],
        })
        if normalized:
            rows.append(normalized)
    return rows


def build_initiative_evidence_intake(
    *,
    structural_candidates: Iterable[Mapping[str, Any]] = (),
    operator_findings: Iterable[Mapping[str, Any]] = (),
    failing_tests: Iterable[Mapping[str, Any]] = (),
    diagnostics: Iterable[Mapping[str, Any]] = (),
    performance_regressions: Iterable[Mapping[str, Any]] = (),
    conversation_findings: Iterable[Mapping[str, Any]] = (),
    capability_gaps: Iterable[Mapping[str, Any]] = (),
    security_findings: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Normalize public evidence projections without reading private content."""

    grouped = (
        ("operator_reported_defect", operator_findings),
        ("failing_test", failing_tests),
        ("diagnostic_finding", diagnostics),
        ("performance_regression", performance_regressions),
        ("conversation_quality_finding", conversation_findings),
        ("missing_capability", capability_gaps),
        ("security_debt", security_findings),
    )
    records = _structural_rows(structural_candidates)
    rejected_count = 0
    for evidence_class, values in grouped:
        for value in values:
            normalized = _normalize(evidence_class, dict(value or {}))
            if normalized:
                records.append(normalized)
            else:
                rejected_count += 1
    unique: dict[str, dict[str, Any]] = {}
    for row in records:
        unique.setdefault(str(row["evidence_digest"]), row)
    records = sorted(unique.values(), key=lambda row: (-float(row["impact_score"]), row["evidence_id"]))
    class_counts = {name: sum(row["evidence_class"] == name for row in records) for name in EVIDENCE_CLASSES}
    unbound = [row for row in records if not row["implementation_ready"] and row["impact_score"] >= 0.6]
    result = {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "records": records,
        "record_count": len(records),
        "rejected_or_inactive_count": rejected_count,
        "class_counts": class_counts,
        "implementation_ready_count": sum(bool(row["implementation_ready"]) for row in records),
        "unbound_priority_evidence_count": len(unbound),
        "highest_impact_score": float(records[0]["impact_score"]) if records else 0.0,
        "private_content_inspected": False,
        "provider_contacted": False,
        "proposal_created": False,
        "workspace_prepared": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["intake_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "records": [(row["evidence_id"], row["evidence_digest"]) for row in records],
        "class_counts": class_counts,
    })
    return result



def initiative_evidence_contract() -> dict[str, Any]:
    """Return the portable v1502-v1508 evidence contract without runtime access."""

    contract = {
        "contract_version": "v1508.9",
        "input_classes": list(EVIDENCE_CLASSES),
        "required_identity": ["provenance_id_or_source_digest"],
        "public_record_fields": [
            "evidence_id", "evidence_digest", "evidence_class", "provenance_id",
            "source_evidence_digest", "candidate_id", "source_module", "issue_domain",
            "severity", "frequency_score", "confidence", "freshness", "impact_score",
            "practical_benefit", "acceptance_criteria", "implementation_ready",
            "capability_change_expected", "structural_only", "operator_confirmed",
            "content_free",
        ],
        "lifecycle_states_ignored_for_selection": ["resolved", "dismissed", "superseded", "retracted"],
        "provenance_rules": [
            "preserve_source_evidence_digest_when_supplied",
            "derive_stable_public_evidence_identity_from_content_free_fields",
            "never_copy_private_finding_text_into_public_evidence",
            "freshness_is_explicit_or_derived_from_attributable_timestamp",
        ],
        "compatibility_rules": [
            "structural_candidates_remain_supported",
            "unbound_high_impact_evidence_remains_visible",
            "unknown_optional_fields_are_ignored_not_executed",
        ],
        "failure_states": [
            "missing_identity_rejected",
            "inactive_evidence_rejected",
            "malformed_optional_values_bounded",
            "private_fields_redacted",
        ],
        "authority_boundary": {
            "proposal_creation_authorized": False,
            "workspace_preparation_authorized": False,
            "provider_contact_authorized": False,
            "source_mutation_authorized": False,
            "approval_granted": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "independent_authority_granted": False,
        },
        "content_free": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract

def public_evidence_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if PRIVATE_FIELDS.intersection(str(key) for key in current):
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False


__all__ = [
    "CONTRACT_VERSION",
    "EVIDENCE_CLASSES",
    "build_initiative_evidence_intake",
    "initiative_evidence_contract",
    "public_evidence_contains_private_fields",
]
