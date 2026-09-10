from __future__ import annotations

"""v1289.0-v1289.2 product-quality evidence and dimension foundations."""

from collections import defaultdict
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v1289.2"
DIMENSIONS = (
    "coherence", "usability", "accessibility", "maintainability", "completeness", "operator_readiness",
)
EVIDENCE_STATES = {"pass", "warn", "fail", "unknown"}
EVIDENCE_TYPES = {
    "deterministic_test", "integration_test", "regression_test", "static_analysis",
    "maintainability_review", "usability_review", "accessibility_review", "documentation_review",
    "requirements_review", "operator_walkthrough", "native_validation", "security_privacy_review",
}
REQUIRED_SPECIALIZED_EVIDENCE = {
    "coherence": {"integration_test", "requirements_review", "operator_walkthrough"},
    "usability": {"usability_review", "operator_walkthrough"},
    "accessibility": {"accessibility_review", "native_validation"},
    "maintainability": {"maintainability_review", "static_analysis"},
    "completeness": {"requirements_review", "integration_test", "operator_walkthrough"},
    "operator_readiness": {"operator_walkthrough", "native_validation"},
}
DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "project_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "self_update_authorized": False,
    "rollback_authorized": False,
    "release_authorized": False,
    "standing_authority_granted": False,
}


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def normalize_quality_evidence(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in rows:
        dimension = str(raw.get("dimension") or "").lower().strip()
        evidence_type = str(raw.get("evidence_type") or "").lower().strip()
        state = str(raw.get("state") or "unknown").lower().strip()
        digest = str(raw.get("evidence_digest") or "").lower().strip()
        scope_digest = str(raw.get("scope_digest") or digest or "").lower().strip()
        if dimension not in DIMENSIONS:
            raise ValueError("unsupported_quality_dimension")
        if evidence_type not in EVIDENCE_TYPES:
            raise ValueError("unsupported_quality_evidence_type")
        if state not in EVIDENCE_STATES:
            raise ValueError("unsupported_quality_evidence_state")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("quality_evidence_digest_required")
        if len(scope_digest) != 64 or any(ch not in "0123456789abcdef" for ch in scope_digest):
            raise ValueError("quality_scope_digest_required")
        key = (dimension, evidence_type, digest)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({
            "dimension": dimension,
            "evidence_type": evidence_type,
            "state": state,
            "evidence_digest": digest,
            "scope_digest": scope_digest,
            "critical": bool(raw.get("critical", False)),
            "fresh": bool(raw.get("fresh", True)),
            "content_free": True,
        })
    return sorted(normalized, key=lambda r: (r["dimension"], r["evidence_type"], r["evidence_digest"]))


def assess_quality_dimensions(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    evidence = normalize_quality_evidence(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        grouped[row["dimension"]].append(row)
    dimensions: dict[str, dict[str, Any]] = {}
    for dimension in DIMENSIONS:
        items = grouped.get(dimension, [])
        fresh = [row for row in items if row["fresh"]]
        types = {row["evidence_type"] for row in fresh}
        specialized = bool(types & REQUIRED_SPECIALIZED_EVIDENCE[dimension])
        failures = [row for row in fresh if row["state"] == "fail"]
        warnings = [row for row in fresh if row["state"] == "warn"]
        passes = [row for row in fresh if row["state"] == "pass"]
        unknowns = [row for row in fresh if row["state"] == "unknown"]
        if failures:
            state = "fail"
            reason = "negative_quality_evidence"
        elif not fresh:
            state = "unknown"
            reason = "no_fresh_quality_evidence"
        elif not specialized:
            state = "insufficient"
            reason = "specialized_evidence_required"
        elif unknowns and not passes:
            state = "unknown"
            reason = "quality_evidence_unknown"
        elif warnings or unknowns:
            state = "warn"
            reason = "known_quality_gap_or_uncertainty"
        elif passes:
            state = "pass"
            reason = "specialized_evidence_passed"
        else:
            state = "unknown"
            reason = "quality_not_established"
        dimensions[dimension] = {
            "state": state,
            "reason": reason,
            "fresh_evidence_count": len(fresh),
            "evidence_type_count": len(types),
            "specialized_evidence_present": specialized,
            "failure_count": len(failures),
            "warning_count": len(warnings),
            "unknown_count": len(unknowns),
            "evidence_digest": _digest(items),
            "content_free": True,
        }
    return {"contract_version": CONTRACT_VERSION, "dimensions": dimensions, "evidence_count": len(evidence), "evidence_digest": _digest(evidence), "content_free": True, "read_only": True, **DENIED_AUTHORITY}
