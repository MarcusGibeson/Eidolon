from __future__ import annotations

"""v1266.6-v1266.8 freshness, tamper, recovery and operator handoff."""

from pathlib import Path
from typing import Any, Mapping

from intelligent_test_selection_foundations import (
    TEST_SELECTION_DENIED_AUTHORITY,
    _classify_surfaces,
    _select_tests,
    _digest,
    _record_digest,
    load_test_selection,
    prepare_intelligent_test_selection,
    validate_test_selection,
)
from isolated_self_modification_foundations import load_self_modification, source_only_manifest
from isolated_self_modification_reliability import validate_self_modification_candidate

CONTRACT_VERSION = "v1266.8"


def validate_test_selection_freshness(
    selection_id: str,
    source_root: str | Path,
    *,
    self_modification_runtime_root: str | Path | None,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    record = load_test_selection(selection_id, runtime_root=runtime_root)
    if not record:
        return {"ok": False, "status": "test_selection_missing"}
    base = validate_test_selection(record)
    if not base.get("ok"):
        return {"ok": False, "status": "test_selection_invalid"}
    source_operation_id = str(record.get("source_operation_id") or "")
    candidate_valid = validate_self_modification_candidate(source_operation_id, source_root, runtime_root=self_modification_runtime_root)
    source_record = load_self_modification(source_operation_id, runtime_root=self_modification_runtime_root)
    result = dict(source_record.get("result") or {})
    workspace = Path(str(source_record.get("workspace_path") or ""))
    workspace_ok = workspace.is_dir()
    current_manifest = source_only_manifest(workspace)["source_manifest_digest"] if workspace_ok else ""
    candidate_match = current_manifest == record.get("candidate_manifest_digest") == result.get("candidate_manifest_digest")
    result_match = source_record.get("result_digest") == record.get("source_result_digest")
    changed_paths = sorted(str(row.get("relative_path") or "") for row in result.get("changed_files") or [] if row.get("relative_path"))
    surfaces = _classify_surfaces(changed_paths)
    recomputed, inventory, _depth = _select_tests(workspace, changed_paths, surfaces, trusted_test_root=Path(source_root).expanduser().resolve(strict=True)) if workspace_ok else ([], [], {})
    selection_semantics_match = recomputed == list(record.get("selected_tests") or []) and surfaces == list(record.get("affected_surfaces") or []) and _digest(inventory) == record.get("test_inventory_digest")
    ok = bool(candidate_valid.get("ok")) and workspace_ok and candidate_match and result_match and selection_semantics_match
    return {
        "ok": ok, "status": "test_selection_fresh" if ok else "stale_or_changed_test_selection_source",
        "candidate_valid": candidate_valid.get("ok") is True, "workspace_present": workspace_ok,
        "candidate_manifest_match": candidate_match, "source_result_match": result_match, "selection_semantics_match": selection_semantics_match,
        "tests_executed": False, "active_source_modified": False,
    }


def inspect_intelligent_test_selection_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    checks = {
        "foundations_present": (root / "conscious_agent/intelligent_test_selection_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/intelligent_test_selection.py").is_file(),
        "reliability_present": (root / "conscious_agent/intelligent_test_selection_reliability.py").is_file(),
        "v1265_retained": (root / "conscious_agent/isolated_self_modification.py").is_file(),
        "package_privacy_retained": (root / "conscious_agent/package_integrity.py").is_file(),
    }
    return {"ok": all(checks.values()), "status": "intelligent_test_selection_health_ready" if all(checks.values()) else "intelligent_test_selection_health_blocked", "checks": checks, "read_only": True, "tests_executed": False, **TEST_SELECTION_DENIED_AUTHORITY}


def build_intelligent_test_selection_operator_handoff(*, source_root: str | Path | None = None) -> dict[str, Any]:
    health = inspect_intelligent_test_selection_health(source_root=source_root)
    return {
        "ok": health["ok"], "contract_version": CONTRACT_VERSION,
        "status": "intelligent_test_selection_operator_handoff_ready" if health["ok"] else "intelligent_test_selection_operator_handoff_blocked",
        "next_bounded_unit": "v1267 Iterative Self-Repair",
        "review_boundaries": [
            "selection_does_not_execute_tests", "selection_does_not_contact_provider", "active_source_never_modified",
            "candidate_workspace_not_modified", "application_remains_separately_governed_by_v1255", "repair_deferred_to_v1267",
        ],
        "native_windows_review": [
            "real_ntfs_junction_and_reparse_containment", "case_insensitive_test_path_aliases", "long_candidate_workspace_paths",
            "cross_process_duplicate_selection", "candidate_change_between_selection_and_execution",
        ],
        **TEST_SELECTION_DENIED_AUTHORITY,
    }


__all__ = ["CONTRACT_VERSION", "validate_test_selection_freshness", "inspect_intelligent_test_selection_health", "build_intelligent_test_selection_operator_handoff"]
