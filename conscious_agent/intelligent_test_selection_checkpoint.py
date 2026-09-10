from __future__ import annotations

"""v1266.9 read-only Intelligent Test Selection checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from intelligent_test_selection_foundations import TEST_SELECTION_DENIED_AUTHORITY
from intelligent_test_selection_reliability import inspect_intelligent_test_selection_health

CONTRACT_VERSION = "v1266.9"


def build_intelligent_test_selection_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_intelligent_test_selection_health(source_root=root)
    checks = {
        "test_selection_foundations_present": (root / "conscious_agent/intelligent_test_selection_foundations.py").is_file(),
        "test_selection_integration_present": (root / "conscious_agent/intelligent_test_selection.py").is_file(),
        "test_selection_reliability_present": (root / "conscious_agent/intelligent_test_selection_reliability.py").is_file(),
        "v1265_self_modification_retained": (root / "conscious_agent/isolated_self_modification.py").is_file(),
        "package_privacy_retained": (root / "conscious_agent/package_integrity.py").is_file(),
        "health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1266_0_2_intelligent_test_selection_foundations_tests.py",
            "tools/v1266_3_5_intelligent_test_selection_integration_tests.py",
            "tools/v1266_6_8_intelligent_test_selection_reliability_tests.py",
        ],
        "selection_contract": ["changed_paths", "affected_surfaces", "focused_tests", "regression_tests", "selection_rationale", "risk_band"],
        "tests_executed": False, "provider_contacted": False, "commands_executed": False,
        "active_source_modified": False, "candidate_workspace_modified": False,
        "repair_deferred_to_v1267": True, "next_bounded_unit": "v1267 Iterative Self-Repair",
        "native_windows_validation": "desktop_review_required", **TEST_SELECTION_DENIED_AUTHORITY,
    }
    return build_read_only_checkpoint_report(version="1266.9", status="intelligent_test_selection_checkpoint_ready", checks=checks, details=details, source_root=root)


__all__ = ["CONTRACT_VERSION", "build_intelligent_test_selection_checkpoint"]
