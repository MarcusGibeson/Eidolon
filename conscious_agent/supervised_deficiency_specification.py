from __future__ import annotations

"""v1180.3-v1180.5 bounded deficiency review and specification foundations.

Consumes only a caller-supplied v1180 project-inspection report. It confirms or
rejects candidates through explicit operator decisions and may create a
content-free, digest-bound specification candidate. It never reads project files,
opens registries, drafts patches, grants authority, or invokes execution.
"""

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1180.5"
MAX_REVIEW_ROWS = 64
MAX_SPECIFICATIONS = 32
MAX_REPORT_BYTES = 131_072
VALID_DECISIONS = frozenset({"confirm", "reject", "defer"})
VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
CATEGORY_OBJECTIVES = {
    "python_syntax_error": ("restore_parseability", "preserve_existing_behavior"),
    "unreadable_file": ("restore_inspectability",),
    "unreadable_text": ("restore_text_decodability",),
    "oversized_file": ("reduce_inspection_surface", "preserve_existing_behavior"),
    "large_module": ("improve_module_cohesion", "preserve_existing_behavior"),
    "maintenance_marker": ("resolve_reviewed_maintenance_marker", "preserve_existing_behavior"),
}
CATEGORY_TESTS = {
    "python_syntax_error": ("python_compile", "focused_regression"),
    "unreadable_file": ("readability_probe",),
    "unreadable_text": ("encoding_probe",),
    "oversized_file": ("bounded_size_check", "focused_regression"),
    "large_module": ("structure_check", "focused_regression"),
    "maintenance_marker": ("focused_regression",),
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _bounded_text(value: Any, limit: int = 160) -> str:
    return " ".join(str(value or "").split())[:limit]


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "review_mode": "operator_explicit_content_free",
        "source_read": False,
        "project_registry_discovered": False,
        "raw_source_exposed": False,
        "raw_evidence_exposed": False,
        "specification_text_created": False,
        "patch_created": False,
        "source_modified": False,
        "approval_created": False,
        "authorization_created": False,
        "execution_invoked": False,
        "provider_contacted": False,
        "operator_review_required": True,
        "content_free": True,
    }


def review_deficiency_candidates(
    inspection: Mapping[str, Any],
    decisions: Mapping[str, str],
) -> dict[str, Any]:
    """Apply exact operator decisions to bounded inspection candidates."""
    base = _base()
    inspection_digest = _bounded_text(inspection.get("inspection_digest"), 64)
    scope_digest = _bounded_text(inspection.get("scope_digest"), 64)
    candidates = list(inspection.get("deficiency_candidates") or [])[:MAX_REVIEW_ROWS]
    valid_inspection = (
        inspection.get("contract_version") == "v1180.2"
        and len(inspection_digest) == 64
        and len(scope_digest) == 64
        and inspection.get("content_free") is True
        and inspection.get("source_modified") is False
    )
    if not valid_inspection:
        result = {**base, "review_status": "blocked", "block_reason": "invalid_inspection_contract", "review_rows": [], "confirmed_count": 0}
        result["review_digest"] = _digest(result)
        return result

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = _bounded_text(candidate.get("candidate_id"), 80)
        category = _bounded_text(candidate.get("category"), 80)
        evidence_digest = _bounded_text(candidate.get("evidence_digest"), 64)
        severity = _bounded_text(candidate.get("severity"), 16)
        if not candidate_id or candidate_id in seen or category not in CATEGORY_OBJECTIVES or len(evidence_digest) != 64 or severity not in VALID_SEVERITIES:
            continue
        seen.add(candidate_id)
        decision = _bounded_text(decisions.get(candidate_id), 16).lower()
        if decision not in VALID_DECISIONS:
            decision = "pending"
        row = {
            "candidate_id": candidate_id,
            "category": category,
            "severity": severity,
            "evidence_digest": evidence_digest,
            "decision": decision,
            "deficiency_confirmed": decision == "confirm",
            "specification_eligible": decision == "confirm",
        }
        row["decision_digest"] = _digest({"inspection_digest": inspection_digest, "scope_digest": scope_digest, **row})
        rows.append(row)

    confirmed = [row for row in rows if row["deficiency_confirmed"]]
    result = {
        **base,
        "review_status": "reviewed" if rows and all(row["decision"] != "pending" for row in rows) else "review_required",
        "inspection_digest": inspection_digest,
        "scope_digest": scope_digest,
        "review_row_count": len(rows),
        "confirmed_count": len(confirmed),
        "rejected_count": sum(row["decision"] == "reject" for row in rows),
        "deferred_count": sum(row["decision"] == "defer" for row in rows),
        "pending_count": sum(row["decision"] == "pending" for row in rows),
        "review_rows": rows,
    }
    result["review_digest"] = _digest(result)
    if len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) > MAX_REPORT_BYTES:
        raise ValueError("Deficiency review exceeded bounded size")
    return result


