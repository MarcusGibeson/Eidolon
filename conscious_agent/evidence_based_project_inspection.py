from __future__ import annotations

"""v1261.3-v1261.5 integration for evidence-based project assessment.

External runtime/test/operator/session signals are explicit inputs.  They are
normalized to status codes and digests before entering the assessment; raw
feedback, logs, test output, provider content, and private paths are not retained.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from evidence_based_project_inspection_foundations import (
    CLAIM_CLASSES, DENIED_AUTHORITY, EVIDENCE_KINDS, inspect_project_evidence,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1261.5"
EXTERNAL_KINDS = {"runtime_health", "operator_feedback", "known_limitation", "development_session", "tests", "environment"}
POLARITIES = {"supports", "contradicts", "neutral"}
STATUSES = {"healthy", "degraded", "failed", "blocked", "available", "unavailable", "present", "absent", "unknown", "passing", "failing", "completed", "active", "cancelled"}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _normalize_external(row: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(row.get("kind") or "").strip()
    if kind not in EXTERNAL_KINDS:
        raise ValueError("unsupported_external_evidence_kind")
    status = str(row.get("status") or "unknown").strip().casefold()
    if status not in STATUSES:
        status = "unknown"
    polarity = str(row.get("polarity") or "neutral").strip().casefold()
    if polarity not in POLARITIES:
        polarity = "neutral"
    claim_code = str(row.get("claim_code") or f"{kind}_signal").strip()[:128]
    source_digest = str(row.get("evidence_digest") or "").strip().casefold()
    if len(source_digest) != 64 or any(ch not in "0123456789abcdef" for ch in source_digest):
        source_digest = _digest({"kind": kind, "status": status, "claim_code": claim_code, "polarity": polarity, "source_ref": str(row.get("source_ref") or "")[:128]})
    clean = {
        "kind": kind, "status": status, "claim_code": claim_code, "polarity": polarity,
        "source_evidence_digest": source_digest,
        "freshness": str(row.get("freshness") or "unspecified")[:64],
        "confidence": str(row.get("confidence") or "medium")[:32],
        "content_minimized": True,
    }
    clean["evidence_id"] = f"ext_{_digest(clean)[:24]}"
    clean["evidence_digest"] = _digest(clean)
    return clean


def _replace_unknown(claims: list[dict[str, Any]], unknown_code: str, replacement: dict[str, Any]) -> None:
    claims[:] = [row for row in claims if str(row.get("claim_code") or "") != unknown_code]
    claims.append(replacement)


def build_evidence_based_project_assessment(
    source_root: str | Path,
    *,
    external_evidence: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    base = inspect_project_evidence(source_root)
    external = [_normalize_external(row) for row in external_evidence]
    claims = [dict(row) for row in base.get("claims") or []]
    kind_rows: dict[str, list[dict[str, Any]]] = {}
    for row in external:
        kind_rows.setdefault(row["kind"], []).append(row)
    mappings = {
        "runtime_health": ("runtime_health_unknown", "runtime_health_observed"),
        "operator_feedback": ("operator_feedback_unknown", "operator_feedback_observed"),
        "development_session": ("development_session_history_unknown", "development_session_history_observed"),
        "tests": ("executed_test_outcome_unknown", "executed_test_outcome_observed"),
    }
    for kind, (unknown_code, observed_code) in mappings.items():
        rows = kind_rows.get(kind) or []
        if rows:
            replacement = {
                "claim_class": "observed", "claim_code": observed_code,
                "confidence": "high" if all(r["confidence"] == "high" for r in rows) else "medium",
                "evidence_ids": [r["evidence_id"] for r in rows[:16]], "basis_code": "explicit_bounded_external_evidence",
            }
            replacement["claim_id"] = f"claim_{_digest(replacement)[:24]}"
            _replace_unknown(claims, unknown_code, replacement)
    if kind_rows.get("known_limitation"):
        row = {"claim_class": "observed", "claim_code": "known_limitations_observed", "confidence": "medium", "evidence_ids": [r["evidence_id"] for r in kind_rows["known_limitation"][:16]], "basis_code": "explicit_known_limitation_evidence"}
        row["claim_id"] = f"claim_{_digest(row)[:24]}"; claims.append(row)
    # Contradictions are evidence about uncertainty, not an invitation to choose whichever row is convenient.
    by_code: dict[str, set[str]] = {}
    for row in external:
        if row["polarity"] != "neutral":
            by_code.setdefault(row["claim_code"], set()).add(row["polarity"])
    contradictions = sorted(code for code, polarities in by_code.items() if {"supports", "contradicts"}.issubset(polarities))
    for code in contradictions:
        ids = [r["evidence_id"] for r in external if r["claim_code"] == code]
        row = {"claim_class": "unknown", "claim_code": f"conflicting_evidence:{code}", "confidence": "none", "evidence_ids": ids[:16], "basis_code": "explicit_evidence_disagrees"}
        row["claim_id"] = f"claim_{_digest(row)[:24]}"; claims.append(row)
    gaps = sorted({str(row.get("claim_code") or "") for row in claims if row.get("claim_class") == "unknown"})
    assessment = {
        "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "status": "evidence_based_project_assessment_ready", "inspection_digest": base.get("inspection_digest", ""),
        "source_manifest_digest": base.get("source_manifest_digest", ""), "project_type": base.get("project_type", ""),
        "adapter_id": base.get("adapter_id", ""), "evidence": list(base.get("evidence") or []) + external,
        "claims": claims, "claim_class_counts": {kind: sum(1 for row in claims if row.get("claim_class") == kind) for kind in CLAIM_CLASSES},
        "contradiction_codes": contradictions, "contradiction_count": len(contradictions),
        "evidence_gap_codes": gaps, "evidence_gap_count": len(gaps),
        "architecture_components": list(base.get("components") or []),
        "test_file_count": int(base.get("test_file_count") or 0), "documentation_file_count": int(base.get("documentation_file_count") or 0),
        "configuration_file_count": int(base.get("configuration_file_count") or 0),
        "maintenance_marker_count": int(base.get("maintenance_marker_count") or 0), "limitation_marker_count": int(base.get("limitation_marker_count") or 0),
        "assessment_creates_development_proposal": False, "assessment_creates_backlog": False,
        "raw_external_content_stored": False, "raw_test_output_stored": False, "raw_operator_feedback_stored": False,
        "private_runtime_discovery_performed": False, "content_minimized": True, "read_only": True,
        **DENIED_AUTHORITY,
    }
    assessment["assessment_digest"] = _digest(assessment)
    return assessment


def validate_project_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    supplied = str(assessment.get("assessment_digest") or "")
    valid = bool(supplied and supplied == _digest({key: value for key, value in assessment.items() if key != "assessment_digest"}))
    claims = list(assessment.get("claims") or [])
    classes_valid = all(str(row.get("claim_class") or "") in CLAIM_CLASSES for row in claims)
    return {
        "ok": valid and classes_valid,
        "status": "project_assessment_valid" if valid and classes_valid else "project_assessment_invalid",
        "digest_valid": valid, "claim_classes_valid": classes_valid,
        "assessment_digest": supplied, "read_only": True, **DENIED_AUTHORITY,
    }


def public_project_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(assessment.get("ok")), "status": str(assessment.get("status") or ""),
        "project_type": str(assessment.get("project_type") or ""), "adapter_id": str(assessment.get("adapter_id") or ""),
        "source_manifest_digest": str(assessment.get("source_manifest_digest") or ""),
        "claim_class_counts": dict(assessment.get("claim_class_counts") or {}),
        "contradiction_count": int(assessment.get("contradiction_count") or 0), "evidence_gap_count": int(assessment.get("evidence_gap_count") or 0),
        "component_count": len(assessment.get("architecture_components") or []), "test_file_count": int(assessment.get("test_file_count") or 0),
        "documentation_file_count": int(assessment.get("documentation_file_count") or 0), "configuration_file_count": int(assessment.get("configuration_file_count") or 0),
        "assessment_digest": str(assessment.get("assessment_digest") or ""), "raw_content_exposed": False,
        "private_runtime_content_exposed": False, "content_minimized": True, "read_only": True, **DENIED_AUTHORITY,
    }


__all__ = ["CONTRACT_VERSION", "build_evidence_based_project_assessment", "validate_project_assessment", "public_project_assessment"]
