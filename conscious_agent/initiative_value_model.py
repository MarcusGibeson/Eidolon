from __future__ import annotations

"""Portable v1509-v1516 capability-value model for supervised development.

The model ranks attributable evidence for operator review.  It is deterministic,
content-free, provider-free, and authority-inert.  A score is not permission to
create a proposal or execute development work.
"""

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


CONTRACT_VERSION = "v1516.9"
FACTOR_NAMES = (
    "user_impact",
    "frequency",
    "severity",
    "confidence",
    "reversibility",
    "effort_fit",
    "dependency_readiness",
    "strategic_value",
    "evidence_quality",
)

_SEVERITY = {
    "none": 0.05,
    "minor": 0.2,
    "low": 0.25,
    "medium": 0.55,
    "major": 0.8,
    "high": 0.82,
    "blocking": 1.0,
    "critical": 1.0,
}
_FRESHNESS = {"current": 1.0, "current_source_snapshot": 1.0, "recent": 0.9, "aging": 0.65, "stale": 0.35, "unknown": 0.55}
_STRATEGIC = {
    "security_debt": 0.95,
    "operator_reported_defect": 0.9,
    "conversation_quality_finding": 0.88,
    "performance_regression": 0.82,
    "missing_capability": 0.8,
    "failing_test": 0.74,
    "diagnostic_finding": 0.62,
    "structural_debt": 0.32,
}
_WEIGHTS = {
    "user_impact": 0.20,
    "frequency": 0.10,
    "severity": 0.13,
    "confidence": 0.09,
    "reversibility": 0.09,
    "effort_fit": 0.09,
    "dependency_readiness": 0.08,
    "strategic_value": 0.11,
    "evidence_quality": 0.11,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _bounded(value: Any, default: float = 0.0) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return round(max(0.0, min(1.0, default)), 4)


def _candidate_map(candidates: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("candidate_id") or ""): dict(row)
        for row in candidates
        if isinstance(row, Mapping) and str(row.get("candidate_id") or "")
    }


def _reversibility(candidate: Mapping[str, Any], evidence: Mapping[str, Any]) -> float:
    if "reversibility" in candidate:
        return _bounded(candidate.get("reversibility"), 0.65)
    if "reversibility_score" in candidate:
        return _bounded(candidate.get("reversibility_score"), 0.65)
    classification = str(candidate.get("reversibility_classification") or "").lower()
    if "bounded" in classification or "wrapper" in classification or "isolated" in classification:
        return 0.9
    if evidence.get("implementation_ready"):
        return 0.72
    return 0.55


def _effort_fit(candidate: Mapping[str, Any], evidence: Mapping[str, Any]) -> float:
    explicit = candidate.get("effort_fit")
    if explicit is not None:
        return _bounded(explicit, 0.5)
    try:
        dependencies = max(0, int(candidate.get("estimated_dependency_count") or 0))
    except (TypeError, ValueError):
        dependencies = 0
    try:
        symbols = max(0, len(candidate.get("source_symbols") or ()))
    except TypeError:
        symbols = 0
    if not candidate and not evidence.get("implementation_ready"):
        return 0.25
    cost = 0.7 * min(1.0, dependencies / 36.0) + 0.3 * min(1.0, symbols / 10.0)
    return round(max(0.0, 1.0 - cost), 4)


def _dependency_readiness(candidate: Mapping[str, Any], evidence: Mapping[str, Any]) -> float:
    explicit_risk = candidate.get("dependency_risk")
    if explicit_risk is not None:
        return round(1.0 - _bounded(explicit_risk), 4)
    try:
        dependencies = max(0, int(candidate.get("estimated_dependency_count") or 0))
    except (TypeError, ValueError):
        dependencies = 0
    if not candidate and not evidence.get("implementation_ready"):
        return 0.2
    return round(max(0.0, 1.0 - min(1.0, dependencies / 30.0)), 4)


def _evidence_quality(evidence: Mapping[str, Any]) -> float:
    confidence = _bounded(evidence.get("effective_confidence", evidence.get("confidence")), 0.5)
    freshness = _FRESHNESS.get(str(evidence.get("freshness") or "unknown").lower(), 0.55)
    provenance = 1.0 if str(evidence.get("source_evidence_digest") or evidence.get("provenance_id") or "") else 0.25
    operator = 1.0 if evidence.get("operator_confirmed") or evidence.get("review_state") == "confirmed" else 0.75
    return round(0.35 * confidence + 0.25 * freshness + 0.25 * provenance + 0.15 * operator, 4)


def initiative_value_contract() -> dict[str, Any]:
    result = {
        "contract_version": CONTRACT_VERSION,
        "factors": list(FACTOR_NAMES),
        "weights": dict(_WEIGHTS),
        "penalty_rules": [
            "structural_only_value_ceiling",
            "duplicate_lineage_penalty",
            "busywork_penalty",
            "metric_gaming_penalty",
            "stale_evidence_penalty",
            "deferred_or_cancelled_ineligible",
            "unbound_high_value_evidence_never_pretends_to_be_executable",
        ],
        "score_is_authority": False,
        "provider_contacted": False,
        "source_modified": False,
        "content_free": True,
    }
    result["contract_digest"] = _digest(result)
    return result


