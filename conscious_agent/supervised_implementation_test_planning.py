from __future__ import annotations

"""v1180.6-v1180.8 supervised implementation and test planning foundations.

Consumes only a caller-supplied, content-free v1180.5 specification bundle. It
creates bounded structural implementation and test-plan candidates. It never
reads source, writes source, creates patches, runs tests, grants authority, or
invokes a tool, provider, model, shell, or executor.
"""

import hashlib
import json
from typing import Any, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1180.8"
MAX_SPECIFICATIONS = 32
MAX_PLAN_ROWS = 32
MAX_REPORT_BYTES = 131_072
VALID_CATEGORIES = frozenset({
    "python_syntax_error", "unreadable_file", "unreadable_text",
    "oversized_file", "large_module", "maintenance_marker",
})
CATEGORY_IMPLEMENTATION_STEPS = {
    "python_syntax_error": ("prepare_minimal_parseability_change", "preserve_unrelated_behavior"),
    "unreadable_file": ("prepare_access_restoration_change", "preserve_file_identity"),
    "unreadable_text": ("prepare_encoding_normalization_change", "preserve_semantics"),
    "oversized_file": ("prepare_bounded_surface_reduction", "preserve_public_contract"),
    "large_module": ("prepare_cohesion_refactor", "preserve_public_contract"),
    "maintenance_marker": ("prepare_reviewed_maintenance_resolution", "preserve_unrelated_behavior"),
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _text(value: Any, limit: int = 160) -> str:
    return " ".join(str(value or "").split())[:limit]


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "planning_mode": "structural_content_free",
        "source_read": False,
        "source_modified": False,
        "patch_created": False,
        "patch_applied": False,
        "tests_executed": False,
        "approval_created": False,
        "authorization_created": False,
        "execution_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "shell_invoked": False,
        "project_registry_discovered": False,
        "raw_source_exposed": False,
        "raw_evidence_exposed": False,
        "operator_review_required": True,
        "content_free": True,
    }


def _valid_spec(spec: Mapping[str, Any], bundle: Mapping[str, Any]) -> bool:
    category = _text(spec.get("category"), 80)
    expected = {
        "candidate_id": _text(spec.get("candidate_id"), 80),
        "category": category,
        "severity": _text(spec.get("severity"), 16),
        "evidence_digest": _text(spec.get("evidence_digest"), 64),
        "decision_digest": _text(spec.get("decision_digest"), 64),
        "objective_codes": list(spec.get("objective_codes") or []),
        "acceptance_criteria_codes": list(spec.get("acceptance_criteria_codes") or []),
        "test_intent_codes": list(spec.get("test_intent_codes") or []),
        "risk_class": _text(spec.get("risk_class"), 16),
        "reversibility_required": spec.get("reversibility_required") is True,
        "operator_approval_required": spec.get("operator_approval_required") is True,
        "implementation_allowed": spec.get("implementation_allowed") is True,
    }
    digest = _digest({
        "review_digest": _text(bundle.get("review_digest"), 64),
        "inspection_digest": _text(bundle.get("inspection_digest"), 64),
        "scope_digest": _text(bundle.get("scope_digest"), 64),
        **expected,
    })
    return (
        category in VALID_CATEGORIES
        and bool(expected["candidate_id"])
        and len(expected["evidence_digest"]) == 64
        and len(expected["decision_digest"]) == 64
        and expected["reversibility_required"]
        and expected["operator_approval_required"]
        and not expected["implementation_allowed"]
        and _text(spec.get("specification_digest"), 64) == digest
        and _text(spec.get("specification_id"), 64) == f"spec-{digest[:20]}"
    )


