from __future__ import annotations

"""v1276.0-.2 evidence-first architecture boundary foundations."""

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "v1276.2"
BASELINE_PARENT_LINES = {
    "conscious_agent/self_maintenance.py": 46614,
    "conscious_agent/dashboard.py": 17585,
    "conscious_agent/api_server.py": 9652,
}
EXTRACTIONS = {
    "release_evidence": {
        "parent": "conscious_agent/self_maintenance.py",
        "child": "conscious_agent/release_evidence_boundary.py",
        "names": (
            "_is_metadata_drift_tolerant_path", "_evidence_manifest_entries", "_canonical_json_hash",
            "_canonical_manifest_payload", "_canonical_evidence_payload", "_validate_canonical_manifest_payload",
            "_validate_canonical_evidence_payload", "_signing_payload",
        ),
        "reason": "canonical release-evidence hashing/build/validation is a cohesive read-only domain with no route ownership",
        "minimum_reduction": 150,
    },
    "development_campaign_panel": {
        "parent": "conscious_agent/dashboard.py",
        "child": "conscious_agent/dashboard_development_campaign_panel.py",
        "names": ("_development_campaign_panel",),
        "reason": "the panel is a dependency-free static renderer with an established dashboard wrapper boundary",
        "minimum_reduction": 250,
    },
    "api_request_boundary": {
        "parent": "conscious_agent/api_server.py",
        "child": "conscious_agent/api_request_boundary.py",
        "names": (
            "ApiError", "_now", "_to_jsonable", "_query_release_zip_path", "_query_path",
            "_query_signature_options", "_path_parts", "_query_bool", "_body_bool", "_require_confirmation",
            "parse_request_body",
        ),
        "reason": "request decoding/path validation is transport-adjacent and independent of route dispatch authority",
        "minimum_reduction": 75,
    },
}
AUTHORITY_FLAGS = {
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "release_authorized": False,
    "autonomy_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _definitions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def assess_extraction_candidate(*, name: str, cohesion_evidence: list[str], behavior_evidence: list[str], dependency_count: int, authority_owner: bool = False) -> dict[str, Any]:
    reasons = [str(row).strip() for row in cohesion_evidence if str(row).strip()]
    behavior = [str(row).strip() for row in behavior_evidence if str(row).strip()]
    blocked = []
    if not reasons:
        blocked.append("missing_cohesion_evidence")
    if not behavior:
        blocked.append("missing_behavior_evidence")
    if dependency_count < 0:
        blocked.append("invalid_dependency_count")
    if dependency_count > 24:
        blocked.append("dependency_surface_too_broad")
    if authority_owner:
        blocked.append("authority_owning_boundary_requires_separate_governance_review")
    accepted = not blocked
    result = {
        "name": name,
        "accepted": accepted,
        "status": "candidate_supported" if accepted else "candidate_rejected",
        "cohesion_evidence_count": len(reasons),
        "behavior_evidence_count": len(behavior),
        "dependency_count": dependency_count,
        "blockers": blocked,
        "aesthetic_size_only_is_insufficient": True,
        **AUTHORITY_FLAGS,
    }
    result["assessment_digest"] = _digest(result)
    return result


def build_architecture_boundary_inventory(source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    rows = []
    for boundary, spec in EXTRACTIONS.items():
        parent = root / spec["parent"]
        child = root / spec["child"]
        parent_defs = _definitions(parent)
        child_defs = _definitions(child)
        missing_child = sorted(set(spec["names"]) - child_defs)
        lingering_parent = sorted(set(spec["names"]) & parent_defs)
        parent_lines = _line_count(parent)
        baseline = BASELINE_PARENT_LINES[spec["parent"]]
        reduction = baseline - parent_lines
        rows.append({
            "boundary": boundary,
            "parent": spec["parent"],
            "child": spec["child"],
            "reason": spec["reason"],
            "baseline_parent_lines": baseline,
            "current_parent_lines": parent_lines,
            "line_reduction": reduction,
            "minimum_reduction": spec["minimum_reduction"],
            "child_present": child.is_file(),
            "missing_child_definitions": missing_child,
            "lingering_parent_definitions": lingering_parent,
            "historical_surface_import_present": all(name in parent.read_text(encoding="utf-8") for name in spec["names"]),
            "ok": child.is_file() and not missing_child and not lingering_parent and reduction >= int(spec["minimum_reduction"]),
        })
    result = {
        "contract_version": CONTRACT_VERSION,
        "status": "architecture_boundaries_evidence_backed" if all(row["ok"] for row in rows) else "architecture_boundary_blocked",
        "ok": all(row["ok"] for row in rows),
        "rows": rows,
        "boundary_count": len(rows),
        "read_only": True,
        "aesthetic_refactor_authorized": False,
        **AUTHORITY_FLAGS,
    }
    result["inventory_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "BASELINE_PARENT_LINES", "EXTRACTIONS", "AUTHORITY_FLAGS", "assess_extraction_candidate", "build_architecture_boundary_inventory"]
