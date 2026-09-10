from __future__ import annotations

"""v1258.0-v1258.2 Complete Application Construction foundations.

The foundation turns an existing v1254 coding request/inspection/plan into one
sealed application-construction contract.  It describes the application as a
set of cooperating artifact roles and cross-file quality obligations instead
of treating a provider response as an unrelated pile of files.  It is entirely
provider-free and command-free and grants no execution or application
authority.
"""

import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from isolated_coding_execution_foundations import (
    check_coding_source_freshness,
    load_coding_project_inspection,
    load_coding_work_plan,
    load_coding_work_request,
)
from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1258.2"
MAX_ARTIFACT_ROLES = 12
MAX_RELATIONSHIPS = 24

DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "construction_execution_authorized": False,
    "test_execution_authorized": False,
    "dependency_installation_authorized": False,
    "network_authorized": False,
    "application_authorized": False,
    "rollback_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}

_WEB_TYPES = {"static_web_project", "javascript_web_project"}


def _record_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "complete_application_construction" / f"{request_id}.json"


def _seal(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({k: v for k, v in row.items() if k != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != field}))


def _failure(status: str, request_id: str = "") -> dict[str, Any]:
    row = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "request_id": request_id,
        "content_minimized": True,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    row["failure_digest"] = _digest(row)
    return row


def _paths(inspection: Mapping[str, Any]) -> list[str]:
    return [str(row.get("relative_path") or "") for row in inspection.get("inventory") or [] if row.get("relative_path")]


def _has_suffix(paths: Sequence[str], suffixes: Iterable[str]) -> bool:
    accepted = {str(value).casefold() for value in suffixes}
    return any(PurePosixPath(path).suffix.casefold() in accepted for path in paths)


def _first_named(paths: Sequence[str], names: Iterable[str]) -> str:
    accepted = {str(value).casefold() for value in names}
    for path in paths:
        if PurePosixPath(path).name.casefold() in accepted:
            return path
    return ""


def _role(role: str, *, required: bool, purpose: str, preferred_paths: Sequence[str], acceptance: Sequence[str]) -> dict[str, Any]:
    row = {
        "role": role,
        "required": bool(required),
        "purpose": purpose,
        "preferred_paths": list(preferred_paths)[:6],
        "acceptance_codes": list(acceptance)[:8],
    }
    row["role_digest"] = _digest(row)
    return row


def _web_roles(paths: Sequence[str]) -> list[dict[str, Any]]:
    html = _first_named(paths, ["index.html", "index.htm"]) or "index.html"
    js = _first_named(paths, ["app.js", "main.js", "index.js", "script.js"]) or "app.js"
    css = _first_named(paths, ["styles.css", "style.css", "app.css", "main.css"]) or "styles.css"
    config = _first_named(paths, ["package.json"]) or "package.json"
    readme = _first_named(paths, ["README.md", "README.txt"]) or "README.md"
    tests = [p for p in paths if PurePosixPath(p).name.casefold().endswith((".test.js", ".spec.js")) or "test" in PurePosixPath(p).parts]
    return [
        _role("interface", required=True, purpose="user-facing semantic interface", preferred_paths=[html], acceptance=["document_language", "viewport_declared", "semantic_main", "control_accessibility"]),
        _role("application_logic", required=True, purpose="coherent interactive behavior", preferred_paths=[js], acceptance=["interface_binding", "bounded_state", "no_missing_local_imports"]),
        _role("styles", required=True, purpose="usable visual layout", preferred_paths=[css], acceptance=["responsive_breakpoint", "focus_visibility", "layout_not_fixed_only"]),
        _role("configuration", required=True, purpose="deterministic local project configuration", preferred_paths=[config], acceptance=["valid_configuration", "test_command_declared", "dependencies_declared"]),
        _role("tests", required=True, purpose="project-owned behavior verification", preferred_paths=tests or ["tests/app.test.js"], acceptance=["test_artifact_present", "behavior_coverage_declared"]),
        _role("documentation", required=True, purpose="operator/developer run and test guidance", preferred_paths=[readme], acceptance=["run_guidance", "test_guidance", "scope_documented"]),
    ]