def build_implementation_and_test_plans(specification_bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Create bounded structural plans from exact v1180.5 specifications."""
    base = _base()
    bundle_digest = _text(specification_bundle.get("specification_bundle_digest"), 64)
    review_digest = _text(specification_bundle.get("review_digest"), 64)
    inspection_digest = _text(specification_bundle.get("inspection_digest"), 64)
    scope_digest = _text(specification_bundle.get("scope_digest"), 64)
    valid_bundle = (
        specification_bundle.get("contract_version") == "v1180.5"
        and specification_bundle.get("content_free") is True
        and specification_bundle.get("source_modified") is False
        and specification_bundle.get("implementation_allowed") is False
        and specification_bundle.get("test_execution_allowed") is False
        and all(len(value) == 64 for value in (bundle_digest, review_digest, inspection_digest, scope_digest))
    )
    if not valid_bundle:
        result = {**base, "planning_status": "blocked", "block_reason": "invalid_specification_bundle", "plans": [], "plan_count": 0}
        result["planning_bundle_digest"] = _digest(result)
        return result

    plans: list[dict[str, Any]] = []
    seen: set[str] = set()
    invalid_count = 0
    for spec in list(specification_bundle.get("specifications") or [])[:MAX_SPECIFICATIONS]:
        spec_id = _text(spec.get("specification_id"), 64)
        if not spec_id or spec_id in seen or not _valid_spec(spec, specification_bundle):
            invalid_count += 1
            continue
        seen.add(spec_id)
        category = _text(spec.get("category"), 80)
        test_codes = [_text(v, 80) for v in list(spec.get("test_intent_codes") or [])[:12] if _text(v, 80)]
        acceptance = [_text(v, 80) for v in list(spec.get("acceptance_criteria_codes") or [])[:12] if _text(v, 80)]
        structural = {
            "specification_id": spec_id,
            "specification_digest": _text(spec.get("specification_digest"), 64),
            "candidate_id": _text(spec.get("candidate_id"), 80),
            "category": category,
            "risk_class": _text(spec.get("risk_class"), 16),
            "implementation_step_codes": list(CATEGORY_IMPLEMENTATION_STEPS[category]),
            "implementation_constraints": [
                "minimal_bounded_change", "preserve_privacy_boundary",
                "operator_review_before_patch", "rollback_required",
            ],
            "test_plan_codes": test_codes,
            "acceptance_criteria_codes": acceptance,
            "pre_change_checks": ["source_identity_match", "specification_digest_match", "clean_sandbox_required"],
            "post_change_checks": list(dict.fromkeys([*test_codes, "focused_regression", "source_privacy_scan"])),
            "rollback_plan_codes": ["restore_pre_change_snapshot", "rerun_focused_regression"],
            "patch_allowed": False,
            "test_execution_allowed": False,
            "implementation_authorized": False,
        }
        structural["implementation_plan_digest"] = _digest({"specification_bundle_digest": bundle_digest, **structural})
        structural["implementation_plan_id"] = f"impl-{structural['implementation_plan_digest'][:20]}"
        structural["test_plan_digest"] = _digest({
            "implementation_plan_digest": structural["implementation_plan_digest"],
            "pre_change_checks": structural["pre_change_checks"],
            "post_change_checks": structural["post_change_checks"],
            "acceptance_criteria_codes": structural["acceptance_criteria_codes"],
        })
        plans.append(structural)
        if len(plans) >= MAX_PLAN_ROWS:
            break

    result = {
        **base,
        "planning_status": "candidate_ready" if plans else "no_valid_specification",
        "specification_bundle_digest": bundle_digest,
        "review_digest": review_digest,
        "inspection_digest": inspection_digest,
        "scope_digest": scope_digest,
        "input_specification_count": min(len(list(specification_bundle.get("specifications") or [])), MAX_SPECIFICATIONS),
        "invalid_specification_count": invalid_count,
        "plan_count": len(plans),
        "plans": plans,
        "implementation_allowed": False,
        "test_execution_allowed": False,
    }
    result["planning_bundle_digest"] = _digest(result)
    if len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) > MAX_REPORT_BYTES:
        raise ValueError("Implementation and test planning report exceeded bounded size")
    return result


def implementation_test_planning_prompt(result: Mapping[str, Any]) -> str:
    return (
        "Bounded supervised implementation and test planning:\n"
        f"- Plan candidates: {int(result.get('plan_count') or 0)}.\n"
        "- These are structural plans, not patches or executable test commands.\n"
        "- Do not claim implementation, test execution, approval, authorization, or source modification."
    )
