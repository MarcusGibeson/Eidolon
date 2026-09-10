from __future__ import annotations

"""v1265.9 read-only Isolated Self-Modification checkpoint."""

from pathlib import Path
from typing import Any
from checkpoint_registry import build_read_only_checkpoint_report
from isolated_self_modification_foundations import SELF_MODIFICATION_DENIED_AUTHORITY
from isolated_self_modification_reliability import inspect_isolated_self_modification_health

CONTRACT_VERSION = "v1265.9"


def build_isolated_self_modification_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve(); health = inspect_isolated_self_modification_health(source_root=root)
    checks = {
        "self_modification_foundations_present": (root / "conscious_agent/isolated_self_modification_foundations.py").is_file(),
        "self_modification_integration_present": (root / "conscious_agent/isolated_self_modification.py").is_file(),
        "self_modification_reliability_present": (root / "conscious_agent/isolated_self_modification_reliability.py").is_file(),
        "v1264_alternative_planning_retained": (root / "conscious_agent/alternative_planning.py").is_file(),
        "package_privacy_retained": (root / "conscious_agent/package_integrity.py").is_file(),
        "health_checks_pass": health.get("ok") is True,
    }
    details = {
        "behavioral_evidence": ["tools/v1265_0_2_isolated_self_modification_foundations_tests.py", "tools/v1265_3_5_isolated_self_modification_integration_tests.py", "tools/v1265_6_8_isolated_self_modification_reliability_tests.py"],
        "clean_copy_required": True, "private_runtime_copied": False, "active_source_modified": False, "provider_contacted": False,
        "commands_executed": False, "tests_executed": False, "candidate_application_authorized": False, "self_update_authorized": False,
        "test_selection_deferred_to_v1266": True, "next_bounded_unit": "v1266 Intelligent Test Selection", "native_windows_validation": "desktop_review_required",
        **SELF_MODIFICATION_DENIED_AUTHORITY,
    }
    return build_read_only_checkpoint_report(version="1265.9", status="isolated_self_modification_checkpoint_ready", checks=checks, details=details, source_root=root)


__all__ = ["CONTRACT_VERSION", "build_isolated_self_modification_checkpoint"]