def _python_roles(paths: Sequence[str]) -> list[dict[str, Any]]:
    source = next((p for p in paths if p.endswith(".py") and "test" not in PurePosixPath(p).name.casefold()), "main.py")
    tests = [p for p in paths if p.endswith(".py") and (PurePosixPath(p).name.casefold().startswith("test_") or "tests" in [x.casefold() for x in PurePosixPath(p).parts])]
    config = _first_named(paths, ["pyproject.toml", "requirements.txt", "setup.cfg", "setup.py"]) or "pyproject.toml"
    readme = _first_named(paths, ["README.md", "README.txt"]) or "README.md"
    return [
        _role("application_logic", required=True, purpose="coherent application behavior", preferred_paths=[source], acceptance=["entry_behavior_present", "bounded_interfaces"]),
        _role("configuration", required=True, purpose="deterministic local project configuration", preferred_paths=[config], acceptance=["valid_configuration", "dependencies_declared_or_explicitly_empty"]),
        _role("tests", required=True, purpose="project-owned behavior verification", preferred_paths=tests or ["tests/test_app.py"], acceptance=["test_artifact_present", "behavior_coverage_declared"]),
        _role("documentation", required=True, purpose="operator/developer run and test guidance", preferred_paths=[readme], acceptance=["run_guidance", "test_guidance", "scope_documented"]),
    ]


def _generic_roles(paths: Sequence[str]) -> list[dict[str, Any]]:
    source = paths[:3] or ["src/main"]
    readme = _first_named(paths, ["README.md", "README.txt"]) or "README.md"
    return [
        _role("application_logic", required=True, purpose="coherent application behavior", preferred_paths=source, acceptance=["entry_behavior_present"]),
        _role("tests", required=True, purpose="project-owned behavior verification", preferred_paths=["tests/"], acceptance=["test_artifact_present"]),
        _role("documentation", required=True, purpose="operator/developer run and test guidance", preferred_paths=[readme], acceptance=["run_guidance", "test_guidance"]),
    ]


