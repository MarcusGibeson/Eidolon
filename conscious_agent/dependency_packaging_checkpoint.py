from __future__ import annotations

"""v1275.9 read-only Dependency and Packaging Management checkpoint."""

from pathlib import Path
from typing import Any

from checkpoint_registry import build_read_only_checkpoint_report
from dependency_packaging_foundations import AUTHORITY_FLAGS
from dependency_packaging_reliability import inspect_dependency_packaging_health

CONTRACT_VERSION = "v1275.9"


def build_dependency_packaging_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_dependency_packaging_health(source_root=root)
    checks = {
        "foundations_present": (root / "conscious_agent/dependency_packaging_foundations.py").is_file(),
        "integration_present": (root / "conscious_agent/dependency_packaging.py").is_file(),
        "reliability_present": (root / "conscious_agent/dependency_packaging_reliability.py").is_file(),
        "v1274_environment_integration_retained": (root / "conscious_agent/environment_awareness.py").is_file(),
        "v1273_ownership_integration_retained": (root / "conscious_agent/ownership_concurrency.py").is_file(),
        "v1272_recovery_integration_retained": (root / "conscious_agent/restart_crash_recovery.py").is_file(),
        "source_only_policy_retained": (root / "conscious_agent/package_integrity.py").is_file(),
        "checkpoint_is_read_only": True,
        "health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": [
            "tools/v1275_0_2_dependency_packaging_foundations_tests.py",
            "tools/v1275_3_5_dependency_packaging_integration_tests.py",
            "tools/v1275_6_8_dependency_packaging_reliability_tests.py",
        ],
        "contract": [
            "dependency_intent_inventory", "conflict_detection", "deliberate_change_plan", "lock_configuration_intent",
            "exact_disposable_install_authorization", "clean_install_verification", "reproducible_source_package_manifest",
            "privacy_safe_source_only_packaging", "v1274_observed_environment_preflight", "no_authority_creation",
        ],
        "checkpoint_executes_provider": False, "checkpoint_executes_commands": False, "checkpoint_executes_tests": False,
        "checkpoint_executes_install": False, "checkpoint_executes_update": False, "checkpoint_mutates_source": False,
        "next_bounded_unit": "v1276 Architecture Boundary Extraction", "native_windows_validation": "desktop_review_required",
        **AUTHORITY_FLAGS,
    }
    return build_read_only_checkpoint_report(version="1275.9", status="dependency_packaging_management_checkpoint_ready", checks=checks, details=details, source_root=root)


__all__ = ["build_dependency_packaging_checkpoint"]