def score_initiative_value(
    evidence: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any] | None = None,
    prior_candidate_ids: Sequence[str] = (),
) -> dict[str, Any]:
    row = dict(evidence or {})
    candidate_row = dict(candidate or {})
    evidence_class = str(row.get("evidence_class") or "structural_debt")
    severity_name = str(row.get("effective_severity") or row.get("severity") or "medium").lower()
    impact = _bounded(row.get("user_impact", row.get("impact_score")), 0.0)
    factors = {
        "user_impact": impact,
        "frequency": _bounded(row.get("frequency_score"), 0.15),
        "severity": _SEVERITY.get(severity_name, _SEVERITY["medium"]),
        "confidence": _bounded(row.get("effective_confidence", row.get("confidence")), 0.5),
        "reversibility": _reversibility(candidate_row, row),
        "effort_fit": _effort_fit(candidate_row, row),
        "dependency_readiness": _dependency_readiness(candidate_row, row),
        "strategic_value": _bounded(row.get("strategic_value"), _STRATEGIC.get(evidence_class, 0.5)),
        "evidence_quality": _evidence_quality(row),
    }
    base_score = sum(_WEIGHTS[name] * factors[name] for name in FACTOR_NAMES)
    penalties: list[dict[str, Any]] = []

    structural_only = bool(row.get("structural_only")) or evidence_class == "structural_debt"
    if structural_only:
        penalties.append({"code": "structural_only", "amount": 0.12})
    candidate_id = str(row.get("candidate_id") or candidate_row.get("candidate_id") or "")
    if candidate_id and candidate_id in {str(value) for value in prior_candidate_ids}:
        penalties.append({"code": "duplicate_lineage", "amount": 0.32})
    if structural_only and impact <= 0.42 and factors["effort_fit"] >= 0.85:
        penalties.append({"code": "easy_low_value_busywork", "amount": 0.10})
    # Test-count abundance is intentionally excluded from positive scoring.  If a
    # structural candidate leans on unusually high test counts while impact is
    # weak, treat that as a metric-gaming warning rather than extra value.
    try:
        test_count = max(0, int(candidate_row.get("test_reference_file_count") or 0))
    except (TypeError, ValueError):
        test_count = 0
    if structural_only and test_count >= 25 and impact < 0.5:
        penalties.append({"code": "metric_gaming_guard", "amount": 0.08})
    if str(row.get("freshness") or "").lower() == "stale":
        penalties.append({"code": "stale_evidence", "amount": 0.10})

    review_state = str(row.get("review_state") or "unreviewed")
    selection_eligible = bool(row.get("implementation_ready")) and review_state not in {"deferred", "cancelled"}
    if review_state in {"deferred", "cancelled"}:
        penalties.append({"code": f"operator_{review_state}", "amount": 1.0})
    total_penalty = min(1.0, sum(float(item["amount"]) for item in penalties))
    value_score = round(max(0.0, min(1.0, base_score - total_penalty)), 4)
    if structural_only:
        value_score = min(value_score, 0.48)
    if review_state in {"deferred", "cancelled"}:
        value_score = 0.0

    result = {
        "contract_version": CONTRACT_VERSION,
        "evidence_id": str(row.get("evidence_id") or ""),
        "evidence_digest": str(row.get("evidence_digest") or ""),
        "evidence_class": evidence_class,
        "candidate_id": candidate_id,
        "source_module": str(row.get("source_module") or candidate_row.get("source_module") or ""),
        "issue_domain": str(row.get("issue_domain") or "unknown"),
        "factors": {name: round(float(factors[name]), 4) for name in FACTOR_NAMES},
        "base_score": round(base_score, 4),
        "penalties": penalties,
        "penalty_total": round(total_penalty, 4),
        "value_score": round(value_score, 4),
        "selection_eligible": selection_eligible,
        "implementation_ready": bool(row.get("implementation_ready")),
        "structural_only": structural_only,
        "operator_review_state": review_state,
        "acceptance_criteria": list(row.get("effective_acceptance_criteria") or row.get("acceptance_criteria") or ()),
        "practical_benefit": str(row.get("practical_benefit") or ""),
        "content_free": True,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
    }
    result["value_digest"] = _digest(result)
    return result


def build_initiative_value_model(
    evidence_review: Mapping[str, Any] | None,
    *,
    candidates: Iterable[Mapping[str, Any]] = (),
    prior_candidate_ids: Sequence[str] = (),
) -> dict[str, Any]:
    review = dict(evidence_review or {})
    candidate_by_id = _candidate_map(candidates)
    scored = [
        score_initiative_value(
            row,
            candidate=candidate_by_id.get(str(row.get("candidate_id") or ""), {}),
            prior_candidate_ids=prior_candidate_ids,
        )
        for row in review.get("records") or ()
        if isinstance(row, Mapping)
    ]
    scored.sort(key=lambda row: (-float(row["value_score"]), -float(row["factors"]["evidence_quality"]), row["evidence_id"]))
    executable = [row for row in scored if row["selection_eligible"]]
    unbound = [row for row in scored if not row["implementation_ready"] and row["value_score"] >= 0.55]
    highest = scored[0] if scored else {}
    highest_executable = executable[0] if executable else {}
    result = {
        "ok": True,
        "status": "initiative_value_model_ready",
        "contract_version": CONTRACT_VERSION,
        "records": scored,
        "record_count": len(scored),
        "selection_eligible_count": len(executable),
        "unbound_high_value_count": len(unbound),
        "highest_value_evidence_id": str(highest.get("evidence_id") or ""),
        "highest_value_score": float(highest.get("value_score") or 0.0),
        "highest_executable_evidence_id": str(highest_executable.get("evidence_id") or ""),
        "highest_executable_score": float(highest_executable.get("value_score") or 0.0),
        "busywork_resistance_active": True,
        "metric_gaming_resistance_active": True,
        "score_is_authority": False,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["value_model_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "records": [(row["evidence_id"], row["value_digest"]) for row in scored],
    })
    return result


__all__ = [
    "CONTRACT_VERSION",
    "FACTOR_NAMES",
    "initiative_value_contract",
    "score_initiative_value",
    "build_initiative_value_model",
]