def _relationships(project_type: str, roles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    available = {str(row.get("role") or "") for row in roles}
    pairs: list[tuple[str, str, str]] = [
        ("tests", "application_logic", "tests_verify_application_behavior"),
        ("documentation", "configuration", "documentation_matches_run_and_test_configuration"),
    ]
    if project_type in _WEB_TYPES:
        pairs.extend([
            ("interface", "application_logic", "interface_loads_and_binds_application_logic"),
            ("interface", "styles", "interface_loads_styles"),
            ("styles", "interface", "responsive_and_focus_styles_cover_user_interface"),
            ("configuration", "tests", "configuration_exposes_bounded_test_command"),
        ])
    rows = []
    for source, target, obligation in pairs:
        if source not in available or target not in available:
            continue
        row = {"from_role": source, "to_role": target, "obligation": obligation}
        row["relationship_digest"] = _digest(row)
        rows.append(row)
    return rows[:MAX_RELATIONSHIPS]


def _quality_dimensions(project_type: str) -> list[dict[str, Any]]:
    rows = [
        {"dimension": "interface_coherence", "required": True},
        {"dimension": "dependency_coherence", "required": True},
        {"dimension": "configuration_coherence", "required": True},
        {"dimension": "test_coverage", "required": True},
        {"dimension": "documentation_completeness", "required": True},
    ]
    rows.extend([
        {"dimension": "accessibility", "required": project_type in _WEB_TYPES, "not_applicable_reason": "non_web_project" if project_type not in _WEB_TYPES else ""},
        {"dimension": "responsive_behavior", "required": project_type in _WEB_TYPES, "not_applicable_reason": "non_web_project" if project_type not in _WEB_TYPES else ""},
    ])
    return rows


def _looks_like_complete_application(request: Mapping[str, Any], inspection: Mapping[str, Any]) -> bool:
    text = " ".join([
        str(request.get("user_objective") or ""),
        *[str(x) for x in request.get("requirements") or []],
        *[str(x) for x in request.get("expected_artifacts") or []],
    ]).casefold()
    cues = ("application", "web app", "website", "complete app", "multi-file", "responsive", "accessible", "accessibility", "frontend")
    return any(cue in text for cue in cues)


def prepare_complete_application_construction(request_id: str, *, runtime_root=None, force: bool = False) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    with _proposal_lock(request_id, runtime_root):
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
        plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
        if not request or not inspection or not plan:
            return _failure("complete_application_construction_lineage_missing", request_id)
        if request.get("cancelled"):
            return _failure("complete_application_construction_request_cancelled", request_id)
        freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
        if freshness.get("ok") is not True:
            return _failure("complete_application_construction_stale_source", request_id)
        if not force and not _looks_like_complete_application(request, inspection):
            return _failure("complete_application_construction_not_required", request_id)
        path = _record_path(request_id, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "construction_contract_digest"):
                return _failure("complete_application_construction_record_invalid", request_id)
            expected = (str(request.get("request_digest") or ""), str(inspection.get("inspection_digest") or ""), str(plan.get("plan_digest") or ""))
            actual = (str(existing.get("request_digest") or ""), str(existing.get("inspection_digest") or ""), str(existing.get("plan_digest") or ""))
            if expected != actual:
                return _failure("complete_application_construction_lineage_stale", request_id)
            return {**existing, "operation_status": "restored"}

        project_type = str(inspection.get("project_type") or "")
        paths = _paths(inspection)
        if project_type in _WEB_TYPES or _has_suffix(paths, {".html", ".css"}):
            profile = "web_application"
            roles = _web_roles(paths)
        elif project_type == "python_project" or _has_suffix(paths, {".py"}):
            profile = "python_application"
            roles = _python_roles(paths)
        else:
            profile = "general_application"
            roles = _generic_roles(paths)
        relationships = _relationships(project_type, roles)
        dimensions = _quality_dimensions(project_type)
        record = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "complete_application_construction_contract_ready",
            "request_id": request_id,
            "request_digest": str(request.get("request_digest") or ""),
            "inspection_digest": str(inspection.get("inspection_digest") or ""),
            "plan_digest": str(plan.get("plan_digest") or ""),
            "source_manifest_digest": str(inspection.get("source_manifest_digest") or ""),
            "project_type": project_type,
            "construction_profile": profile,
            "artifact_roles": roles[:MAX_ARTIFACT_ROLES],
            "artifact_role_count": len(roles[:MAX_ARTIFACT_ROLES]),
            "relationships": relationships,
            "relationship_count": len(relationships),
            "quality_dimensions": dimensions,
            "required_quality_dimensions": [row["dimension"] for row in dimensions if row.get("required")],
            "completion_conditions": [
                "Every required artifact role is satisfied by a contained workspace file.",
                "Cross-file references and declared configuration are internally coherent.",
                "Project-owned tests pass under the existing bounded verifier.",
                "Documentation explains bounded local run and test behavior.",
                "Web applications satisfy structural accessibility and responsive-layout checks.",
                "The result remains a reviewable isolated candidate until separately authorized application.",
            ],
            "blocker_conditions": [
                "A required artifact or relationship cannot be produced within the bounded workspace.",
                "Dependency installation or network access would be required without separate authority.",
                "Configuration or local references are missing or contradictory.",
                "Required tests cannot run safely under the existing verifier.",
                "Source becomes stale or the workspace fails containment/integrity checks.",
            ],
            "dependency_policy": {
                "installation_allowed": False,
                "network_allowed": False,
                "undeclared_external_dependency_allowed": False,
                "existing_declared_dependencies_may_be_used": True,
                "new_dependency_requires_separate_future_authority": True,
            },
            "configuration_policy": {
                "configuration_must_be_project_owned": True,
                "secrets_must_not_be_embedded": True,
                "runtime_private_configuration_must_not_be_copied": True,
            },
            "accessibility_policy": {
                "required": project_type in _WEB_TYPES,
                "structural_checks": ["document_language", "viewport", "semantic_main", "labelled_controls", "keyboard_focus_visibility"],
            },
            "responsive_policy": {
                "required": project_type in _WEB_TYPES,
                "structural_checks": ["viewport", "relative_or_fluid_layout", "responsive_breakpoint"],
            },
            "content_minimized": True,
            "raw_source_content_stored": False,
            "private_paths_publicly_exposed": False,
            "selected_project_modified": False,
            "source_modified": False,
            **DENIED_AUTHORITY,
        }
        record = _seal(record, "construction_contract_digest")
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_complete_application_construction(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_record_path(str(request_id or "").lower(), runtime_root))
    return row if row and _valid(row, "construction_contract_digest") else {}


def public_complete_application_construction(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "request_id": str(record.get("request_id") or ""),
        "project_type": str(record.get("project_type") or ""),
        "construction_profile": str(record.get("construction_profile") or ""),
        "artifact_roles": [
            {k: row.get(k) for k in ("role", "required", "purpose", "preferred_paths", "acceptance_codes", "role_digest")}
            for row in list(record.get("artifact_roles") or [])[:MAX_ARTIFACT_ROLES]
        ],
        "relationships": [
            {k: row.get(k) for k in ("from_role", "to_role", "obligation", "relationship_digest")}
            for row in list(record.get("relationships") or [])[:MAX_RELATIONSHIPS]
        ],
        "required_quality_dimensions": list(record.get("required_quality_dimensions") or []),
        "construction_contract_digest": str(record.get("construction_contract_digest") or ""),
        "content_minimized": True,
        "private_paths_exposed": False,
        "raw_source_content_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }


__all__ = [
    "CONTRACT_VERSION",
    "DENIED_AUTHORITY",
    "load_complete_application_construction",
    "prepare_complete_application_construction",
    "public_complete_application_construction",
]