def build_specification_candidates(review: Mapping[str, Any]) -> dict[str, Any]:
    """Create bounded structural specifications from explicitly confirmed rows."""
    base = _base()
    review_digest = _bounded_text(review.get("review_digest"), 64)
    inspection_digest = _bounded_text(review.get("inspection_digest"), 64)
    scope_digest = _bounded_text(review.get("scope_digest"), 64)
    if len(review_digest) != 64 or len(inspection_digest) != 64 or len(scope_digest) != 64 or review.get("content_free") is not True:
        result = {**base, "specification_status": "blocked", "block_reason": "invalid_review_contract", "specifications": []}
        result["specification_bundle_digest"] = _digest(result)
        return result

    specs: list[dict[str, Any]] = []
    for row in list(review.get("review_rows") or [])[:MAX_REVIEW_ROWS]:
        if row.get("decision") != "confirm" or row.get("deficiency_confirmed") is not True:
            continue
        category = _bounded_text(row.get("category"), 80)
        if category not in CATEGORY_OBJECTIVES:
            continue
        decision_digest = _bounded_text(row.get("decision_digest"), 64)
        evidence_digest = _bounded_text(row.get("evidence_digest"), 64)
        candidate_id = _bounded_text(row.get("candidate_id"), 80)
        if len(decision_digest) != 64 or len(evidence_digest) != 64 or not candidate_id:
            continue
        structural = {
            "candidate_id": candidate_id,
            "category": category,
            "severity": _bounded_text(row.get("severity"), 16),
            "evidence_digest": evidence_digest,
            "decision_digest": decision_digest,
            "objective_codes": list(CATEGORY_OBJECTIVES[category]),
            "acceptance_criteria_codes": ["deficiency_condition_absent", "focused_tests_pass", "source_privacy_preserved"],
            "test_intent_codes": list(CATEGORY_TESTS[category]),
            "risk_class": "medium" if row.get("severity") in {"high", "critical"} else "low",
            "reversibility_required": True,
            "operator_approval_required": True,
            "implementation_allowed": False,
        }
        structural["specification_digest"] = _digest({"review_digest": review_digest, "inspection_digest": inspection_digest, "scope_digest": scope_digest, **structural})
        structural["specification_id"] = f"spec-{structural['specification_digest'][:20]}"
        specs.append(structural)
        if len(specs) >= MAX_SPECIFICATIONS:
            break

    result = {
        **base,
        "specification_status": "candidate_ready" if specs else "no_confirmed_deficiency",
        "inspection_digest": inspection_digest,
        "scope_digest": scope_digest,
        "review_digest": review_digest,
        "specification_count": len(specs),
        "specifications": specs,
        "implementation_allowed": False,
        "test_execution_allowed": False,
    }
    result["specification_bundle_digest"] = _digest(result)
    if len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) > MAX_REPORT_BYTES:
        raise ValueError("Specification candidate report exceeded bounded size")
    return result


def specification_foundation_prompt(result: Mapping[str, Any]) -> str:
    return (
        "Bounded deficiency review and specification foundation:\n"
        f"- Specification candidates: {int(result.get('specification_count') or 0)}.\n"
        "- These are structural candidates, not patch instructions.\n"
        "- Do not claim implementation, testing, approval, execution, or source modification."
    )
