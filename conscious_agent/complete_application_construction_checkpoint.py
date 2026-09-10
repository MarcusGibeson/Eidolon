from __future__ import annotations

"""v1258.9 read-only Complete Application Construction checkpoint.

The checkpoint inspects source and structured release metadata only. It does not
open operator runtime construction records, contact providers, execute tests,
run diagnostics, mutate a project, apply a candidate, or create authority.
"""

import ast
import hashlib
from pathlib import Path
from typing import Any

try:
    from checkpoint_registry import build_read_only_checkpoint_report, lookup_checkpoint
    from release_authority import WORKING_SOURCE_VERSION
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report, lookup_checkpoint  # type: ignore
    from release_authority import WORKING_SOURCE_VERSION  # type: ignore

CONTRACT_VERSION = "v1258.9"

_REQUIRED_SOURCE = (
    "conscious_agent/complete_application_construction_foundations.py",
    "conscious_agent/complete_application_construction.py",
    "conscious_agent/complete_application_construction_reliability.py",
    "conscious_agent/isolated_coding_execution.py",
    "conscious_agent/diagnostic_repair_reasoning.py",
    "tools/v1258_0_2_complete_application_construction_foundations_tests.py",
    "tools/v1258_3_5_complete_application_construction_integration_tests.py",
    "tools/v1258_6_8_complete_application_construction_reliability_tests.py",
    "tools/v1258_9_complete_application_construction_checkpoint_tests.py",
)


def _root(value: str | Path | None = None) -> Path:
    return Path(value or Path(__file__).resolve().parents[1]).expanduser().resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            try:
                return ast.literal_eval(node.value)
            except (TypeError, ValueError):
                return None
    return None


def build_complete_application_construction_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(source_root)
    files = {relative: root / relative for relative in _REQUIRED_SOURCE}
    foundations = files["conscious_agent/complete_application_construction_foundations.py"]
    integration = files["conscious_agent/complete_application_construction.py"]
    reliability = files["conscious_agent/complete_application_construction_reliability.py"]
    execution = files["conscious_agent/isolated_coding_execution.py"]
    diagnostics = files["conscious_agent/diagnostic_repair_reasoning.py"]
    foundation_text = foundations.read_text(encoding="utf-8") if foundations.is_file() else ""
    integration_text = integration.read_text(encoding="utf-8") if integration.is_file() else ""
    reliability_text = reliability.read_text(encoding="utf-8") if reliability.is_file() else ""
    execution_text = execution.read_text(encoding="utf-8") if execution.is_file() else ""
    diagnostics_text = diagnostics.read_text(encoding="utf-8") if diagnostics.is_file() else ""
    denied = _literal_assignment(foundations, "DENIED_AUTHORITY") if foundations.is_file() else None
    record = lookup_checkpoint("1258.9")
    try:
        working_parts = tuple(int(part) for part in WORKING_SOURCE_VERSION.split("."))
    except ValueError:
        working_parts = ()
    checks = {
        "working_source_at_or_after_v1258_9": working_parts >= (1258, 9),
        "required_v1258_surfaces_present": all(path.is_file() for path in files.values()),
        "foundation_contract_retained": _literal_assignment(foundations, "CONTRACT_VERSION") == "v1258.2" if foundations.is_file() else False,
        "integration_contract_retained": _literal_assignment(integration, "CONTRACT_VERSION") == "v1258.5" if integration.is_file() else False,
        "reliability_contract_retained": _literal_assignment(reliability, "CONTRACT_VERSION") == "v1258.8" if reliability.is_file() else False,
        "construction_authority_defaults_denied": isinstance(denied, dict) and bool(denied) and not any(bool(value) for value in denied.values()),
        "artifact_roles_and_relationships_present": all(token in foundation_text for token in ("artifact_roles", "relationships", "interface", "application_logic", "tests", "documentation")),
        "all_quality_dimensions_present": all(token in foundation_text for token in ("interface_coherence", "dependency_coherence", "configuration_coherence", "test_coverage", "documentation_completeness", "accessibility", "responsive_behavior")),
        "provider_prompt_receives_construction_contract": "application_construction" in execution_text and "construction_contract_public" in execution_text,
        "construction_quality_part_of_verification": "construction_quality" in execution_text and "evaluate_complete_application_quality" in execution_text,
        "quality_failure_routes_through_diagnostics": "construction_quality_recheck" in diagnostics_text and "application_coherence_defect" in diagnostics_text,
        "cross_file_quality_checks_present": all(token in integration_text for token in ("local_interface_references_resolve", "external_dependencies_declared", "project_owned_tests_present", "documentation_present")),
        "accessibility_responsive_checks_present": all(token in integration_text for token in ("document_language_declared", "controls_structurally_labelled", "keyboard_focus_visible", "responsive_breakpoint_present")),
        "read_only_health_and_handoff_present": all(token in reliability_text for token in ("inspect_complete_application_health", "build_complete_application_operator_handoff", "read_only")),
        "v1258_9_registered_exactly": bool(record and record.test_selector == "tools/v1258_9_complete_application_construction_checkpoint_tests.py"),
    }
    hashes = {relative: _sha256(path) for relative, path in files.items() if path.is_file()}
    return build_read_only_checkpoint_report(
        version="1258.9",
        status="complete_application_construction_checkpoint_ready",
        checks=checks,
        source_root=root,
        details={
            "required_source_count": len(_REQUIRED_SOURCE),
            "present_source_count": len(hashes),
            "source_sha256": hashes,
            "behavioral_evidence": [
                "tools/v1258_0_2_complete_application_construction_foundations_tests.py",
                "tools/v1258_3_5_complete_application_construction_integration_tests.py",
                "tools/v1258_6_8_complete_application_construction_reliability_tests.py",
            ],
            "coherent_multi_file_construction": True,
            "dependency_installation_performed": False,
            "accessibility_structural_verification": True,
            "responsive_structural_verification": True,
            "quality_failure_can_enter_v1257_repair": True,
            "ordinary_chat_explicit_complete_app_integration": True,
            "selected_project_application_separate_v1255_authority": True,
            "provider_contact_authorized": False,
            "construction_execution_authorized": False,
            "dependency_installation_authorized": False,
            "project_mutation_authorized": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "certification_authorized": False,
            "release_authorized": False,
            "permanent_approval_granted": False,
            "independent_authority_granted": False,
            "native_windows_and_real_browser_validation": "desktop_review_required",
        },
    )


__all__ = ["CONTRACT_VERSION", "build_complete_application_construction_checkpoint"]
